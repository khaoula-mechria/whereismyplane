from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from aeropulse import config
from aeropulse.api import predict_handler
from aeropulse.api.predict_service import PredictionService
from aeropulse.features.serving import (
    FeatureBuilder,
    InvalidRequestError,
    OutOfCoverageError,
)


def _tables(tmp_path: Path) -> Path:
    obs = pd.DataFrame(
        {
            "airport": ["JFK", "JFK", "JFK"],
            "observed_utc": pd.to_datetime(
                ["2024-03-14T10:51:00", "2024-03-14T11:51:00", "2024-03-14T12:51:00"]
            ),
            "temperature_c": [5.0, 6.0, 7.0],
            "dewpoint_c": [1.0, 2.0, 3.0],
            "wind_speed_mps": [3.0, 4.0, 5.0],
            "visibility_m": [9000.0, 9000.0, 9000.0],
            "ceiling_m": [900.0, 900.0, 900.0],
            "sea_level_pressure_hpa": [1010.0, 1011.0, 1012.0],
        }
    )
    routes = pd.DataFrame(
        {
            "origin": ["JFK"],
            "destination": ["LAX"],
            "distance_miles": [2475.0],
            "scheduled_elapsed_minutes": [360.0],
            "n_flights": [100],
        }
    )
    rows = []
    keys = {"carrier": "AA", "origin": "JFK", "route": "JFK-LAX", "origin_hour": "JFK|8"}
    for kind, key in keys.items():
        for d in range(1, 41):  # 40 jours avant le 14 mars 2024
            date = pd.Timestamp("2024-03-14") - pd.Timedelta(days=d)
            rows.append((kind, key, date, 40, 10))
        # le jour même : ne doit JAMAIS être compté (retards connus après coup)
        rows.append((kind, key, pd.Timestamp("2024-03-14"), 100, 100))
    history = pd.DataFrame(rows, columns=["kind", "key", "date", "n", "delayed"])
    obs.to_parquet(tmp_path / "observations.parquet", index=False)
    routes.to_parquet(tmp_path / "routes.parquet", index=False)
    history.to_parquet(tmp_path / "history_daily.parquet", index=False)
    return tmp_path


REQUEST: dict[str, Any] = {
    "airline": "aa",
    "origin": "jfk",
    "destination": "lax",
    "scheduled_departure": "2024-03-14T08:30:00-04:00",  # 12:30 UTC -> cutoff 10:30 UTC
}


def test_features_follow_contract_and_t2h_rules(tmp_path: Path) -> None:
    builder = FeatureBuilder(_tables(tmp_path))
    x = builder.build(REQUEST)
    assert list(x.columns) == list(config.FEATURE_COLUMNS)
    row = x.iloc[0]
    assert row["departure_hour"] == 8 and row["month"] == 3
    assert row["day_of_week"] == 4  # jeudi, convention du jeu : lundi = 1
    assert row["route"] == "JFK-LAX" and row["distance_miles"] == 2475.0
    # Cutoff 10:30 UTC : la plus récente observation <= cutoff n'existe pas (première à 10:51).
    assert bool(row["weather_missing"]) and pd.isna(row["temperature_c"])
    # 28 jours précédents, 40 vols et 10 retards par jour -> 0,25 ; le jour même est exclu.
    assert row["carrier_delay_rate_28d"] == pytest.approx(0.25)
    assert row["origin_hour_delay_rate_28d"] == pytest.approx(0.25)


def test_weather_is_last_observation_not_after_cutoff(tmp_path: Path) -> None:
    builder = FeatureBuilder(_tables(tmp_path))
    late = {**REQUEST, "scheduled_departure": "2024-03-14T10:00:00-04:00"}  # cutoff 12:00 UTC
    row = builder.build(late).iloc[0]
    assert row["temperature_c"] == 6.0  # observation de 11:51, jamais celle de 12:51
    assert row["weather_age_minutes"] == 9
    assert not bool(row["weather_missing"])


def test_history_hidden_below_minimum_sample(tmp_path: Path) -> None:
    builder = FeatureBuilder(_tables(tmp_path))
    far = {**REQUEST, "scheduled_departure": "2024-04-20T08:30:00-04:00"}  # fenêtre vide
    assert pd.isna(builder.build(far).iloc[0]["carrier_delay_rate_28d"])


