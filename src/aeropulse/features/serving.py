"""Variables T-2h pour un vol saisi (service de prédiction, T7.3, R-18).

Réutilise le code partagé de ``features/`` et de ``data/weather`` (jointure as-of ≤ T-2h,
variables calendaires, écart de point de rosée) ; seul l'historique est recalculé depuis des
agrégats quotidiens, avec la **même règle** qu'à l'entraînement (jours précédents uniquement,
fenêtre de ``config.HISTORY_WINDOW_DAYS``, NaN sous ``config.MIN_SAMPLE_SIZE`` vols). La parité
avec ``ml_dataset`` est vérifiée par un test sur données réelles.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from aeropulse import config
from aeropulse.data import weather
from aeropulse.features import temporal
from aeropulse.features import weather as weather_features

ALLOWED_FIELDS = frozenset(
    {"airline", "origin", "destination", "scheduled_departure", "scheduled_elapsed_minutes"}
)
REQUIRED_FIELDS = ("airline", "origin", "destination", "scheduled_departure")
HISTORY_COLUMNS = {
    "carrier": "carrier_delay_rate_28d",
    "origin": "origin_delay_rate_28d",
    "route": "route_delay_rate_28d",
    "origin_hour": "origin_hour_delay_rate_28d",
}
MAX_ELAPSED_MINUTES = 1500  # vols vers Hawaï : jusqu'à 1 162 min dans les données


class ServingError(ValueError):
    """Erreur de service ; ``code`` et ``status`` pilotent la réponse HTTP."""

    status = 500
    code = "internal_error"


class InvalidRequestError(ServingError):
    status = 400
    code = "invalid_parameter"


class OutOfCoverageError(ServingError):
    status = 422
    code = "out_of_coverage"


class NotFoundError(ServingError):
    status = 404
    code = "flight_not_found"


class FeatureBuilder:
    """Construit les ``FEATURE_COLUMNS`` d'un vol à partir des tables de service."""

    def __init__(self, tables_dir: Path) -> None:
        self.observations = pd.read_parquet(tables_dir / "observations.parquet")
        self.routes = pd.read_parquet(tables_dir / "routes.parquet").set_index(
            ["origin", "destination"]
        )
        history = pd.read_parquet(tables_dir / "history_daily.parquet")
        self._history = {
            (kind, key): g.sort_values("date")
            for (kind, key), g in history.groupby(["kind", "key"], sort=False)
        }
        self.carriers = frozenset(str(k) for kind, k in self._history if kind == "carrier")
        self.destinations = frozenset(str(d) for _, d in self.routes.index)

    # --- validation -----------------------------------------------------------------------
    def _parse(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(request, Mapping):
            raise InvalidRequestError("le corps doit être un objet JSON")
        unknown = sorted(set(request) - ALLOWED_FIELDS)
        if unknown:
            raise InvalidRequestError(f"champs non autorisés : {unknown}")
        missing = [f for f in REQUIRED_FIELDS if request.get(f) in (None, "")]
        if missing:
            raise InvalidRequestError(f"champs manquants : {missing}")
        carrier = str(request["airline"]).upper()
        origin = str(request["origin"]).upper()
        destination = str(request["destination"]).upper()
        if carrier not in self.carriers:
            raise InvalidRequestError("airline : compagnie inconnue")
        if origin not in config.AIRPORTS:
            raise InvalidRequestError(f"origin : une valeur parmi {sorted(config.AIRPORTS)}")
        if (origin, destination) not in self.routes.index:
            raise InvalidRequestError("destination : itinéraire inconnu pour cette origine")
        raw_dt = request["scheduled_departure"]
        if not isinstance(raw_dt, str) or len(raw_dt) > 40:
            raise InvalidRequestError("scheduled_departure : date ISO 8601 avec fuseau attendue")
        try:
            parsed = datetime.fromisoformat(raw_dt)
        except ValueError as exc:
            raise InvalidRequestError("scheduled_departure : format ISO 8601 invalide") from exc
        if parsed.tzinfo is None:
            raise InvalidRequestError("scheduled_departure : le fuseau horaire est obligatoire")
        elapsed = request.get("scheduled_elapsed_minutes")
        if elapsed is not None:
            if isinstance(elapsed, bool) or not isinstance(elapsed, int | float):
                raise InvalidRequestError("scheduled_elapsed_minutes : nombre attendu")
            if not 20 <= float(elapsed) <= MAX_ELAPSED_MINUTES:
                raise InvalidRequestError(
                    f"scheduled_elapsed_minutes : entre 20 et {MAX_ELAPSED_MINUTES}"
                )
        return {
            "carrier": carrier,
            "origin": origin,
            "destination": destination,
            "departure": parsed,
            "elapsed": None if elapsed is None else float(elapsed),
        }

    # --- historique -----------------------------------------------------------------------
    def _rate(self, kind: str, key: str, date: pd.Timestamp) -> float:
        g = self._history.get((kind, key))
        if g is None:
            return math.nan
        start = date - pd.Timedelta(days=config.HISTORY_WINDOW_DAYS)
        window = g[(g["date"] >= start) & (g["date"] < date)]  # jours précédents uniquement
        n = int(window["n"].sum())
        if n < config.MIN_SAMPLE_SIZE:
            return math.nan
        return float(window["delayed"].sum()) / n

    # --- construction ---------------------------------------------------------------------
    def build(self, request: Mapping[str, Any]) -> pd.DataFrame:
        r = self._parse(request)
        local = r["departure"].astimezone(ZoneInfo(config.LOCAL_TIMEZONE))
        flight_date = pd.Timestamp(local.date())
        if not pd.Timestamp(config.STUDY_START) <= flight_date <= pd.Timestamp(config.STUDY_END):
            raise OutOfCoverageError(
                f"date hors de la période couverte ({config.STUDY_START} → {config.STUDY_END})"
            )
        route_row = self.routes.loc[(r["origin"], r["destination"])]
        frame = pd.DataFrame(
            {
                "flight_date": [str(flight_date.date())],
                "carrier": [r["carrier"]],
                "origin": [r["origin"]],
                "destination": [r["destination"]],
                "scheduled_departure_utc": [pd.Timestamp(r["departure"]).tz_convert("UTC")],
                "departure_hour": [local.hour],
                "day_of_week": [local.isoweekday()],  # convention du jeu : lundi = 1
                "month": [local.month],
                "distance_miles": [float(route_row["distance_miles"])],
                "scheduled_elapsed_minutes": [
                    r["elapsed"]
                    if r["elapsed"] is not None
                    else float(route_row["scheduled_elapsed_minutes"])
                ],
            }
        )
        frame = temporal.add_temporal_features(frame)
        frame = weather.join_weather_at_cutoff(
            frame, self.observations, max_age=pd.Timedelta(config.MAX_WEATHER_AGE)
        )
        weather.assert_no_future_weather(frame)
        frame["weather_missing"] = frame["weather_observed_utc"].isna()
        frame = weather_features.add_weather_features(frame)
        keys = {
            "carrier": r["carrier"],
            "origin": r["origin"],
            "route": f"{r['origin']}-{r['destination']}",
            "origin_hour": f"{r['origin']}|{local.hour}",
        }
        for kind, column in HISTORY_COLUMNS.items():
            frame[column] = self._rate(kind, keys[kind], flight_date)
        return frame[list(config.FEATURE_COLUMNS)]

    def weather_summary(self, features: pd.DataFrame) -> dict[str, Any]:
        """Résumé de la météo utilisée (âge, absence) pour la réponse."""
        age = features["weather_age_minutes"].iloc[0]
        return {
            "missing": bool(features["weather_missing"].iloc[0]),
            "age_minutes": None if pd.isna(age) else float(age),
        }


FLIGHT_ID = re.compile(r"^\d{4}-\d{2}-\d{2}_[A-Z0-9]{2}\d{1,4}_[A-Z]{3}_\d{4}$")


class ReplayStore:
    """Rejeu d'un vol de la période de test (D-02) : variables exactes du jeu ML, sans recalcul."""

    def __init__(self, tables_dir: Path) -> None:
        table = pd.read_parquet(tables_dir / "replay.parquet")
        self._table = table.set_index("flight_id")

    def get(self, request: Mapping[str, Any]) -> tuple[pd.DataFrame, bool]:
        """Renvoie (variables du vol, issue observée). Seul ``flight_id`` est accepté."""
        extra = sorted(set(request) - {"flight_id"})
        if extra:
            raise InvalidRequestError(f"avec flight_id, aucun autre champ n'est autorisé : {extra}")
        flight_id = request.get("flight_id")
        if not isinstance(flight_id, str) or not FLIGHT_ID.fullmatch(flight_id.upper()):
            raise InvalidRequestError(
                "flight_id : format AAAA-MM-JJ_<compagnie><numéro>_<ORI>_<HHMM>"
            )
        key = flight_id.upper()
        if key not in self._table.index:
            raise NotFoundError("vol introuvable dans la période de test")
        row = self._table.loc[[key]]
        return row[list(config.FEATURE_COLUMNS)], bool(row["observed_is_delayed"].iloc[0])
