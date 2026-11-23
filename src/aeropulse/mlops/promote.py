"""Promotion d'un modèle approuvé dans le Model Registry vers l'API (Lambda, EventBridge).

Déclencheur : événement « SageMaker Model Package State Change » avec
``ModelApprovalStatus = Approved`` pour le groupe de modèles du projet. La fonction :

1. lit ``ModelDataUrl`` du paquet (le ``model.tar.gz`` de l'entraînement, qui est un bundle) ;
2. refuse un artefact hors du bucket du projet ;
3. télécharge, **vérifie** (empreintes du modèle et des tables) ;
4. copie l'archive sous ``releases/<version>/bundle.tar.gz`` ;
5. sauvegarde l'ancien pointeur dans ``releases/previous.json`` (retour arrière) et écrit
   ``releases/current.json``. Les Lambdas de prédiction basculent au plus tard après leur délai
   de rafraîchissement (5 min par défaut).

Aucune approbation automatique : l'approbation reste manuelle (T5.5).
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from aeropulse.mlops import bundle
from aeropulse.mlops.store import DEFAULT_POINTER_KEY

PREVIOUS_POINTER_KEY = "releases/previous.json"


class PromotionError(RuntimeError):
    """Événement ou artefact refusé : rien n'est promu."""


def parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.lstrip("/"):
        raise PromotionError("ModelDataUrl n'est pas une URI S3 valide")
    return parsed.netloc, parsed.path.lstrip("/")


def approved_package_arn(event: dict[str, Any], group_name: str) -> str | None:
    """ARN du paquet si l'événement est une approbation pour ``group_name``, sinon ``None``."""
    detail = event.get("detail") or {}
    if detail.get("ModelPackageGroupName") != group_name:
        return None
    if detail.get("ModelApprovalStatus") != "Approved":
        return None
    arn = detail.get("ModelPackageArn")
    return str(arn) if arn else None


def promote(
    sm: Any,
    s3: Any,
    *,
    package_arn: str,
    bucket: str,
    work_dir: Path,
    pointer_key: str = DEFAULT_POINTER_KEY,
    now: datetime | None = None,
) -> dict[str, Any]:
    package = sm.describe_model_package(ModelPackageName=package_arn)
    containers = package.get("InferenceSpecification", {}).get("Containers", [])
    if len(containers) != 1 or "ModelDataUrl" not in containers[0]:
        raise PromotionError("le paquet doit référencer exactement un artefact")
    src_bucket, src_key = parse_s3_uri(str(containers[0]["ModelDataUrl"]))
    if src_bucket != bucket:
        raise PromotionError("artefact hors du bucket du projet : refusé")

    archive = work_dir / "model.tar.gz"
    s3.download_file(src_bucket, src_key, str(archive))
    info = bundle.extract_bundle(archive, work_dir / "check")  # lève IntegrityError
    digest = bundle.sha256_file(archive)
    bundle_key = f"releases/{info.model_version}/bundle.tar.gz"
    s3.upload_file(str(archive), bucket, bundle_key)

    pointer = {
        "model_version": info.model_version,
        "bundle_key": bundle_key,
        "sha256": digest,
        "source": "model-registry",
        "model_package_arn": package_arn,
        "promoted_at": (now or datetime.now(UTC)).isoformat(timespec="seconds"),
    }
    write_pointer(s3, bucket, pointer, pointer_key)
    return pointer


def write_pointer(
    s3: Any, bucket: str, pointer: dict[str, Any], pointer_key: str = DEFAULT_POINTER_KEY
) -> None:
    """Sauvegarde l'ancien pointeur dans ``previous.json`` puis écrit le nouveau.

    Seule la **lecture** de l'ancien pointeur peut échouer sans conséquence (premier
    déploiement) ; une erreur d'écriture est propagée : sans sauvegarde, pas de bascule.
    """
    try:
        previous = s3.get_object(Bucket=bucket, Key=pointer_key)["Body"].read()
    except Exception:  # noqa: BLE001 - pas encore de pointeur : premier déploiement
        previous = None
    if previous:
        s3.put_object(
            Bucket=bucket, Key=PREVIOUS_POINTER_KEY, Body=previous, ContentType="application/json"
        )
    s3.put_object(
        Bucket=bucket,
        Key=pointer_key,
        Body=json.dumps(pointer, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    group = os.environ["AEROPULSE_MODEL_PACKAGE_GROUP"]
    bucket = os.environ["AEROPULSE_BUNDLE_BUCKET"]
    arn = approved_package_arn(event, group)
    if arn is None:
        return {"promoted": False, "reason": "événement ignoré (groupe ou statut)"}
    import boto3  # fourni par le runtime Lambda

    with tempfile.TemporaryDirectory() as tmp:
        pointer = promote(
            boto3.client("sagemaker"),
            boto3.client("s3"),
            package_arn=arn,
            bucket=bucket,
            work_dir=Path(tmp),
            pointer_key=os.environ.get("AEROPULSE_BUNDLE_POINTER", DEFAULT_POINTER_KEY),
        )
    print(json.dumps({"promoted": True, "model_version": pointer["model_version"]}))
    return {"promoted": True, **pointer}
