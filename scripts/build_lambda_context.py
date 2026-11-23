"""Assemble le contexte de build de l'image d'exécution AeroPulse (Lambda + jobs SageMaker).

Copie le paquet ``aeropulse``, les tests de non-fuite (exécutés par l'étape « Evaluate » du
pipeline), le Dockerfile et le point d'entrée, et écrit ``requirements.txt`` depuis ``uv.lock``
(versions déjà testées) **sans** les paquets ``nvidia-*`` (GPU, inutiles et très lourds), plus
``pytest`` et ses dépendances épinglés depuis le même verrou.

Le modèle et les tables de service ne sont **plus** dans l'image (ADR-0018) : ils sont publiés
dans S3 sous forme de bundle vérifié (``scripts/aws/aeropulse_aws.py publish-local-bundle``).
Aucun secret, aucune donnée. Commande : ``uv run python scripts/build_lambda_context.py``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Iterable, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = ROOT / "infra" / "images" / "runtime"
IMAGE_FILES = ("Dockerfile", "entrypoint.sh")
CHECKS = (ROOT / "tests" / "test_leakage.py",)
CHECK_TOOLS = ("pytest",)


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


def pinned_closure(lock_text: str, roots: Iterable[str]) -> list[str]:
    """``nom==version`` pour ``roots`` et leurs dépendances (hors Windows), depuis ``uv.lock``."""
    packages = {p["name"]: p for p in tomllib.loads(lock_text)["package"]}
    seen: dict[str, str] = {}
    todo = list(roots)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        pkg = packages[name]
        seen[name] = str(pkg["version"])
        for dep in pkg.get("dependencies", []):
            if "win32" not in str(dep.get("marker", "")):
                todo.append(str(dep["name"]))
    return [f"{n}=={v}" for n, v in sorted(seen.items())]


def merge_requirements(base: str, extra: Sequence[str]) -> str:
    """Ajoute les épinglages ``extra`` absents de ``base`` (sans doublon de paquet)."""
    present = {line.split("==")[0].strip().lower() for line in base.splitlines() if "==" in line}
    added = [e for e in extra if e.split("==")[0].lower() not in present]
    if not added:
        return base
    return base.rstrip() + "\n# contrôles de non-fuite (étape Evaluate)\n" + "\n".join(added) + "\n"


def export_requirements() -> str:
    result = subprocess.run(
        ["uv", "export", "--no-dev", "--no-hashes", "--no-emit-project", "--frozen"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def stage(
    out_dir: Path,
    requirements: str,
    package_dir: Path = ROOT / "src" / "aeropulse",
    image_dir: Path = IMAGE_DIR,
    checks: Sequence[Path] = CHECKS,
) -> dict[str, object]:
    for name in IMAGE_FILES:
        if not (image_dir / name).is_file():
            raise FileNotFoundError(f"fichier d'image manquant : {name}")
    missing = [str(c) for c in checks if not c.is_file()]
    if missing:
        raise FileNotFoundError(f"tests de non-fuite manquants : {missing}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    shutil.copytree(
        package_dir, out_dir / "aeropulse", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    (out_dir / "checks").mkdir()
    for check in checks:
        shutil.copyfile(check, out_dir / "checks" / check.name)
    (out_dir / "requirements.txt").write_text(requirements, encoding="utf-8")
    for name in IMAGE_FILES:
        # Fins de ligne Unix pour le script shell (le Dockerfile les corrige aussi).
        data = (image_dir / name).read_bytes().replace(b"\r\n", b"\n")
        (out_dir / name).write_bytes(data)
    return {"out_dir": str(out_dir), "checks": [c.name for c in checks]}


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", type=Path, default=ROOT / "build" / "runtime")
    args = p.parse_args(argv)
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    requirements = merge_requirements(
        filter_requirements(export_requirements()), pinned_closure(lock, CHECK_TOOLS)
    )
    info = stage(args.out_dir, requirements)
    print(json.dumps(info, indent=2))
    print("Étape suivante : le déploiement CDK construit l'image depuis " + str(args.out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
