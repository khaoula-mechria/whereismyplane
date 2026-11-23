"""Chargement S3, promotion et garde-fou, avec de faux clients AWS (aucun appel réseau)."""

from __future__ import annotations

import io
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from aeropulse.mlops import guard, promote
from aeropulse.mlops.bundle import IntegrityError, extract_bundle
from aeropulse.mlops.bundle import make_archive as tar_dir
from aeropulse.mlops.store import BundleStore, BundleUnavailableError, Pointer, PrefixSync
from test_bundle import make_archive


class FakeS3:
    """Sous-ensemble du client S3 : objets en mémoire, fichiers copiés depuis/vers le disque."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.downloads = 0
        self.fail = False

    def put(self, bucket: str, key: str, data: bytes) -> None:
        self.objects[(bucket, key)] = data

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if self.fail or (Bucket, Key) not in self.objects:
            raise KeyError(Key)
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def download_file(self, Bucket: str, Key: str, Filename: str) -> None:
        if self.fail:
            raise ConnectionError("réseau")
        self.downloads += 1
        Path(Filename).write_bytes(self.objects[(Bucket, Key)])

    def upload_file(self, Filename: str, Bucket: str, Key: str) -> None:
        self.objects[(Bucket, Key)] = Path(Filename).read_bytes()

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str = "") -> None:
        self.objects[(Bucket, Key)] = Body

    def get_paginator(self, name: str) -> Any:
        s3 = self

        class Paginator:
            def paginate(self, *, Bucket: str, Prefix: str) -> list[dict[str, Any]]:
                keys = [k for (b, k) in s3.objects if b == Bucket and k.startswith(Prefix)]
                return [{"Contents": [{"Key": k} for k in sorted(keys)]}]

        return Paginator()


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def publish(s3: FakeS3, tmp_path: Path, model: bytes = b'{"model": 1}') -> str:
    work = tmp_path / f"pub-{len(s3.objects)}"
    work.mkdir()
    archive, digest = make_archive(work, model)
    version = extract_bundle(archive, work / "check").model_version
    key = f"releases/{version}/bundle.tar.gz"
    s3.put("b", key, archive.read_bytes())
    pointer = {"model_version": version, "bundle_key": key, "sha256": digest}
    s3.put("b", "releases/current.json", json.dumps(pointer).encode())
    return version


def test_store_loads_then_caches_until_refresh(tmp_path: Path) -> None:
    s3, clock = FakeS3(), Clock()
    v1 = publish(s3, tmp_path)
    store = BundleStore(s3, "b", tmp_path / "cache", refresh_seconds=300, clock=clock)
    assert store.current().model_version == v1
    clock.now = 100
    assert store.current().model_version == v1 and s3.downloads == 1  # pas de relecture
    v2 = publish(s3, tmp_path, b'{"model": 2}')
    clock.now = 200
    assert store.current().model_version == v1  # délai pas écoulé
    clock.now = 301
    info = store.current()
    assert info.model_version == v2 and s3.downloads == 2
    assert (info.release_dir / "classifier.json").read_bytes() == b'{"model": 2}'


def test_store_keeps_serving_last_good_bundle_when_s3_fails(tmp_path: Path) -> None:
    s3, clock = FakeS3(), Clock()
    v1 = publish(s3, tmp_path)
    store = BundleStore(s3, "b", tmp_path / "cache", clock=clock)
    store.current()
    s3.fail = True
    clock.now = 10_000
    assert store.current().model_version == v1


def test_store_without_any_bundle_is_unavailable(tmp_path: Path) -> None:
    store = BundleStore(FakeS3(), "b", tmp_path / "cache", clock=Clock())
    with pytest.raises(BundleUnavailableError):
        store.current()


def test_store_refuses_archive_not_matching_pointer(tmp_path: Path) -> None:
    s3 = FakeS3()
    publish(s3, tmp_path)
    pointer = json.loads(s3.objects[("b", "releases/current.json")])
    pointer["sha256"] = "0" * 64
    s3.put("b", "releases/current.json", json.dumps(pointer).encode())
    with pytest.raises(BundleUnavailableError):
        BundleStore(s3, "b", tmp_path / "cache", clock=Clock()).current()


@pytest.mark.parametrize(
    "raw",
    [
        b"pas du json",
        b'{"model_version": "x"}',
        b'{"model_version":"x","bundle_key":"../k","sha256":"s"}',
    ],
)
def test_invalid_pointers_are_refused(raw: bytes) -> None:
    with pytest.raises(BundleUnavailableError):
        Pointer.parse(raw)


def test_prefix_sync_copies_only_the_prefix(tmp_path: Path) -> None:
    s3 = FakeS3()
    s3.put("b", "processed/flights/year=2024/month=3/part-0.parquet", b"p")
    s3.put("b", "processed/report.json", b"r")
    s3.put("b", "raw/x.parquet", b"x")
    n = PrefixSync(s3, "b", "processed/flights", tmp_path / "f").sync()
    assert n == 1 and (tmp_path / "f" / "year=2024/month=3/part-0.parquet").read_bytes() == b"p"
    with pytest.raises(BundleUnavailableError):
        PrefixSync(s3, "b", "vide/", tmp_path / "g").sync()


# --- promotion ------------------------------------------------------------------------------


class FakeSageMaker:
    def __init__(self, model_data_url: str) -> None:
        self.url = model_data_url

    def describe_model_package(self, *, ModelPackageName: str) -> dict[str, Any]:
        return {"InferenceSpecification": {"Containers": [{"ModelDataUrl": self.url}]}}


def _event(group: str = "grp", status: str = "Approved") -> dict[str, Any]:
    return {
        "detail": {
            "ModelPackageGroupName": group,
            "ModelApprovalStatus": status,
            "ModelPackageArn": "arn:aws:sagemaker:us-east-1:1:model-package/grp/3",
        }
    }


def test_only_approvals_of_the_project_group_are_promoted() -> None:
    assert promote.approved_package_arn(_event(), "grp") is not None
    assert promote.approved_package_arn(_event(group="autre"), "grp") is None
    assert promote.approved_package_arn(_event(status="PendingManualApproval"), "grp") is None
    assert promote.approved_package_arn({}, "grp") is None


def test_promotion_copies_verified_bundle_and_keeps_previous_pointer(tmp_path: Path) -> None:
    s3 = FakeS3()
    publish(s3, tmp_path)  # pointeur existant (amorçage)
    old_pointer = s3.objects[("b", "releases/current.json")]
    archive, _ = make_archive(tmp_path / "train", b'{"model": 7}')
    s3.put("b", "runs/exec-1/model/job/output/model.tar.gz", archive.read_bytes())
    sm = FakeSageMaker("s3://b/runs/exec-1/model/job/output/model.tar.gz")
    work = tmp_path / "w"
    work.mkdir()
    pointer = promote.promote(
        sm,
        s3,
        package_arn="arn:pkg",
        bucket="b",
        work_dir=work,
        now=datetime(2026, 11, 21, tzinfo=UTC),
    )
    assert pointer["source"] == "model-registry" and pointer["promoted_at"].startswith("2026-11-21")
    assert ("b", pointer["bundle_key"]) in s3.objects
    assert s3.objects[("b", "releases/previous.json")] == old_pointer
    # La Lambda de prédiction charge bien le bundle promu.
    info = BundleStore(s3, "b", tmp_path / "cache", clock=Clock()).current()
    assert info.model_version == pointer["model_version"]


def test_promotion_refuses_foreign_bucket_and_tampered_artifact(tmp_path: Path) -> None:
    s3 = FakeS3()
    work = tmp_path / "w"
    work.mkdir()
    with pytest.raises(promote.PromotionError, match="hors du bucket"):
        promote.promote(
            FakeSageMaker("s3://autre/model.tar.gz"), s3, package_arn="a", bucket="b", work_dir=work
        )
    src = tmp_path / "t"
    src.mkdir()
    archive, _ = make_archive(src)
    staged = src / "staged"
    (staged / "release" / "meta.json").write_text("{}", encoding="utf-8")  # modifié après export
    tampered = src / "tampered.tar.gz"
    tar_dir(staged, tampered)
    s3.put("b", "runs/x/model.tar.gz", tampered.read_bytes())
    with pytest.raises(IntegrityError):
        promote.promote(
            FakeSageMaker("s3://b/runs/x/model.tar.gz"),
            s3,
            package_arn="a",
            bucket="b",
            work_dir=work,
        )
    assert ("b", "releases/current.json") not in s3.objects
    shutil.rmtree(work, ignore_errors=True)


# --- garde-fou des endpoints ------------------------------------------------------------------


class FakeGuardClients:
    def __init__(self, endpoints: list[dict[str, str]]) -> None:
        self.endpoints = endpoints
        self.published: list[dict[str, Any]] = []

    def get_paginator(self, name: str) -> Any:
        eps = self.endpoints

        class P:
            def paginate(self) -> list[dict[str, Any]]:
                return [{"Endpoints": eps}]

        return P()

    def publish(self, **kwargs: Any) -> None:
        self.published.append(kwargs)


def test_guard_alerts_only_when_an_endpoint_exists() -> None:
    quiet = FakeGuardClients([])
    assert guard.check(quiet, quiet, "arn:topic")["alerted"] is False and not quiet.published
    noisy = FakeGuardClients([{"EndpointName": "oubli", "EndpointStatus": "InService"}])
    result = guard.check(noisy, noisy, "arn:topic")
    assert result["alerted"] is True and "oubli" in noisy.published[0]["Message"]
