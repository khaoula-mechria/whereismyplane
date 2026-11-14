"""Variables calendaires et horaires connues à T-2h (T3.3).

Heure, jour de semaine, saison, jour férié américain : tout est connu à l'avance.
"""

from __future__ import annotations

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

_SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring"}
_SEASONS |= {6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}


def add_temporal_features(flights: pd.DataFrame) -> pd.DataFrame:
    out = flights.copy()
    dates = pd.to_datetime(out["flight_date"]).dt.normalize()
    out["is_weekend"] = dates.dt.day_of_week >= 5
    out["season"] = dates.dt.month.map(_SEASONS)
    holidays = USFederalHolidayCalendar().holidays(
        start=dates.min() - pd.Timedelta(days=1), end=dates.max() + pd.Timedelta(days=1)
    )
    out["is_holiday"] = dates.isin(holidays)
    out["route"] = out["origin"].astype(str) + "-" + out["destination"].astype(str)
    return out
