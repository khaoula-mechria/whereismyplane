"""Statistiques historiques ordonnées dans le temps (T3.5, AC-04).

Calculées uniquement sur le passé strict de chaque vol : seuls les vols des **jours locaux
précédents** (fenêtre ``config.HISTORY_WINDOW_DAYS``) comptent, jamais ceux du jour même (le
retard d'un vol du matin n'est pas connu à T-2h d'un vol de midi de façon fiable). En dessous de
``config.MIN_SAMPLE_SIZE`` vols dans la fenêtre, la statistique est absente (NaN).
"""

from __future__ import annotations

import pandas as pd

from aeropulse import config

_GROUPS = {
    "carrier_delay_rate_28d": ["carrier"],
    "origin_delay_rate_28d": ["origin"],
    "route_delay_rate_28d": ["route"],
    "origin_hour_delay_rate_28d": ["origin", "departure_hour"],
}


def _rate_for_group(frame: pd.DataFrame, keys: list[str]) -> pd.Series:
    """Taux de retard sur les jours précédents (fenêtre glissante), aligné sur ``frame.index``."""
    window = f"{config.HISTORY_WINDOW_DAYS}D"
    scored = frame[frame["ml_eligible"]]
    daily = (
        scored.groupby([*keys, "_date"])["is_delayed"]
        .agg(delayed=lambda s: int(s.astype(bool).sum()), n="size")
        .reset_index()
        .sort_values("_date")
    )
    parts: list[pd.DataFrame] = []
    for _, g in daily.groupby(keys, sort=False):
        g = g.set_index("_date")
        rolled = g[["delayed", "n"]].rolling(window, closed="left").sum()  # exclut le jour même
        rolled = rolled.reset_index()
        for k in keys:
            rolled[k] = g[k].iloc[0]
        parts.append(rolled)
    keys_date = [*keys, "_date"]
    if not parts:
        return pd.Series(float("nan"), index=frame.index)
    stats = pd.concat(parts, ignore_index=True)
    rate = (stats["delayed"] / stats["n"]).where(stats["n"] >= config.MIN_SAMPLE_SIZE)
    lookup = stats[keys_date].assign(rate=rate)
    merged = frame[keys_date].merge(lookup, on=keys_date, how="left")
    return pd.Series(merged["rate"].to_numpy(), index=frame.index)


def add_history_features(flights: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les taux de retard historiques (jours précédents uniquement)."""
    out = flights.copy()
    out["_date"] = pd.to_datetime(out["flight_date"]).dt.normalize()
    for name, keys in _GROUPS.items():
        out[name] = _rate_for_group(out, keys)
    return out.drop(columns="_date")
