"""Contrôles de schéma et de qualité (CMP-02, NFR-08).

Compte de lignes, types, plages de valeurs ; échoue bruyamment plutôt que de corriger en silence.
"""

from __future__ import annotations

import pandas as pd

from aeropulse import config

KEY_COLUMNS = ("flight_date", "carrier", "flight_number", "origin", "scheduled_departure_utc")
REQUIRED_COLUMNS = (
    *KEY_COLUMNS,
    "destination",
    "distance_miles",
    "departure_delay_minutes",
    "cancelled",
    "diverted",
)
MAX_PLAUSIBLE_DELAY_MINUTES = 7 * 24 * 60  # 25 vols réels dépassent 24 h (max 2 590 min)


class ValidationError(ValueError):
    """Un contrôle bloquant a échoué ; les données ne sont pas écrites."""


def validate_raw(raw: pd.DataFrame, *, expected_rows: int | None = None) -> None:
    """Contrôles bloquants sur le fichier brut ; ``ValidationError`` listant toutes les erreurs."""
    errors: list[str] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        raise ValidationError(f"colonnes manquantes : {missing}")
    if expected_rows is not None and len(raw) != expected_rows:
        errors.append(f"{len(raw)} lignes, {expected_rows} attendues")
    if raw.empty:
        errors.append("aucune ligne")
    dup = int(raw.duplicated(list(KEY_COLUMNS)).sum())
    if dup:
        errors.append(f"{dup} doublons de clé")
    if raw["scheduled_departure_utc"].isna().any():
        errors.append("scheduled_departure_utc manquant")
    unknown = sorted(set(raw["origin"].dropna()) - set(config.AIRPORTS))
    if unknown:
        errors.append(f"aéroports hors périmètre : {unknown}")
    dates = pd.to_datetime(raw["flight_date"])
    start, end = pd.Timestamp(config.STUDY_START), pd.Timestamp(config.STUDY_END)
    if bool(((dates < start) | (dates > end)).any()):
        errors.append(f"dates hors de {config.STUDY_START} → {config.STUDY_END}")
    delay = pd.to_numeric(raw["departure_delay_minutes"], errors="coerce")
    if bool((delay.abs() > MAX_PLAUSIBLE_DELAY_MINUTES).any()):
        errors.append("retards au départ de plus de 7 jours")
    if errors:
        raise ValidationError("; ".join(errors))
