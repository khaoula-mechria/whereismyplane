"""Tests de non-fuite et cas construits (T3.7, AC-03, AC-04)."""

from __future__ import annotations

import pandas as pd
import pytest

from aeropulse import config
from aeropulse.data import clean
from aeropulse.features import build, history, split


def test_feature_contract_has_no_forbidden_column() -> None:
    assert config.forbidden_columns_in(config.FEATURE_COLUMNS) == []
    assert config.TARGET_CLASSIFICATION not in config.FEATURE_COLUMNS
    assert config.TARGET_REGRESSION not in config.FEATURE_COLUMNS


def _history_frame(days: int = 40, per_day: int = 40) -> pd.DataFrame:
    rows = []
    for d in range(days):
        date = (pd.Timestamp("2024-01-01") + pd.Timedelta(days=d)).strftime("%Y-%m-%d")
        for i in range(per_day):
            rows.append(
                {
                    "flight_date": date,
                    "carrier": "AA",
                    "origin": "JFK",
                    "destination": "LAX",
                    "route": "JFK-LAX",
                    "departure_hour": 8,
                    "ml_eligible": True,
                    "is_delayed": (i % 2 == 0),
                }
            )
    return pd.DataFrame(rows)


def test_history_uses_strictly_previous_days_only() -> None:
    base = _history_frame()
    out = history.add_history_features(base)
    day1 = out[out["flight_date"] == "2024-01-02"]
    # un seul jour passé (40 vols >= 30) : taux = 0,5 ; le jour même est exclu
    assert day1["carrier_delay_rate_28d"].iloc[0] == pytest.approx(0.5)
    first_day = out[out["flight_date"] == "2024-01-01"]
    assert first_day["carrier_delay_rate_28d"].isna().all()  # aucun passé


def test_changing_the_future_does_not_change_past_features() -> None:
    base = _history_frame()
    altered = base.copy()
    altered.loc[altered["flight_date"] >= "2024-02-01", "is_delayed"] = True  # futur modifié
    a = history.add_history_features(base)
    b = history.add_history_features(altered)
    past = a["flight_date"] < "2024-02-01"
    cols = [c for c in a.columns if c.endswith("_28d")]
    pd.testing.assert_frame_equal(a.loc[past, cols], b.loc[past, cols])


def test_history_hides_small_samples() -> None:
    small = _history_frame(days=5, per_day=5)  # 5 vols par jour < 30
    out = history.add_history_features(small)
    assert out["carrier_delay_rate_28d"].isna().all()


def test_split_is_chronological_and_test_is_guarded() -> None:
    dates = pd.Series(["2023-01-01", "2024-06-30", "2024-07-01", "2024-12-31", "2025-01-01"])
    assert split.assign_split(dates).tolist() == [
        "train",
        "train",
        "validation",
        "validation",
        "test",
    ]
    with pytest.raises(ValueError):
        split.assign_split(pd.Series(["2025-08-01"]))
    df = pd.DataFrame({"split": ["train", "test"]})
    with pytest.raises(PermissionError):
        split.select_split(df, "test")
    assert len(split.select_split(df, "test", final_evaluation=True)) == 1


def test_split_periods_do_not_overlap_and_are_ordered() -> None:
    assert config.TRAIN_END < config.VALIDATION_START
    assert config.VALIDATION_END < config.TEST_START
    assert config.TEST_END <= config.STUDY_END


def test_weather_after_cutoff_is_rejected_and_old_weather_is_masked() -> None:
    flights = pd.DataFrame(
        {
            "flight_date": ["2024-01-01"],
            "origin": ["JFK"],
            "scheduled_departure_utc": pd.to_datetime(["2024-01-01T12:00:00Z"]),
            "scheduled_elapsed_minutes": ["300"],
            "distance_miles": ["2475"],
            "departure_delay_minutes": ["20"],
            "arrival_delay_minutes": ["0"],
            "cancelled": [False],
            "diverted": [False],
        }
    )
    obs = pd.DataFrame(
        {
            "airport": ["JFK"],
            "observed_utc": pd.to_datetime(["2024-01-01T09:00:00"]),  # 60 min avant le cutoff 10:00
            "weather_station": ["74486094789"],
            "temperature_c": [1.0],
            "dewpoint_c": [0.0],
            "wind_speed_mps": [3.0],
            "visibility_m": [9000.0],
            "ceiling_m": [900.0],
            "sea_level_pressure_hpa": [1010.0],
        }
    )
    out = clean.prepare_flights(flights, obs)
    assert out["weather_age_minutes"].iloc[0] == 60
    masked = clean.prepare_flights(flights, obs, max_weather_age=pd.Timedelta(minutes=30))
    assert bool(masked["weather_missing"].iloc[0]) and pd.isna(masked["temperature_c"].iloc[0])


def test_build_dataset_has_only_contract_columns_and_eligible_rows() -> None:
    frame = _history_frame(days=3, per_day=4)
    frame["flight_number"] = "1"
    frame["scheduled_departure_utc"] = pd.Timestamp("2024-01-01T12:00:00Z")
    frame["departure_delay_minutes"] = 20.0
    frame["cancelled"] = False
    frame["diverted"] = False
    frame["scheduled_elapsed_minutes"] = 300.0
    frame["distance_miles"] = 2475.0
    frame["month"] = 1
    frame["day_of_week"] = 0
    for c in ("temperature_c", "dewpoint_c", "wind_speed_mps", "visibility_m", "ceiling_m"):
        frame[c] = 1.0
    frame["sea_level_pressure_hpa"] = 1010.0
    frame["weather_age_minutes"] = 10.0
    frame["weather_missing"] = False
    frame["weather_observed_utc"] = pd.Timestamp("2024-01-01T09:00:00")
    frame["feature_cutoff_utc"] = pd.Timestamp("2024-01-01T10:00:00")
    frame.loc[0, "ml_eligible"] = False
    out = build.build_ml_dataset(frame)
    assert len(out) == len(frame) - 1
    assert out.columns.is_unique
    assert set(config.FEATURE_COLUMNS) <= set(out.columns)
    assert config.forbidden_columns_in(config.FEATURE_COLUMNS) == []
    assert (out["split"] == "train").all()
