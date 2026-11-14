"""Variables météo connues à T-2h (T3.4, ADR-0009).

La jointure (dernière observation ≤ T-2h, âge maximal ``config.MAX_WEATHER_AGE``) est faite dans
``aeropulse.data.weather`` / ``clean`` ; ici : variables dérivées et garde-fou anti-fuite.
"""

from __future__ import annotations

import pandas as pd

from aeropulse.data.weather import assert_no_future_weather


def add_weather_features(flights: pd.DataFrame) -> pd.DataFrame:
    """Ajoute l'écart température–point de rosée ; vérifie qu'aucune observation n'est > T-2h."""
    assert_no_future_weather(flights)
    out = flights.copy()
    out["dewpoint_spread_c"] = out["temperature_c"] - out["dewpoint_c"]
    out["weather_missing"] = out["weather_missing"].astype(bool)
    return out
