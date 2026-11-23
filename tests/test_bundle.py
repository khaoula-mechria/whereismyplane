"""Bundle de service : création, archive, extraction sûre et contrôle d'intégrité (ADR-0018)."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

from aeropulse.mlops import bundle


def make_release(root: Path, model: bytes = b'{"model": 1}') -> Path:
    rel = root / "release"
    rel.mkdir(parents=True)
    (rel / "classifier.json").write_bytes(model)
    (rel / "meta.json").write_text('{"meta": 1}', encoding="utf-8")

    def sha(name: str) -> str:
        return hashlib.sha256((rel / name).read_bytes()).hexdigest()

    manifest = {
        "model_version": f"clf-{sha('classifier.json')[:12]}",
        "threshold": 0.2,
        "files": {"classifier.json": sha("classifier.json"), "meta.json": sha("meta.json")},
    }
    (rel / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return rel


def make_serving(root: Path, replay: bool = True) -> Path:
    srv = root / "serving"
    srv.mkdir(parents=True)
    for name in bundle.SERVING_FILES:
        (srv / name).write_bytes(name.encode())
    if replay:
        (srv / "replay.parquet").write_bytes(b"replay")
    return srv


def make_archive(tmp_path: Path, model: bytes = b'{"model": 1}') -> tuple[Path, str]:
    src = tmp_path / "src"
    staged = tmp_path / "staged"
    bundle.stage_bundle(make_release(src, model), make_serving(src), staged)
    archive = tmp_path / "bundle.tar.gz"
    return archive, bundle.make_archive(staged, archive)


def test_round_trip_keeps_version_and_tables(tmp_path: Path) -> None:
    archive, digest = make_archive(tmp_path)
    assert digest == bundle.sha256_file(archive)
    info = bundle.extract_bundle(archive, tmp_path / "out")
    assert info.model_version.startswith("clf-")
    assert (info.release_dir / "classifier.json").read_bytes() == b'{"model": 1}'
    assert (info.serving_dir / "replay.parquet").read_bytes() == b"replay"


def test_replay_table_is_optional(tmp_path: Path) -> None:
    src = tmp_path / "src"
    info = bundle.stage_bundle(make_release(src), make_serving(src, replay=False), tmp_path / "s")
    assert "replay.parquet" not in info["serving_files"]
    assert bundle.verify_bundle(tmp_path / "s").model_version == info["model_version"]


def test_missing_serving_table_is_refused(tmp_path: Path) -> None:
    src = tmp_path / "src"
    srv = make_serving(src)
    (srv / "routes.parquet").unlink()
    with pytest.raises(bundle.IntegrityError, match="manquantes"):
        bundle.stage_bundle(make_release(src), srv, tmp_path / "s")


def test_tampered_model_is_refused_before_staging(tmp_path: Path) -> None:
    rel = make_release(tmp_path / "src")
    (rel / "classifier.json").write_text('{"model": 2}', encoding="utf-8")
    with pytest.raises(bundle.IntegrityError):
        bundle.stage_bundle(rel, make_serving(tmp_path / "src"), tmp_path / "s")


def test_tampered_table_inside_archive_is_refused_and_cleaned(tmp_path: Path) -> None:
    src = tmp_path / "src"
    staged = tmp_path / "staged"
    bundle.stage_bundle(make_release(src), make_serving(src), staged)
    (staged / "serving" / "routes.parquet").write_bytes(b"modifie")
    archive = tmp_path / "b.tar.gz"
    bundle.make_archive(staged, archive)
    with pytest.raises(bundle.IntegrityError, match="routes.parquet"):
        bundle.extract_bundle(archive, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def _tar_with(tmp_path: Path, member: tarfile.TarInfo, data: bytes = b"") -> Path:
    archive = tmp_path / "evil.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.addfile(member, io.BytesIO(data) if data else None)
    return archive


def test_path_traversal_is_refused(tmp_path: Path) -> None:
    member = tarfile.TarInfo("../outside.txt")
    member.size = 1
    archive = _tar_with(tmp_path, member, b"x")
    with pytest.raises(bundle.IntegrityError, match="refusée"):
        bundle.extract_bundle(archive, tmp_path / "out")
    assert not (tmp_path / "outside.txt").exists()


def test_symlink_is_refused(tmp_path: Path) -> None:
    member = tarfile.TarInfo("release/classifier.json")
    member.type = tarfile.SYMTYPE
    member.linkname = "/etc/passwd"
    with pytest.raises(bundle.IntegrityError, match="refusée"):
        bundle.extract_bundle(_tar_with(tmp_path, member), tmp_path / "out")


def test_sagemaker_style_dot_prefix_is_accepted(tmp_path: Path) -> None:
    src = tmp_path / "src"
    staged = tmp_path / "staged"
    bundle.stage_bundle(make_release(src), make_serving(src), staged)
    archive = tmp_path / "model.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(staged, arcname=".")  # SageMaker archive le contenu de /opt/ml/model
    assert bundle.extract_bundle(archive, tmp_path / "out").model_version.startswith("clf-")
