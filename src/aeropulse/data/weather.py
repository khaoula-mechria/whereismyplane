"""Observations météo NOAA Global Hourly (UTC) et jointure à T-2h (T1.5, AC-24, ADR-0009).

Seules les observations METAR (FM-15) et SPECI (FM-16) sont retenues. Pour chaque vol, on prend
la dernière observation **dont l'heure est ≤ T-2h** à l'aéroport de départ (jointure as-of) ;
aucune valeur n'est inventée : sans observation (ou trop ancienne), les champs sont ``NaN``.
Les champs ISD sont ``valeur,code_qualité,...`` ; les valeurs manquantes sont des 9 répétés.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd

from aeropulse import config

REPORT_TYPES = ("FM-15", "FM-16")
BAD_QUALITY = ("2", "3", "6", "7")  # suspect / erroné (codes de qualité ISD)
NOAA_COLUMNS = ("STATION", "DATE", "REPORT_TYPE", "TMP", "DEW", "WND", "VIS", "CIG", "SLP")
WEATHER_COLUMNS = (
    "temperature_c",
    "dewpoint_c",
    "wind_speed_mps",
    "visibility_m",
    "ceiling_m",
    "sea_level_pressure_hpa",
)


def _field(series: pd.Series, index: int, missing: int, scale: float, qual_index: int) -> pd.Series:
    """Extrait un nombre d'un champ ISD ; ``NaN`` si manquant, absent ou de qualité douteuse."""
    width = max(index, qual_index) + 1
    parts = series.fillna("").astype(str).str.split(",", expand=True).reindex(columns=range(width))
    raw = pd.to_numeric(parts[index].astype(str).str.strip(), errors="coerce")
    quality = parts[qual_index].astype(str).str.strip().str[:1]
    invalid = raw.isna() | (raw == missing) | quality.isin(BAD_QUALITY)
    return (raw / scale).where(~invalid).astype("float64")


def decode_observations(raw: pd.DataFrame) -> pd.DataFrame:
    """Décode les champs ISD d'un tableau brut en colonnes numériques (unités SI)."""
    return pd.DataFrame(
        {
            "weather_station": raw["STATION"].astype(str),
            "observed_utc": pd.to_datetime(raw["DATE"]),
            "temperature_c": _field(raw["TMP"], 0, 9999, 10, 1),
            "dewpoint_c": _field(raw["DEW"], 0, 9999, 10, 1),
            "wind_speed_mps": _field(raw["WND"], 3, 9999, 10, 4),
            "visibility_m": _field(raw["VIS"], 0, 999999, 1, 1),
            "ceiling_m": _field(raw["CIG"], 0, 99999, 1, 1),
            "sea_level_pressure_hpa": _field(raw["SLP"], 0, 99999, 10, 1),
        }
    )


def read_noaa(paths: Iterable[Path]) -> pd.DataFrame:
    """Lit des CSV NOAA par nom de colonne (les schémas varient selon l'année) puis décode.

    Garde uniquement METAR/SPECI et ajoute ``airport`` d'après ``config.NOAA_STATIONS``.
    """
    stations = {station: airport for airport, station in config.NOAA_STATIONS.items()}
    frames: list[pd.DataFrame] = []
    for path in paths:
        raw = pd.read_csv(path, usecols=lambda c: c in NOAA_COLUMNS, dtype=str)
        frames.append(raw[raw["REPORT_TYPE"].str.strip().isin(REPORT_TYPES)])
    if not frames:
        raise ValueError("aucun fichier NOAA fourni")
    obs = decode_observations(pd.concat(frames, ignore_index=True))
    obs["airport"] = obs["weather_station"].map(stations)
    if obs["airport"].isna().any():
        raise ValueError("station NOAA inconnue dans les fichiers")
    return obs.sort_values(["airport", "observed_utc"], kind="stable").reset_index(drop=True)


def join_weather_at_cutoff(
    flights: pd.DataFrame,
    observations: pd.DataFrame,
    *,
    max_age: pd.Timedelta | None = None,
    airport_col: str = "origin",
    departure_col: str = "scheduled_departure_utc",
) -> pd.DataFrame:
    """Ajoute la dernière observation ≤ T-2h par vol (jointure as-of, par aéroport).

    ``weather_age_minutes`` = âge à T-2h. Si ``max_age`` est fourni, les observations plus
    anciennes sont remplacées par ``NaN`` (valeur du seuil : décision en attente, jamais codée
    en dur ici). L'ordre des lignes de ``flights`` est conservé.
    """
    left = flights.copy()
    departure = pd.to_datetime(left[departure_col])
    if departure.dt.tz is not None:
        departure = departure.dt.tz_convert("UTC").dt.tz_localize(None)
    left["feature_cutoff_utc"] = departure - config.PREDICTION_HORIZON
    left["_row"] = np.arange(len(left))
    right = observations[["airport", "observed_utc", *WEATHER_COLUMNS]].copy()
    right["weather_observed_utc"] = right["observed_utc"]
    merged = pd.merge_asof(
        left.sort_values("feature_cutoff_utc", kind="stable"),
        right.sort_values("observed_utc", kind="stable"),
        left_on="feature_cutoff_utc",
        right_on="observed_utc",
        left_by=airport_col,
        right_by="airport",
        direction="backward",
    )
    age = (merged["feature_cutoff_utc"] - merged["weather_observed_utc"]).dt.total_seconds() / 60
    merged["weather_age_minutes"] = age
    if max_age is not None:
        too_old = age > max_age.total_seconds() / 60
        masked = [*WEATHER_COLUMNS, "weather_observed_utc", "weather_age_minutes"]
        merged.loc[too_old, masked] = np.nan
    merged = merged.sort_values("_row", kind="stable")
    return merged.drop(columns=["_row", "observed_utc", "airport"]).reset_index(drop=True)


def assert_no_future_weather(joined: pd.DataFrame) -> None:
    """Garde-fou anti-fuite : aucune observation postérieure au cutoff."""
    after = joined["weather_observed_utc"] > joined["feature_cutoff_utc"]
    if bool(after.any()):
        raise ValueError(f"{int(after.sum())} observations météo postérieures à T-2h")
