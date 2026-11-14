from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_lambda_context as blc  # noqa: E402

REQUIREMENTS = """numpy==2.5.4
    # via pandas
nvidia-nccl-cu13==2.32.6 ; sys_platform == 'linux'
    # via xgboost
pandas==3.1.1
    # via aeropulse
xgboost==3.4.1
"""


def _release(tmp_path: Path) -> Path:
    rel = tmp_path / "release"
    rel.mkdir()
    (rel / "classifier.json").write_text('{"model": 1}', encoding="utf-8")
    (rel / "meta.json").write_text('{"meta": 1}', encoding="utf-8")

    def sha(name: str) -> str:
        return hashlib.sha256((rel / name).read_bytes()).hexdigest()

    manifest = {
        "model_version": f"clf-{sha('classifier.json')[:12]}",
        "files": {"classifier.json": sha("classifier.json"), "meta.json": sha("meta.json")},
    }
    (rel / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return rel


def _serving(tmp_path: Path) -> Path:
    srv = tmp_path / "serving"
    srv.mkdir()
    for name in blc.SERVING_FILES:
        (srv / name).write_bytes(b"x")
    return srv


def test_requirements_drop_nvidia_and_keep_the_rest() -> None:
    out = blc.filter_requirements(REQUIREMENTS)
    assert "nvidia" not in out and "xgboost==3.4.1" in out
    assert "numpy==2.5.4" in out and "pandas==3.1.1" in out
    assert "# via xgboost" not in out  # le commentaire du paquet retiré part avec lui


def test_stage_builds_context_and_checks_integrity(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    (pkg / "sub").mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "sub" / "__pycache__").mkdir()
    (pkg / "sub" / "__pycache__" / "x.pyc").write_bytes(b"x")
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM scratch\n", encoding="utf-8")
    out = tmp_path / "ctx"
    info = blc.stage(out, _serving(tmp_path), _release(tmp_path), REQUIREMENTS, pkg, dockerfile)
    assert str(info["model_version"]).startswith("clf-")
    for rel in ("Dockerfile", "requirements.txt", "aeropulse/__init__.py", "release/manifest.json"):
        assert (out / rel).exists()
    assert not (out / "aeropulse" / "sub" / "__pycache__").exists()
    assert not (out / "release" / "regressor.json").exists()


def test_replay_table_is_copied_when_present(tmp_path: Path) -> None:
    srv = _serving(tmp_path)
    (srv / "replay.parquet").write_bytes(b"r")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    out = tmp_path / "ctx"
    (tmp_path / "Dockerfile.x").write_text("FROM scratch\n", encoding="utf-8")
    blc.stage(out, srv, _release(tmp_path), REQUIREMENTS, pkg, tmp_path / "Dockerfile.x")
    assert (out / "serving" / "replay.parquet").exists()


def test_tampered_model_is_refused(tmp_path: Path) -> None:
    rel = _release(tmp_path)
    (rel / "classifier.json").write_text('{"model": 2}', encoding="utf-8")  # modifié après export
    with pytest.raises(blc.IntegrityError):
        blc.stage(tmp_path / "ctx", _serving(tmp_path), rel, REQUIREMENTS, tmp_path, tmp_path / "x")
    assert not (tmp_path / "ctx").exists()


def test_missing_serving_table_is_refused(tmp_path: Path) -> None:
    srv = _serving(tmp_path)
    (srv / "routes.parquet").unlink()
    with pytest.raises(FileNotFoundError):
        blc.stage(tmp_path / "ctx", srv, _release(tmp_path), REQUIREMENTS, tmp_path, tmp_path / "x")
