"""Assemble le contexte de build de l'image Lambda de prédiction (option A).

Vérifie l'intégrité du modèle (SHA-256 du manifeste), copie le code, les tables de service et le
modèle, et écrit ``requirements.txt`` depuis ``uv.lock`` (versions déjà testées) **sans** les
paquets ``nvidia-*`` (GPU, inutiles et très lourds). Aucun secret, aucune donnée brute.
Commande : ``uv run python scripts/build_lambda_context.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "infra" / "lambda" / "predict" / "Dockerfile"
SERVING_FILES = ("observations.parquet", "routes.parquet", "history_daily.parquet")
OPTIONAL_SERVING_FILES = ("replay.parquet",)  # mode rejeu (D-02), copié s'il existe
RELEASE_FILES = ("classifier.json", "meta.json", "manifest.json")


class IntegrityError(RuntimeError):
    """Un artefact ne correspond pas à son empreinte : le build est refusé."""


def filter_requirements(text: str) -> str:
    """Retire les paquets ``nvidia-*`` et leurs commentaires ``# via`` ; garde le reste intact."""
    out: list[str] = []
    skipping = False
    for line in text.splitlines():
        if line.startswith("nvidia-"):
            skipping = True
            continue
        if skipping and line.lstrip().startswith("#"):
            continue
        skipping = False
        out.append(line)
    return "\n".join(out).rstrip() + "\n"


def export_requirements() -> str:
    result = subprocess.run(
        ["uv", "export", "--no-dev", "--no-hashes", "--no-emit-project", "--frozen"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def verify_release(release_dir: Path) -> dict[str, object]:
    manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files"].items():
        actual = hashlib.sha256((release_dir / name).read_bytes()).hexdigest()
        if actual != expected:
            raise IntegrityError(f"{name} : empreinte différente de celle du manifeste")
    digest = manifest["files"]["classifier.json"]
    if manifest["model_version"] != f"clf-{digest[:12]}":
        raise IntegrityError("version du modèle incohérente avec l'empreinte du classifieur")
    return manifest  # type: ignore[no-any-return]


def stage(
    out_dir: Path,
    serving_dir: Path,
    release_dir: Path,
    requirements: str,
    package_dir: Path = ROOT / "src" / "aeropulse",
    dockerfile: Path = DOCKERFILE,
) -> dict[str, object]:
    manifest = verify_release(release_dir)
    for name in SERVING_FILES:
        if not (serving_dir / name).exists():
            raise FileNotFoundError(f"table de service manquante : {name}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    shutil.copytree(
        package_dir, out_dir / "aeropulse", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    (out_dir / "serving").mkdir()
    for name in (*SERVING_FILES, *OPTIONAL_SERVING_FILES):
        if (serving_dir / name).exists():
            shutil.copyfile(serving_dir / name, out_dir / "serving" / name)
    (out_dir / "release").mkdir()
    for name in RELEASE_FILES:
        shutil.copyfile(release_dir / name, out_dir / "release" / name)
    (out_dir / "requirements.txt").write_text(filter_requirements(requirements), encoding="utf-8")
    shutil.copyfile(dockerfile, out_dir / "Dockerfile")
    return {"model_version": manifest["model_version"], "out_dir": str(out_dir)}


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--serving-dir", type=Path, default=ROOT / "data" / "serving")
    p.add_argument("--release-dir", type=Path, default=ROOT / "data" / "ml" / "release")
    p.add_argument("--out-dir", type=Path, default=ROOT / "build" / "lambda-predict")
    args = p.parse_args(argv)
    info = stage(args.out_dir, args.serving_dir, args.release_dir, export_requirements())
    print(json.dumps(info, indent=2))
    print(
        "Étape suivante (Docker démarré) : docker build -t aeropulse-predict " + str(args.out_dir)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
