"""Exécution des requêtes : DuckDB en local, Athena plus tard.

Connexion en mémoire, vue en lecture seule sur le Parquet préparé (``data/processed/flights``).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import duckdb

from aeropulse import config
from aeropulse.analytics import queries

SOURCE = "aeropulse-processed (NYC Flight Delays and Weather, JFK/EWR/LGA)"
INSUFFICIENT = "données insuffisantes"


def _literal(value: str) -> str:
    """Littéral SQL pour un chemin interne (apostrophes doublées)."""
    return "'" + value.replace("'", "''") + "'"


class Analytics:
    """Accès analytique lecture seule au jeu préparé."""

    def __init__(self, processed_dir: Path = Path("data/processed/flights")) -> None:
        self._con = duckdb.connect(":memory:")
        pattern = _literal((processed_dir / "**" / "*.parquet").as_posix())
        # Chemin interne (jamais une entrée d'appelant) : DuckDB n'accepte pas de paramètre ici.
        self._con.execute(
            f"CREATE VIEW flights AS SELECT * FROM read_parquet({pattern}, hive_partitioning=true)"
        )
        self.allowed = queries.Allowed(
            carriers=self._distinct("carrier"),
            airports=frozenset(config.AIRPORTS),
            destinations=self._distinct("destination"),
        )

    def _distinct(self, column: str) -> frozenset[str]:
        # `column` est une constante interne, jamais une entrée d'appelant.
        rows = self._con.execute(f"SELECT DISTINCT {column} FROM flights").fetchall()
        return frozenset(str(r[0]) for r in rows if r[0] is not None)

    def statistics(
        self,
        dimension: str,
        filters: Mapping[str, object] | None = None,
        limit: object = None,
    ) -> dict[str, Any]:
        """Statistiques par compagnie / aéroport / itinéraire, avec taille d'échantillon."""
        query = queries.build_statistics_query(dimension, dict(filters or {}), limit, self.allowed)
        cur = self._con.execute(query.sql + f" LIMIT {query.limit}", list(query.params))
        names = [d[0] for d in cur.description]
        rows = [self._row(dict(zip(names, r, strict=True)), query.keys) for r in cur.fetchall()]
        return {"source": SOURCE, "dimension": dimension, "limit": query.limit, "rows": rows}

    @staticmethod
    def _row(raw: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
        scored = int(raw["n_scored"])
        enough = scored >= config.MIN_SAMPLE_SIZE
        return {
            **{k: raw[k] for k in keys},
            "period": {"start": str(raw["period_start"]), "end": str(raw["period_end"])},
            "n_flights": int(raw["n_flights"]),
            "n_scored": scored,
            "n_cancelled": int(raw["n_cancelled"]),
            "n_diverted": int(raw["n_diverted"]),
            "sufficient": enough,
            "delay_rate": int(raw["n_delayed"]) / scored if enough else None,
            "mean_departure_delay_min": raw["mean_departure_delay_min"] if enough else None,
            "note": None if enough else INSUFFICIENT,
        }

    def export_aggregates(self, out_dir: Path) -> dict[str, int]:
        """Écrit les agrégats par compagnie, aéroport et itinéraire en Parquet (T2.6)."""
        out_dir.mkdir(parents=True, exist_ok=True)
        counts: dict[str, int] = {}
        for dimension in queries.DIMENSIONS:
            query = queries.build_statistics_query(dimension, {}, queries.MAX_LIMIT, self.allowed)
            target = (out_dir / f"{dimension}.parquet").as_posix()
            self._con.execute(
                f"COPY ({query.sql}) TO {_literal(target)} (FORMAT parquet)", list(query.params)
            )
            row = self._con.execute(
                f"SELECT count(*) FROM read_parquet({_literal(target)})"
            ).fetchone()
            counts[dimension] = int(row[0]) if row else 0
        return counts

    def close(self) -> None:
        self._con.close()
