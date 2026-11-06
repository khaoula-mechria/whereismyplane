from datetime import UTC, datetime, timedelta

import pytest

from aeropulse import config


def test_delay_threshold_is_strict() -> None:
    assert not config.is_delayed(15.0)
    assert config.is_delayed(15.01)
    assert not config.is_delayed(-30.0)  # départ en avance conservé, jamais « retardé »


def test_cutoff_is_two_hours_before_departure() -> None:
    departure = datetime(2024, 3, 10, 12, 30, tzinfo=UTC)
    assert departure - config.feature_cutoff(departure) == timedelta(hours=2)


def test_forbidden_columns_detected_case_insensitive() -> None:
    cols = ["origin", "DepDelay", "arrival_delay_minutes", "distance_miles"]
    assert config.forbidden_columns_in(cols) == ["DepDelay", "arrival_delay_minutes"]
    with pytest.raises(config.LeakageError):
        config.assert_no_forbidden_columns(cols)


def test_allowed_columns_pass() -> None:
    config.assert_no_forbidden_columns(
        ["carrier", "origin", "destination", "scheduled_departure_hhmm", "distance_miles"]
    )


def test_target_and_outcomes_are_forbidden_as_features() -> None:
    for name in ("dep_delay", "is_delayed", "cancelled", "diverted", "ArrDelay", "WeatherDelay"):
        assert name.lower() in config.FORBIDDEN_FEATURE_COLUMNS


def test_study_scope_and_stations() -> None:
    assert set(config.NOAA_STATIONS) == set(config.AIRPORTS)
    assert config.STUDY_START < config.STUDY_END
    assert config.MIN_SAMPLE_SIZE == 30
