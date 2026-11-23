"""Routes déployées sur AWS : santé, indisponibilité du modèle, statistiques et listes (T7.2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from aeropulse import config
from aeropulse.analytics.engine import Analytics
from aeropulse.api import predict_handler, stats_handler
from aeropulse.data import pipeline as data_pipeline
from aeropulse.mlops import prepare_job
from aeropulse.mlops.store import BundleUnavailableError


class FakeService:
    model_version = "clf-test"
    modes = ["manual", "replay"]

    def handle(self, request: Any) -> dict[str, Any]:
        return {"ok": True}


def test_health_reports_loaded_model_version() -> None:
    res = predict_handler.handler({"httpMethod": "GET"}, service=FakeService())  # type: ignore[arg-type]
    body = json.loads(res["body"])
    assert res["statusCode"] == 200 and body["model_versions"] == {"classification": "clf-test"}
    assert body["prediction_modes"] == ["manual", "replay"]


def test_missing_bundle_gives_503_with_correlation_id(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable() -> Any:
        raise BundleUnavailableError("s3")

    monkeypatch.setattr(predict_handler, "get_service", unavailable)
    event = {"httpMethod": "POST", "body": "{}", "requestContext": {"requestId": "req-1"}}
    res = predict_handler.handler(event)
    err = json.loads(res["body"])["error"]
    assert res["statusCode"] == 503 and err["code"] == "model_unavailable"
    assert err["correlation_id"] == "req-1" and "s3" not in res["body"]


@pytest.fixture
def engine(tmp_path: Path) -> Analytics:
    rows = [("AA", "JFK", "LAX", i < 10, 20.0 if i < 10 else 0.0) for i in range(40)]
    rows += [("ZZ", "LGA", "BOS", True, 30.0) for _ in range(5)]
    df = pd.DataFrame(
        rows, columns=["carrier", "origin", "destination", "is_delayed", "departure_delay_minutes"]
    )
    df["is_delayed"] = df["is_delayed"].astype("boolean")
    df["cancelled"] = False
    df["diverted"] = False
    df["ml_eligible"] = True
    df["flight_date"] = "2024-03-01"
    df["year"] = 2024
    df["month"] = 3
    df.to_parquet(tmp_path / "flights", partition_cols=["year", "month"], index=False)
    prepare_job.deterministic_names(tmp_path / "flights")  # même disposition que sur S3
    return Analytics(tmp_path / "flights")


def _get(resource: str, engine: Analytics, **extra: Any) -> tuple[int, dict[str, Any]]:
    res = stats_handler.handler({"httpMethod": "GET", "resource": resource, **extra}, engine=engine)
    return int(res["statusCode"]), json.loads(res["body"])


def test_stats_route_with_filters_and_limit(engine: Analytics) -> None:
    status, body = _get(
        "/v1/stats/{dimension}",
        engine,
        pathParameters={"dimension": "carrier"},
        queryStringParameters={"origin": "jfk", "year": "2024", "limit": "5"},
    )
    assert status == 200 and body["limit"] == 5
    (row,) = body["rows"]
    assert row["carrier"] == "AA" and row["delay_rate"] == pytest.approx(0.25)


def test_stats_under_30_flights_are_not_reported(engine: Analytics) -> None:
    _, body = _get("/v1/stats/{dimension}", engine, pathParameters={"dimension": "carrier"})
    zz = next(r for r in body["rows"] if r["carrier"] == "ZZ")
    assert zz["delay_rate"] is None and zz["note"] == "données insuffisantes"


@pytest.mark.parametrize(
    "params",
    [
        {"dimension": "pilot"},
        {"dimension": "carrier", "q": {"sql": "DROP TABLE flights"}},
        {"dimension": "carrier", "q": {"origin": "XXX"}},
        {"dimension": "carrier", "q": {"limit": "1000"}},
        {"dimension": "carrier", "q": {"year": "deux mille"}},
    ],
)
def test_invalid_stats_parameters_give_400(engine: Analytics, params: dict[str, Any]) -> None:
    status, body = _get(
        "/v1/stats/{dimension}",
        engine,
        pathParameters={"dimension": params["dimension"]},
        queryStringParameters=params.get("q"),
    )
    assert status == 400 and body["error"]["code"] == "invalid_parameter"


def test_meta_lists_allowed_values(engine: Analytics) -> None:
    status, body = _get("/v1/meta", engine)
    assert status == 200 and body["airports"] == ["EWR", "JFK", "LGA"]
    assert body["carriers"] == ["AA", "ZZ"] and body["min_sample_size"] == 30


def test_unknown_route_and_method(engine: Analytics) -> None:
    assert _get("/v1/other", engine)[0] == 404
    res = stats_handler.handler({"httpMethod": "POST", "resource": "/v1/meta"}, engine=engine)
    assert res["statusCode"] == 405


def test_prepare_job_applies_max_weather_age(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-20 : l'étape Prepare doit imposer l'âge maximal de la météo (défaut de run() = aucun)."""
    seen: dict[str, Any] = {}

    class Stop(Exception):
        pass

    def fake_run(*args: Any, **kwargs: Any) -> dict[str, object]:
        seen.update(kwargs)
        raise Stop

    monkeypatch.setattr(data_pipeline, "run", fake_run)
    with pytest.raises(Stop):
        prepare_job.run(tmp_path / "raw", tmp_path / "out", expected_rows=None)
    assert seen["max_weather_age"] == pd.Timedelta(config.MAX_WEATHER_AGE)


def test_deterministic_names_make_reruns_overwrite(tmp_path: Path) -> None:
    part = tmp_path / "flights" / "year=2024" / "month=3"
    part.mkdir(parents=True)
    (part / "b1c2-0.parquet").write_bytes(b"1")
    assert prepare_job.deterministic_names(tmp_path / "flights") == 1
    assert [p.name for p in part.iterdir()] == ["part-0.parquet"]
