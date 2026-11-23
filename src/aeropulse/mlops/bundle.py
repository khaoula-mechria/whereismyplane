"""Paquet de service versionné (« bundle ») : modèle + tables de service, vérifiés par empreinte.

Un bundle est une archive ``tar.gz`` dont la racine contient :

- ``release/`` : ``classifier.json``, ``meta.json``, ``manifest.json`` (export de T4.9) ;
- ``serving/`` : tables lues par ``FeatureBuilder`` et ``ReplayStore`` ;
- ``bundle.json`` : version du modèle et SHA-256 de chaque table de service.

C'est exactement le contenu de ``/opt/ml/model`` à la fin du job d'entraînement SageMaker : le
``model.tar.gz`` produit par SageMaker *est* un bundle. La Lambda de prédiction le télécharge au
démarrage ; un modèle modifié ou incomplet est refusé (``IntegrityError``).
Bibliothèque standard uniquement (utilisé par la Lambda de promotion, sans pandas).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

RELEASE_FILES = ("classifier.json", "meta.json", "manifest.json")
SERVING_FILES = ("observations.parquet", "routes.parquet", "history_daily.parquet")
OPTIONAL_SERVING_FILES = ("replay.parquet",)  # mode rejeu (D-02)
BUNDLE_MANIFEST = "bundle.json"
MAX_UNPACKED_BYTES = 512 * 1024 * 1024  # garde-fou contre une archive anormale


class IntegrityError(RuntimeError):
    """Un artefact ne correspond pas à son empreinte, ou le bundle est incomplet."""


@dataclass(frozen=True)
class BundleInfo:
    model_version: str
    root: Path

    @property
    def release_dir(self) -> Path:
        return self.root / "release"

    @property
    def serving_dir(self) -> Path:
        return self.root / "serving"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_release(release_dir: Path) -> dict[str, Any]:
    """Vérifie ``manifest.json`` : empreintes des fichiers et version dérivée du classifieur."""
    try:
        manifest: dict[str, Any] = json.loads(
            (release_dir / "manifest.json").read_text(encoding="utf-8")
        )
        files: dict[str, str] = manifest["files"]
        version = str(manifest["model_version"])
    except (OSError, KeyError, ValueError) as exc:
        raise IntegrityError("manifest.json absent ou invalide") from exc
    for name, expected in files.items():
        path = release_dir / name
        if not path.is_file() or sha256_file(path) != expected:
            raise IntegrityError(f"{name} : empreinte différente de celle du manifeste")
    digest = files.get("classifier.json")
    if digest is None or version != f"clf-{digest[:12]}":
        raise IntegrityError("version du modèle incohérente avec l'empreinte du classifieur")
    return manifest


def stage_bundle(release_dir: Path, serving_dir: Path, out_dir: Path) -> dict[str, Any]:
    """Écrit la disposition d'un bundle dans ``out_dir`` (vide ou absent) et renvoie bundle.json."""
    manifest = verify_release(release_dir)
    missing = [n for n in SERVING_FILES if not (serving_dir / n).is_file()]
    if missing:
        raise IntegrityError(f"tables de service manquantes : {missing}")
    (out_dir / "release").mkdir(parents=True, exist_ok=True)
    (out_dir / "serving").mkdir(parents=True, exist_ok=True)
    for name in RELEASE_FILES:
        shutil.copyfile(release_dir / name, out_dir / "release" / name)
    tables: dict[str, str] = {}
    for name in (*SERVING_FILES, *OPTIONAL_SERVING_FILES):
        if (serving_dir / name).is_file():
            shutil.copyfile(serving_dir / name, out_dir / "serving" / name)
            tables[name] = sha256_file(out_dir / "serving" / name)
    info = {
        "model_version": manifest["model_version"],
        "threshold": manifest.get("threshold"),
        "serving_files": tables,
    }
    (out_dir / BUNDLE_MANIFEST).write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def make_archive(staged_dir: Path, archive: Path) -> str:
    """Archive un bundle préparé (chemins relatifs à la racine) ; renvoie le SHA-256."""
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "w:gz") as tar:
        for path in sorted(staged_dir.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=path.relative_to(staged_dir).as_posix(), recursive=False)
    return sha256_file(archive)


def _safe_members(tar: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members: list[tarfile.TarInfo] = []
    total = 0
    for m in tar.getmembers():
        name = m.name[2:] if m.name.startswith("./") else m.name
        parts = PurePosixPath(name).parts
        if not name or name == ".":
            continue
        if name.startswith("/") or ".." in parts or not (m.isfile() or m.isdir()):
            raise IntegrityError(f"entrée d'archive refusée : {m.name!r}")
        total += m.size
        if total > MAX_UNPACKED_BYTES:
            raise IntegrityError("archive trop volumineuse")
        m.name = name
        members.append(m)
    return members


def verify_bundle(root: Path) -> BundleInfo:
    """Vérifie un bundle déjà extrait : manifeste du modèle et empreintes des tables."""
    manifest = verify_release(root / "release")
    try:
        info = json.loads((root / BUNDLE_MANIFEST).read_text(encoding="utf-8"))
        tables: dict[str, str] = info["serving_files"]
    except (OSError, KeyError, ValueError) as exc:
        raise IntegrityError("bundle.json absent ou invalide") from exc
    if info.get("model_version") != manifest["model_version"]:
        raise IntegrityError("bundle.json ne correspond pas au modèle")
    if any(n not in tables for n in SERVING_FILES):
        raise IntegrityError("tables de service manquantes dans bundle.json")
    for name, expected in tables.items():
        path = root / "serving" / name
        if not path.is_file() or sha256_file(path) != expected:
            raise IntegrityError(f"serving/{name} : empreinte différente")
    return BundleInfo(str(manifest["model_version"]), root)


def extract_bundle(archive: Path, dest: Path) -> BundleInfo:
    """Extrait (sans chemin hors de ``dest``, sans lien) puis vérifie. ``dest`` est remplacé."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    try:
        with tarfile.open(archive, "r:gz") as tar:
            for member in _safe_members(tar):
                target = dest / member.name
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                src = tar.extractfile(member)
                if src is None:
                    raise IntegrityError(f"entrée illisible : {member.name!r}")
                with src, target.open("wb") as out:
                    shutil.copyfileobj(src, out)
        return verify_bundle(dest)
    except (tarfile.TarError, OSError, IntegrityError):
        shutil.rmtree(dest, ignore_errors=True)
        raise
