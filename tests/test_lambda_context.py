from __future__ import annotations

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

LOCK = """
version = 1

[[package]]
name = "pytest"
version = "9.2.0"
dependencies = [
    { name = "colorama", marker = "sys_platform == 'win32'" },
    { name = "pluggy" },
    { name = "packaging" },
]

[[package]]
name = "pluggy"
version = "1.7.0"

[[package]]
name = "packaging"
version = "26.3"

[[package]]
name = "colorama"
version = "0.4.6"
"""


def _image_dir(tmp_path: Path) -> Path:
    img = tmp_path / "image"
    img.mkdir()
    (img / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (img / "entrypoint.sh").write_bytes(b"#!/bin/sh\r\nexec true\r\n")
    return img


def _check(tmp_path: Path) -> Path:
    check = tmp_path / "test_leakage.py"
    check.write_text("def test_ok() -> None:\n    assert True\n", encoding="utf-8")
    return check


def test_requirements_drop_nvidia_and_keep_the_rest() -> None:
    out = blc.filter_requirements(REQUIREMENTS)
    assert "nvidia" not in out and "xgboost==3.4.1" in out
    assert "numpy==2.5.4" in out and "pandas==3.1.1" in out
    assert "# via xgboost" not in out  # le commentaire du paquet retiré part avec lui


def test_pytest_closure_is_pinned_from_lock_without_windows_only_packages() -> None:
    pins = blc.pinned_closure(LOCK, ["pytest"])
    assert pins == ["packaging==26.3", "pluggy==1.7.0", "pytest==9.2.0"]


def test_merge_does_not_duplicate_existing_packages() -> None:
    merged = blc.merge_requirements(
        "packaging==26.3\npandas==3.1.1\n", ["packaging==26.3", "pytest==9.2.0"]
    )
    assert merged.count("packaging==") == 1 and "pytest==9.2.0" in merged


def test_stage_builds_context_without_model_or_data(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    (pkg / "sub" / "__pycache__").mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "sub" / "__pycache__" / "x.pyc").write_bytes(b"x")
    out = tmp_path / "ctx"
    blc.stage(out, "pandas==3.1.1\n", pkg, _image_dir(tmp_path), [_check(tmp_path)])
    for rel in ("Dockerfile", "entrypoint.sh", "requirements.txt", "aeropulse/__init__.py"):
        assert (out / rel).exists()
    assert (out / "checks" / "test_leakage.py").exists()
    assert not (out / "aeropulse" / "sub" / "__pycache__").exists()
    assert not (out / "release").exists() and not (out / "serving").exists()  # ADR-0018
    assert b"\r\n" not in (out / "entrypoint.sh").read_bytes()


def test_missing_leakage_tests_are_refused(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        blc.stage(tmp_path / "ctx", "", tmp_path, _image_dir(tmp_path), [tmp_path / "absent.py"])
    assert not (tmp_path / "ctx").exists()


def test_real_image_files_exist() -> None:
    for name in blc.IMAGE_FILES:
        assert (blc.IMAGE_DIR / name).is_file()
    assert all(c.is_file() for c in blc.CHECKS)
