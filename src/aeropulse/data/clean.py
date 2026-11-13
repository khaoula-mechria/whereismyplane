"""Préparation des vols : cible recalculée, météo NOAA à T-2h (CMP-02, FR-02, FR-06, D-19).

- Les colonnes météo du fichier Mostly Right (cutoff T-1h) sont **écartées** (fuite) ;
  la météo vient de NOAA par jointure as-of ≤ T-2h.
- ``is_delayed`` = ``departure_delay_minutes > 15`` (strict), recalculé ; ``departure_delayed_15``
  (≥ 15) n'est pas utilisée.
- Annulés et déroutés restent dans le fichier (statistiques descriptives) mais
  ``ml_eligible`` les exclut des cibles ML (D-19). Les résultats (retards, annulation…) sont des
  étiquettes, jamais des variables : voir ``config.FORBIDDEN_FEATURE_COLUMNS``.
"""

from __future__ import annotations

import pandas as pd

from aeropulse import config
from aeropulse.data import weather

SOURCE_WEATHER_COLUMNS = (
    "weather_station",
    "weather_observed_utc",
    "weather_age_minutes",
    "temperature_c",
    "dewpoint_c",
    "wind_speed_mps",
    "visibility_m",
    "ceiling_m",
    "feature_cutoff_utc",
)
NUMERIC_COLUMNS = (
    "scheduled_elapsed_minutes",
    "distance_miles",
    "departure_delay_minutes",
    "arrival_delay_minutes",
)


def prepare_flights(
    raw: pd.DataFrame,
    observations: pd.DataFrame,
    *,
    max_weather_age: pd.Timedelta | None = None,
) -> pd.DataFrame:
    """Retourne les vols préparés (ordre conservé)."""
    flights = raw.drop(columns=[c for c in SOURCE_WEATHER_COLUMNS if c in raw.columns]).copy()
    for col in NUMERIC_COLUMNS:
        flights[col] = pd.to_numeric(flights[col], errors="coerce").astype("float64")
    flights["cancelled"] = flights["cancelled"].astype(bool)
    flights["diverted"] = flights["diverted"].astype(bool)
    flights["scheduled_departure_utc"] = pd.to_datetime(
        flights["scheduled_departure_utc"], utc=True
    )

    flights = weather.join_weather_at_cutoff(flights, observations, max_age=max_weather_age)
    weather.assert_no_future_weather(flights)
    flights["weather_missing"] = flights["weather_observed_utc"].isna()

    delay = flights["departure_delay_minutes"]
    flights["ml_eligible"] = ~flights["cancelled"] & ~flights["diverted"] & delay.notna()
    flights["is_delayed"] = pd.array(
        [
            bool(config.is_delayed(x)) if ok else None
            for x, ok in zip(delay, flights["ml_eligible"], strict=True)
        ],
        dtype="boolean",
    )
    flights["year"] = pd.to_datetime(flights["flight_date"]).dt.year
    return flights
