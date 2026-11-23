"""Script d'opérations AWS : parties testables sans compte (clés S3, publication, requêtes)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from aeropulse.features.serving import FeatureBuilder, ReplayStore
from aeropulse.mlops.store import BundleStore
from test_bundle import make_release, make_serving
from test_mlops_aws import Clock, FakeS3

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "aws"))
import aeropulse_aws as ops  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def test_partition_keys_are_deterministic(tmp_path: Path) -> None:
    for month in (1, 10):
        part = tmp_path / "year=2024" / f"month={month}"
        part.mkdir(parents=True)
        (part / f"uuid{month}-0.parquet").write_bytes(b"x")
    keys = [k for _, k in ops.partition_keys(tmp_path, "processed/flights/")]
    assert keys == [
        "processed/flights/year=2024/month=1/part-0.parquet",
        "processed/flights/year=2024/month=10/part-0.parquet",
    ]


def test_raw_keys_keep_layout_and_require_data(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        ops.raw_keys(tmp_path)
    (tmp_path / "nyc_flight_delays_ml.parquet").write_bytes(b"p")
    (tmp_path / "noaa" / "2024").mkdir(parents=True)
    (tmp_path / "noaa" / "2024" / "74486094789.csv").write_bytes(b"c")
    keys = [k for _, k in ops.raw_keys(tmp_path)]
    assert keys == ["raw/nyc_flight_delays_ml.parquet", "raw/noaa/2024/74486094789.csv"]


def test_publish_bundle_is_loadable_by_the_lambda_store(tmp_path: Path) -> None:
    s3 = FakeS3()
    src = tmp_path / "src"
    first = ops.publish_bundle(s3, "b", make_release(src), make_serving(src), "bootstrap-local")
    assert ("b", "releases/previous.json") not in s3.objects
    info = BundleStore(s3, "b", tmp_path / "cache", clock=Clock()).current()
    assert info.model_version == first["model_version"]
    src2 = tmp_path / "src2"
    ops.publish_bundle(s3, "b", make_release(src2, b'{"m": 9}'), make_serving(src2), "bootstrap")
    previous = json.loads(s3.objects[("b", "releases/previous.json")])
    assert previous["model_version"] == first["model_version"]  # retour arrière possible


@pytest.mark.skipif(
    not (ROOT / "data" / "serving" / "replay.parquet").exists(),
    reason="tables de service locales absentes (données non versionnées)",
)
def test_smoke_requests_are_valid_for_the_real_tables() -> None:
    serving = ROOT / "data" / "serving"
    replay, manual = ops.sample_requests(serving)
    features, _ = ReplayStore(serving).get(replay)
    built = FeatureBuilder(serving).build(manual)
    for column in ("carrier", "origin", "destination", "departure_hour"):
        assert str(built[column].iloc[0]) == str(features[column].iloc[0])
