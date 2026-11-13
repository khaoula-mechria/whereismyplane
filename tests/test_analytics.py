from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from aeropulse import config
from aeropulse.analytics import queries
from aeropulse.analytics.engine import Analytics


def _flights() -> pd.DataFrame:
    rows: list[tuple[Any, ...]] = []
    # AA : 40 vols éligibles JFK->LAX (10 retardés) + 1 annulé ; ZZ : 5 vols seulement
    for i in range(40):
        rows.append(("AA", "JFK", "LAX", i < 10, 20.0 if i < 10 else 0.0, False, False, True))
    rows.append(("AA", "JFK", "LAX", None, None, True, False, False))
    for _ in range(5):
        rows.append(("ZZ", "LGA", "BOS", True, 30.0, False, False, True))
    df = pd.DataFrame(
        rows,
        columns=[
            "carrier",
            "origin",
            "destination",
            "is_delayed",
            "departure_delay_minutes",
            "cancelled",
            "diverted",
            "ml_eligible",
        ],
    )
    df["is_delayed"] = df["is_delayed"].astype("boolean")
    df["flight_date"] = "2024-03-01"
    df["year"] = 2024
    df["month"] = 3
    return df


@pytest.fixture
def analytics(tmp_path: Path) -> Analytics:
    target = tmp_path / "flights"
    _flights().to_parquet(target, partition_cols=["year", "month"], index=False)
    return Analytics(target)


def test_statistics_by_carrier_with_sample_size(analytics: Analytics) -> None:
    res = analytics.statistics("carrier")
    aa = next(r for r in res["rows"] if r["carrier"] == "AA")
    assert aa["n_flights"] == 41 and aa["n_scored"] == 40 and aa["n_cancelled"] == 1
    assert aa["sufficient"] and aa["delay_rate"] == pytest.approx(0.25)
    assert res["source"] and aa["period"]["start"] == "2024-03-01"


def test_small_sample_returns_insufficient_data(analytics: Analytics) -> None:
    zz = next(r for r in analytics.statistics("carrier")["rows"] if r["carrier"] == "ZZ")
    assert zz["n_scored"] < config.MIN_SAMPLE_SIZE
    assert zz["delay_rate"] is None and zz["mean_departure_delay_min"] is None
    assert zz["note"] == "données insuffisantes"


def test_route_and_filters(analytics: Analytics) -> None:
    res = analytics.statistics("route", {"origin": "jfk", "year": 2024})
    assert [(r["origin"], r["destination"]) for r in res["rows"]] == [("JFK", "LAX")]


def test_rejects_unknown_dimension_filter_and_values(analytics: Analytics) -> None:
    bad: list[dict[str, object]] = [
        {"nope": 1},
        {"carrier": "AA'; DROP TABLE flights;--"},
        {"carrier": "QQ"},
        {"origin": "BOS"},
        {"month": 13},
        {"year": True},
        {"year": "2024"},
    ]
    for filters in bad:
        with pytest.raises(queries.InvalidParameterError):
            analytics.statistics("carrier", filters)
    with pytest.raises(queries.InvalidParameterError):
        analytics.statistics("carrier; DROP TABLE flights")


def test_limit_is_capped(analytics: Analytics) -> None:
    for limit in (0, queries.MAX_LIMIT + 1, -1):
        with pytest.raises(queries.InvalidParameterError):
            analytics.statistics("carrier", limit=limit)
    assert len(analytics.statistics("carrier", limit=1)["rows"]) == 1


def test_export_aggregates(analytics: Analytics, tmp_path: Path) -> None:
    counts = analytics.export_aggregates(tmp_path / "agg")
    assert counts == {"carrier": 2, "airport": 2, "route": 2}
    assert (tmp_path / "agg" / "route.parquet").exists()
