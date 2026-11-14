"""Tables de référence pour le service de prédiction (T7.3, local puis S3).

Construites une fois depuis le Parquet préparé et NOAA, puis lues par ``FeatureBuilder`` :

- ``observations.parquet`` : observations météo décodées (par aéroport, UTC) ;
- ``routes.parquet`` : distance et durée programmée médiane par itinéraire ;
- ``history_daily.parquet`` : vols éligibles et retards par jour pour chaque clé historique ;
- ``replay.parquet`` : vols de la **période de test** avec leurs variables exactes (mode rejeu,
  D-02) ; l'identifiant est ``AAAA-MM-JJ_<compagnie><numéro>_<origine>_<HHMM local>``.

Commande : ``uv run python -m aeropulse.data.serving_tables``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from aeropulse import config
from aeropulse.data import weather

HISTORY_KINDS = ("carrier", "origin", "route", "origin_hour")


def history_keys(flights: pd.DataFrame) -> dict[str, pd.Series]:
    """Clé texte de chaque type d'historique (même définition qu'à l'entraînement)."""
    return {
        "carrier": flights["carrier"].astype(str),
        "origin": flights["origin"].astype(str),
        "route": flights["origin"].astype(str) + "-" + flights["destination"].astype(str),
        "origin_hour": flights["origin"].astype(str) + "|" + flights["departure_hour"].astype(str),
    }


def flight_ids(frame: pd.DataFrame) -> pd.Series:
    """Identifiant de vol : date locale, compagnie+numéro, origine, heure locale programmée."""
    local = pd.to_datetime(frame["scheduled_departure_utc"], utc=True).dt.tz_convert(
        config.LOCAL_TIMEZONE
    )
    return (
        frame["flight_date"].astype(str)
        + "_"
        + frame["carrier"].astype(str)
        + frame["flight_number"].astype(str)
        + "_"
        + frame["origin"].astype(str)
        + "_"
        + local.dt.strftime("%H%M")
    )


def build_replay(ml_path: Path, out_path: Path) -> int:
    """Écrit la table de rejeu (test uniquement) ; refuse des identifiants en double."""
    ml = pd.read_parquet(ml_path)
    test = ml[ml["split"] == "test"].copy()
    test.insert(0, "flight_id", flight_ids(test))
    if test["flight_id"].duplicated().any():
        raise ValueError("identifiants de vol en double dans la période de test")
    test["observed_is_delayed"] = test[config.TARGET_CLASSIFICATION].astype(bool)
    columns = ["flight_id", *config.FEATURE_COLUMNS, "observed_is_delayed"]
    test[columns].to_parquet(out_path, index=False)
    return len(test)


def build(processed_dir: Path, raw_dir: Path, out_dir: Path) -> dict[str, int]:
    flights = pd.read_parquet(
        processed_dir / "flights",
        columns=[
            "flight_date",
            "carrier",
            "origin",
            "destination",
            "departure_hour",
            "ml_eligible",
            "is_delayed",
            "distance_miles",
            "scheduled_elapsed_minutes",
        ],
    )
    obs = weather.read_noaa(sorted((raw_dir / "noaa").glob("*/*.csv")))
    observations = obs[["airport", "observed_utc", *weather.WEATHER_COLUMNS]]

    routes = (
        flights.groupby(["origin", "destination"])
        .agg(
            distance_miles=("distance_miles", "median"),
            scheduled_elapsed_minutes=("scheduled_elapsed_minutes", "median"),
            n_flights=("carrier", "size"),
        )
        .reset_index()
    )

    eligible = flights[flights["ml_eligible"].astype(bool)].copy()
    eligible["_date"] = pd.to_datetime(eligible["flight_date"]).dt.normalize()
    eligible["_delayed"] = eligible["is_delayed"].astype(bool)
    parts: list[pd.DataFrame] = []
    for kind, key in history_keys(eligible).items():
        daily = (
            eligible.assign(key=key)
            .groupby(["key", "_date"])
            .agg(n=("_delayed", "size"), delayed=("_delayed", "sum"))
            .reset_index()
            .rename(columns={"_date": "date"})
        )
        daily.insert(0, "kind", kind)
        parts.append(daily)
    history = pd.concat(parts, ignore_index=True)
    history["n"] = history["n"].astype("int64")
    history["delayed"] = history["delayed"].astype("int64")

    out_dir.mkdir(parents=True, exist_ok=True)
    observations.to_parquet(out_dir / "observations.parquet", index=False)
    routes.to_parquet(out_dir / "routes.parquet", index=False)
    history.to_parquet(out_dir / "history_daily.parquet", index=False)
    sizes = {
        "observations": len(observations),
        "routes": len(routes),
        "history_daily": len(history),
    }
    (out_dir / "serving_tables.json").write_text(json.dumps(sizes, indent=2), encoding="utf-8")
    return sizes


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    p.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    p.add_argument("--out-dir", type=Path, default=Path("data/serving"))
    p.add_argument("--ml-dataset", type=Path, default=Path("data/ml/ml_dataset.parquet"))
    args = p.parse_args(argv)
    sizes = build(args.processed_dir, args.raw_dir, args.out_dir)
    sizes["replay"] = build_replay(args.ml_dataset, args.out_dir / "replay.parquet")
    print(json.dumps(sizes, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
