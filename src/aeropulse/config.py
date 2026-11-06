"""Constantes centrales du projet (T0.5).

Source unique pour : le seuil de retard, l'horizon T-2h, les colonnes interdites comme
variables (prévention des fuites, ADR-0003), le seuil d'échantillon minimal (D-16) et les
stations météo. Aucune date de découpage n'est fixée ici : elle dépend de la couverture
réelle des données (T3.6, ADR-0004).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import Final

# --- Cible (docs/01-planning/requirements.md FR-06) ---------------------------------------
DELAY_THRESHOLD_MINUTES: Final = 15
"""`is_delayed = 1` si `dep_delay > 15` (strict). BTS/Mostly Right utilisent >= 15 : on
recalcule la cible depuis `dep_delay` (docs/data-acquisition-study.md §2)."""

# --- Horizon de prédiction (ADR-0003) ----------------------------------------------------
PREDICTION_HORIZON: Final = timedelta(hours=2)
"""Prédiction faite 2 h avant le départ programmé. Le dataset Mostly Right, lui, utilise 1 h."""

LOCAL_TIMEZONE: Final = "America/New_York"
"""Fuseau des heures BTS (heure locale hhmm) pour JFK, EWR et LGA."""

# --- Périmètre des données (cible de l'étude, à vérifier sur les données réelles) --------
AIRPORTS: Final = ("JFK", "EWR", "LGA")
STUDY_START: Final = date(2023, 1, 1)
STUDY_END: Final = date(2025, 7, 31)

# Stations NOAA Global Hourly (USAF+WBAN), vérifiées dans les fichiers 2024
# (docs/data-acquisition-study.md §4).
NOAA_STATIONS: Final = {
    "JFK": "74486094789",
    "LGA": "72503014732",
    "EWR": "72502014734",
}

# --- Statistiques (D-16) -------------------------------------------------------------------
MIN_SAMPLE_SIZE: Final = 30
"""En dessous de 30 vols, une statistique n'est pas affichée."""

# --- Colonnes interdites comme variables (ADR-0003) ----------------------------------------
# Noms normalisés en minuscules. Couvre le schéma BTS d'origine et le schéma Mostly Right.
FORBIDDEN_FEATURE_COLUMNS: Final = frozenset(
    {
        # Départ réel et résultats (connus après le départ)
        "deptime", "depdelay", "depdelayminutes", "depdel15", "departuredelaygroups",
        "departure_delay_minutes", "departure_delayed_15", "dep_delay", "is_delayed",
        "taxiout", "wheelsoff", "actual_departure",
        # Arrivée
        "arrtime", "arrdelay", "arrdelayminutes", "arrdel15", "arrivaldelaygroups",
        "arrival_delay_minutes", "arrival_delayed_15", "wheelson", "taxiin",
        "actualelapsedtime", "airtime",
        # Annulation / déroutement
        "cancelled", "cancellationcode", "diverted",
        # Causes de retard
        "carrierdelay", "weatherdelay", "nasdelay", "securitydelay", "lateaircraftdelay",
    }
)  # fmt: skip


class LeakageError(ValueError):
    """Une colonne interdite (information postérieure à T-2h) figure dans les variables."""


def forbidden_columns_in(columns: Iterable[str]) -> list[str]:
    """Retourne, dans l'ordre d'entrée, les colonnes interdites présentes (casse ignorée)."""
    return [c for c in columns if c.lower() in FORBIDDEN_FEATURE_COLUMNS]


def assert_no_forbidden_columns(columns: Iterable[str]) -> None:
    """Lève `LeakageError` si une colonne interdite est utilisée comme variable."""
    found = forbidden_columns_in(columns)
    if found:
        raise LeakageError(f"Colonnes interdites (fuite de données) : {sorted(found)}")


def is_delayed(dep_delay_minutes: float) -> bool:
    """Cible de classification : retard strictement supérieur à 15 minutes."""
    return dep_delay_minutes > DELAY_THRESHOLD_MINUTES


def feature_cutoff(scheduled_departure_utc: datetime) -> datetime:
    """Instant T-2h : seules les informations connues à cet instant sont autorisées."""
    return scheduled_departure_utc - PREDICTION_HORIZON
