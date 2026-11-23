"""Chargement du bundle de service actif depuis S3 (Lambda), avec rafraîchissement borné.

Le bundle actif est désigné par un **pointeur** JSON (par défaut ``releases/current.json``) :
``{"model_version", "bundle_key", "sha256", "source", ...}``, écrit par la promotion
(``promote.py``) ou par l'amorçage depuis le poste local. La Lambda relit le pointeur au plus
toutes les ``refresh_seconds`` ; si la version change, elle télécharge, vérifie l'empreinte de
l'archive puis celle de chaque fichier, et bascule. Bibliothèque standard + client S3 injecté.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from aeropulse.mlops import bundle

DEFAULT_POINTER_KEY = "releases/current.json"
DEFAULT_REFRESH_SECONDS = 300.0


class BundleUnavailableError(RuntimeError):
    """Aucun bundle valide n'a pu être chargé (pointeur absent, S3 inaccessible, empreinte)."""


class S3Client(Protocol):
    def get_object(self, *, Bucket: str, Key: str) -> Any: ...

    def download_file(self, Bucket: str, Key: str, Filename: str) -> None: ...


@dataclass(frozen=True)
class Pointer:
    model_version: str
    bundle_key: str
    sha256: str

    @staticmethod
    def parse(raw: bytes) -> Pointer:
        try:
            data = json.loads(raw)
            pointer = Pointer(
                str(data["model_version"]), str(data["bundle_key"]), str(data["sha256"])
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise BundleUnavailableError("pointeur de bundle invalide") from exc
        if not pointer.bundle_key.startswith("releases/") or ".." in pointer.bundle_key:
            raise BundleUnavailableError("pointeur de bundle hors du préfixe releases/")
        return pointer


class BundleStore:
    """Bundle actif, mis en cache dans ``work_dir`` (``/tmp`` en Lambda)."""

    def __init__(
        self,
        s3: S3Client,
        bucket: str,
        work_dir: Path,
        pointer_key: str = DEFAULT_POINTER_KEY,
        refresh_seconds: float = DEFAULT_REFRESH_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._s3 = s3
        self._bucket = bucket
        self._work = work_dir
        self._pointer_key = pointer_key
        self._refresh = refresh_seconds
        self._clock = clock
        self._current: bundle.BundleInfo | None = None
        self._checked_at: float | None = None

    def _read_pointer(self) -> Pointer:
        obj = self._s3.get_object(Bucket=self._bucket, Key=self._pointer_key)
        return Pointer.parse(obj["Body"].read())

    def _load(self, pointer: Pointer) -> bundle.BundleInfo:
        self._work.mkdir(parents=True, exist_ok=True)
        archive = self._work / "bundle.tar.gz"
        self._s3.download_file(self._bucket, pointer.bundle_key, str(archive))
        try:
            if bundle.sha256_file(archive) != pointer.sha256:
                raise bundle.IntegrityError("archive différente de l'empreinte du pointeur")
            info = bundle.extract_bundle(archive, self._work / pointer.model_version)
        finally:
            archive.unlink(missing_ok=True)
        if info.model_version != pointer.model_version:
            raise bundle.IntegrityError("version du bundle différente de celle du pointeur")
        return info

    def current(self) -> bundle.BundleInfo:
        """Bundle actif ; relit le pointeur si le délai de rafraîchissement est écoulé.

        En cas d'échec d'un rafraîchissement, le bundle déjà chargé reste servi.
        """
        now = self._clock()
        due = self._checked_at is None or now - self._checked_at >= self._refresh
        if self._current is not None and not due:
            return self._current
        try:
            pointer = self._read_pointer()
            if self._current is None or pointer.model_version != self._current.model_version:
                self._current = self._load(pointer)
        except Exception as exc:  # noqa: BLE001 - S3, réseau, intégrité : même traitement
            if self._current is None:
                raise BundleUnavailableError("bundle de service indisponible") from exc
        finally:
            self._checked_at = now
        return self._current


def store_from_environment() -> BundleStore | None:
    """``BundleStore`` configuré par l'environnement Lambda, ou ``None`` en local."""
    bucket = os.environ.get("AEROPULSE_BUNDLE_BUCKET")
    if not bucket:
        return None
    import boto3  # fourni par le runtime Lambda ; import tardif pour le local et les tests

    return BundleStore(
        boto3.client("s3"),
        bucket,
        Path(os.environ.get("AEROPULSE_WORK_DIR", "/tmp/aeropulse")) / "bundles",
        os.environ.get("AEROPULSE_BUNDLE_POINTER", DEFAULT_POINTER_KEY),
        float(os.environ.get("AEROPULSE_BUNDLE_REFRESH_SECONDS", DEFAULT_REFRESH_SECONDS)),
    )


class PrefixSync:
    """Copie (une fois par conteneur) un préfixe S3 en lecture seule vers un dossier local."""

    def __init__(self, s3: Any, bucket: str, prefix: str, dest: Path) -> None:
        self._s3 = s3
        self._bucket = bucket
        self._prefix = prefix if prefix.endswith("/") else prefix + "/"
        self._dest = dest

    def sync(self) -> int:
        count = 0
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=self._prefix):
            for obj in page.get("Contents", []):
                rel = str(obj["Key"])[len(self._prefix) :]
                if not rel or rel.endswith("/") or ".." in rel.split("/"):
                    continue
                target = self._dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                self._s3.download_file(self._bucket, obj["Key"], str(target))
                count += 1
        if count == 0:
            raise BundleUnavailableError(f"aucun fichier sous s3://{self._bucket}/{self._prefix}")
        return count
