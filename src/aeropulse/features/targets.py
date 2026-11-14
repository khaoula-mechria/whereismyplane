"""Cibles : is_delayed (dep_delay > 15) et retard en minutes (T3.2, FR-06).

Utilise le seuil de config.py ; ne duplique pas la valeur. Seuls les vols éligibles au ML
(ni annulés ni déroutés, retard renseigné — D-19) ont une cible.
"""

from __future__ import annotations

import pandas as pd

from aeropulse import config


def add_targets(flights: pd.DataFrame) -> pd.DataFrame:
    """Ajoute ``is_delayed`` (booléen) et ``dep_delay`` (minutes) ; NaN hors ``ml_eligible``."""
    out = flights.copy()
    eligible = out["ml_eligible"].astype(bool)
    delay = pd.to_numeric(out["departure_delay_minutes"], errors="coerce").astype("float64")
    out[config.TARGET_REGRESSION] = delay.where(eligible)
    out[config.TARGET_CLASSIFICATION] = pd.array(
        [bool(config.is_delayed(x)) if ok else None for x, ok in zip(delay, eligible, strict=True)],
        dtype="boolean",
    )
    return out