@pytest.mark.parametrize(
    "patch",
    [
        {"extra": 1},
        {"airline": "QQ"},
        {"origin": "BOS"},
        {"destination": "ATL"},
        {"scheduled_departure": "2024-03-14T08:30:00"},  # sans fuseau
        {"scheduled_departure": "pas une date"},
        {"scheduled_departure": 12345},
        {"scheduled_elapsed_minutes": "300"},
        {"scheduled_elapsed_minutes": 5},
        {"airline": "AA'; DROP TABLE x;--"},
    ],
)
def test_invalid_inputs_are_rejected(tmp_path: Path, patch: dict[str, Any]) -> None:
    builder = FeatureBuilder(_tables(tmp_path))
    with pytest.raises(InvalidRequestError):
        builder.build({**REQUEST, **patch})


def test_long_flights_such_as_hawaii_are_accepted(tmp_path: Path) -> None:
    builder = FeatureBuilder(_tables(tmp_path))
    x = builder.build({**REQUEST, "scheduled_elapsed_minutes": 700})
    assert x.iloc[0]["scheduled_elapsed_minutes"] == 700.0
    with pytest.raises(InvalidRequestError):
        builder.build({**REQUEST, "scheduled_elapsed_minutes": 5000})


def test_missing_field_and_out_of_coverage(tmp_path: Path) -> None:
    builder = FeatureBuilder(_tables(tmp_path))
    with pytest.raises(InvalidRequestError):
        builder.build({k: v for k, v in REQUEST.items() if k != "origin"})
    with pytest.raises(OutOfCoverageError):
        builder.build({**REQUEST, "scheduled_departure": "2026-03-14T08:30:00-04:00"})
    with pytest.raises(OutOfCoverageError):
        builder.build({**REQUEST, "scheduled_departure": "2021-03-14T08:30:00-04:00"})


