from __future__ import annotations

import pandas as pd
import pytest

from aeropulse.data import weather


def _raw() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "STATION": ["74486094789"] * 3,
            "DATE": ["2024-01-01T00:51:00", "2024-01-01T01:51:00", "2024-01-01T02:51:00"],
            "TMP": ["+0056,5", "+9999,9", "+0100,3"],
            "DEW": ["-0028,5", "-0030,1", "-0030,1"],
            "WND": ["260,5,N,0041,5", "999,9,9,9999,9", "260,5,N,0050,5"],
            "VIS": ["016093,5,N,5", "999999,9,9,9", "010000,1,N,1"],
            "CIG": ["01524,5,M,N", "99999,9,9,N", "00300,1,M,N"],
            "SLP": ["10163,5", "99999,9", "10150,1"],
        }
    )


def _obs() -> pd.DataFrame:
    obs = weather.decode_observations(_raw())
    obs["airport"] = "JFK"
    return obs


def _flights(dep: str, origin: str = "JFK") -> pd.DataFrame:
    return pd.DataFrame({"origin": [origin], "scheduled_departure_utc": pd.to_datetime([dep])})


def test_decode_units_and_missing() -> None:
    out = weather.decode_observations(_raw())
    assert out["temperature_c"].iloc[0] == pytest.approx(5.6)
    assert out["wind_speed_mps"].iloc[0] == pytest.approx(4.1)
    assert out["visibility_m"].iloc[0] == 16093
    assert out["sea_level_pressure_hpa"].iloc[0] == pytest.approx(1016.3)
    missing = ["temperature_c", "wind_speed_mps", "visibility_m", "ceiling_m"]
    assert out.loc[1, missing].isna().all()
    assert pd.isna(out["temperature_c"].iloc[2])  # qualité 3 = erroné


def test_asof_takes_last_observation_not_after_cutoff() -> None:
    # départ 03:30 -> cutoff 01:30 -> dernière observation <= 01:30 : celle de 00:51
    out = weather.join_weather_at_cutoff(_flights("2024-01-01T03:30:00"), _obs())
    assert out["weather_observed_utc"].iloc[0] == pd.Timestamp("2024-01-01T00:51:00")
    assert out["weather_age_minutes"].iloc[0] == pytest.approx(39)
    weather.assert_no_future_weather(out)


def test_asof_exact_cutoff_is_included() -> None:
    out = weather.join_weather_at_cutoff(_flights("2024-01-01T03:51:00"), _obs())
    assert out["weather_observed_utc"].iloc[0] == pd.Timestamp("2024-01-01T01:51:00")


def test_other_airport_gets_no_weather() -> None:
    out = weather.join_weather_at_cutoff(_flights("2024-01-01T03:30:00", "LGA"), _obs())
    assert out["weather_observed_utc"].isna().all()
    assert out["temperature_c"].isna().all()


def test_max_age_masks_old_observation() -> None:
    out = weather.join_weather_at_cutoff(
        _flights("2024-01-01T03:30:00"), _obs(), max_age=pd.Timedelta(minutes=30)
    )
    assert out["weather_observed_utc"].isna().all()


def test_assert_no_future_weather_detects_leak() -> None:
    bad = pd.DataFrame(
        {
            "feature_cutoff_utc": pd.to_datetime(["2024-01-01T01:00:00"]),
            "weather_observed_utc": pd.to_datetime(["2024-01-01T01:30:00"]),
        }
    )
    with pytest.raises(ValueError):
        weather.assert_no_future_weather(bad)
