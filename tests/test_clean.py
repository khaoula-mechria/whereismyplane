from __future__ import annotations

import pandas as pd
import pytest

from aeropulse.data import clean, validate, weather


def _raw() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "flight_date": ["2024-01-01"] * 5,
            "carrier": ["AA"] * 5,
            "flight_number": ["1", "2", "3", "4", "5"],
            "origin": ["JFK"] * 5,
            "destination": ["LAX"] * 5,
            "scheduled_departure_utc": pd.to_datetime(["2024-01-01T05:00:00Z"] * 5),
            "scheduled_elapsed_minutes": ["300"] * 5,
            "distance_miles": ["2475"] * 5,
            "departure_delay_minutes": ["15", "16", "-3", None, "40"],
            "arrival_delay_minutes": ["0"] * 5,
            "departure_delayed_15": [True, True, False, None, True],
            "cancelled": [False, False, False, True, False],
            "diverted": [False, False, False, False, True],
            "month": [1] * 5,
            "temperature_c": ["99"] * 5,  # météo T-1h du fichier : doit disparaître
            "weather_observed_utc": pd.to_datetime(["2024-01-01T03:59:00Z"] * 5),
        }
    )


def _obs() -> pd.DataFrame:
    obs = pd.DataFrame(
        {
            "weather_station": ["74486094789"],
            "observed_utc": pd.to_datetime(["2024-01-01T02:51:00"]),
            "temperature_c": [5.6],
            "dewpoint_c": [1.0],
            "wind_speed_mps": [4.0],
            "visibility_m": [16000.0],
            "ceiling_m": [1500.0],
            "sea_level_pressure_hpa": [1016.0],
        }
    )
    obs["airport"] = "JFK"
    return obs


def test_target_is_strict_and_ml_eligibility() -> None:
    out = clean.prepare_flights(_raw(), _obs())
    assert out["is_delayed"].tolist()[:3] == [False, True, False]  # 15 min pile : non retardé
    assert out["is_delayed"].iloc[3] is pd.NA and out["is_delayed"].iloc[4] is pd.NA
    assert out["ml_eligible"].tolist() == [True, True, True, False, False]


def test_source_weather_is_replaced_by_t2h_weather() -> None:
    out = clean.prepare_flights(_raw(), _obs())
    assert (out["temperature_c"] == 5.6).all()  # NOAA, pas la valeur 99 du fichier
    assert (out["feature_cutoff_utc"] == pd.Timestamp("2024-01-01T03:00:00")).all()
    assert (out["weather_age_minutes"] == 9).all()
    assert not out["weather_missing"].any()
    assert len(out) == 5 and out["year"].eq(2024).all()


def test_validate_rejects_duplicates_and_unknown_airport() -> None:
    raw = _raw()
    raw.loc[1, "flight_number"] = "1"
    raw.loc[2, "origin"] = "BOS"
    with pytest.raises(validate.ValidationError, match="doublons.*hors périmètre"):
        validate.validate_raw(raw)


def test_validate_accepts_clean_input_and_checks_row_count() -> None:
    validate.validate_raw(_raw(), expected_rows=5)
    with pytest.raises(validate.ValidationError):
        validate.validate_raw(_raw(), expected_rows=6)


def test_join_columns_exposed() -> None:
    assert "sea_level_pressure_hpa" in weather.WEATHER_COLUMNS