class FakeBackend:
    model_version = "clf-test"
    threshold = 0.2

    def predict(self, rows: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(
            {"delay_probability": [0.37] * len(rows), "is_delayed_predicted": [True] * len(rows)}
        )

    def explain(self, rows: pd.DataFrame, top_k: int = 5) -> list[dict[str, Any]]:
        item = {"feature": "departure_hour", "shap": 0.08, "direction": "augmente le risque"}
        return [{"contributions": [item, item, item]} for _ in range(len(rows))]


def _service(tmp_path: Path) -> PredictionService:
    return PredictionService(FeatureBuilder(_tables(tmp_path)), FakeBackend())


def _event(body: Any, **extra: Any) -> dict[str, Any]:
    return {"body": body if isinstance(body, str) else json.dumps(body), **extra}


def test_handler_returns_contract_without_delay_minutes(tmp_path: Path) -> None:
    res = predict_handler.handler(_event(REQUEST), service=_service(tmp_path))
    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["delay_probability"] == 0.37 and body["threshold"] == 0.2
    assert body["model_versions"] == {"classification": "clf-test"}
    assert len(body["explanation"]) >= 3 and "pas une cause" in body["disclaimer"]
    assert "expected_delay_minutes" not in body  # ADR-0017
    assert body["weather"]["missing"] is True


def test_handler_status_codes(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    bad_json = predict_handler.handler(_event("{pas du json"), service=svc)
    assert bad_json["statusCode"] == 400
    assert predict_handler.handler({"body": None}, service=svc)["statusCode"] == 400
    huge = predict_handler.handler(_event("x" * 5000), service=svc)
    assert huge["statusCode"] == 400
    out = predict_handler.handler(
        _event({**REQUEST, "scheduled_departure": "2026-03-14T08:30:00-04:00"}), service=svc
    )
    assert out["statusCode"] == 422
    assert json.loads(out["body"])["error"]["code"] == "out_of_coverage"
    encoded = base64.b64encode(json.dumps(REQUEST).encode()).decode()
    assert (
        predict_handler.handler(_event(encoded, isBase64Encoded=True), service=svc)["statusCode"]
        == 200
    )


def test_internal_errors_do_not_leak_details(tmp_path: Path) -> None:
    class Boom(FakeBackend):
        def predict(self, rows: pd.DataFrame) -> pd.DataFrame:
            raise RuntimeError("secret interne /chemin/vers/modele")

    svc = PredictionService(FeatureBuilder(_tables(tmp_path)), Boom())
    res = predict_handler.handler(_event(REQUEST), service=svc)
    assert res["statusCode"] == 500 and "secret" not in res["body"]
    assert np.isclose(0.0, 0.0)


def _replay_table(tmp_path: Path) -> Path:
    from aeropulse.data import serving_tables

    n = 3
    frame = pd.DataFrame(
        {
            "flight_date": ["2025-03-14"] * n,
            "carrier": ["AA"] * n,
            "flight_number": ["100", "100", "200"],
            "origin": ["JFK"] * n,
            "scheduled_departure_utc": pd.to_datetime(
                ["2025-03-14T12:30:00Z", "2025-03-14T20:30:00Z", "2025-03-14T12:30:00Z"]
            ),
        }
    )
    for col in config.FEATURE_COLUMNS:
        if col not in frame.columns:
            frame[col] = 1.0 if col in config.NUMERIC_FEATURES else "x"
    frame["is_delayed"] = pd.array([True, False, True], dtype="boolean")
    frame["split"] = "test"
    ml = tmp_path / "ml.parquet"
    frame.to_parquet(ml, index=False)
    assert serving_tables.build_replay(ml, tmp_path / "replay.parquet") == n
    return tmp_path


def test_flight_ids_use_local_time_and_must_be_unique(tmp_path: Path) -> None:
    from aeropulse.data import serving_tables

    ids = pd.read_parquet(_replay_table(tmp_path) / "replay.parquet")["flight_id"].tolist()
    assert ids == [
        "2025-03-14_AA100_JFK_0830",
        "2025-03-14_AA100_JFK_1630",
        "2025-03-14_AA200_JFK_0830",
    ]
    dup = pd.DataFrame(
        {
            "split": ["test", "test"],
            "flight_date": ["2025-03-14"] * 2,
            "carrier": ["AA"] * 2,
            "flight_number": ["100"] * 2,
            "origin": ["JFK"] * 2,
            "scheduled_departure_utc": pd.to_datetime(["2025-03-14T12:30:00Z"] * 2),
            "is_delayed": pd.array([True, False], dtype="boolean"),
        }
    )
    for col in config.FEATURE_COLUMNS:
        if col not in dup.columns:
            dup[col] = 1.0
    dup.to_parquet(tmp_path / "dup.parquet", index=False)
    with pytest.raises(ValueError):
        serving_tables.build_replay(tmp_path / "dup.parquet", tmp_path / "out.parquet")


def test_replay_mode_returns_observed_outcome_and_keeps_contract(tmp_path: Path) -> None:
    from aeropulse.features.serving import ReplayStore

    tables = _tables(tmp_path)
    _replay_table(tables)
    svc = PredictionService(FeatureBuilder(tables), FakeBackend(), ReplayStore(tables))
    res = predict_handler.handler(_event({"flight_id": "2025-03-14_aa100_jfk_0830"}), service=svc)
    body = json.loads(res["body"])
    assert res["statusCode"] == 200 and body["mode"] == "replay"
    assert body["observed"]["is_delayed"] is True and "historique" in body["observed"]["note"]
    assert "expected_delay_minutes" not in body and len(body["explanation"]) >= 3
    manual = json.loads(predict_handler.handler(_event(REQUEST), service=svc)["body"])
    assert manual["mode"] == "manual" and "observed" not in manual


def test_replay_rejects_bad_ids_unknown_flights_and_mixed_fields(tmp_path: Path) -> None:
    from aeropulse.features.serving import ReplayStore

    tables = _tables(tmp_path)
    _replay_table(tables)
    svc = PredictionService(FeatureBuilder(tables), FakeBackend(), ReplayStore(tables))

    def code(body: Any) -> int:
        return int(predict_handler.handler(_event(body), service=svc)["statusCode"])

    assert code({"flight_id": "2025-03-14_AA999_JFK_0830"}) == 404
    assert code({"flight_id": "n'importe quoi'; DROP TABLE"}) == 400
    assert code({"flight_id": 123}) == 400
    assert code({"flight_id": "2025-03-14_AA100_JFK_0830", "origin": "JFK"}) == 400
    assert code(["flight_id"]) == 400
    no_replay = PredictionService(FeatureBuilder(tables), FakeBackend())
    res = predict_handler.handler(
        _event({"flight_id": "2025-03-14_AA100_JFK_0830"}), service=no_replay
    )
    assert res["statusCode"] == 400
