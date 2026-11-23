"""Routes de prédiction : ``POST /v1/predict`` et ``GET /v1/health``.

Compatible AWS Lambda / API Gateway (événement proxy). Deux sources de ressources :

- **AWS** (``AEROPULSE_BUNDLE_BUCKET`` défini) : bundle actif lu dans S3 via le pointeur
  ``releases/current.json`` (``mlops.store``), vérifié par empreinte, rafraîchi au plus toutes les
  5 min ; un modèle promu remplace l'ancien sans reconstruire l'image (ADR-0018) ;
- **local** : ``AEROPULSE_SERVING_DIR`` et ``AEROPULSE_RELEASE_DIR`` (comportement d'origine).

Aucune entrée utilisateur n'est écrite dans les journaux ; les erreurs internes ne divulguent rien.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from aeropulse.api.predict_service import PredictionService
from aeropulse.features.serving import (
    FeatureBuilder,
    InvalidRequestError,
    ReplayStore,
    ServingError,
)
from aeropulse.mlops.store import BundleStore, BundleUnavailableError, store_from_environment
from aeropulse.models.predict import Predictor

MAX_BODY_BYTES = 4096
HEADERS = {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"}

_service: PredictionService | None = None
_service_version: str | None = None
_store: BundleStore | None = None


def _correlation_id(event: dict[str, Any]) -> str | None:
    ctx = event.get("requestContext") or {}
    rid = ctx.get("requestId") if isinstance(ctx, dict) else None
    return str(rid) if rid else None


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": HEADERS,
        "body": json.dumps(payload, ensure_ascii=False),
    }


def _error(status: int, code: str, message: str, correlation_id: str | None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if correlation_id:
        error["correlation_id"] = correlation_id
    return _response(status, {"error": error})


def _build(serving: Path, release: Path) -> PredictionService:
    replay = ReplayStore(serving) if (serving / "replay.parquet").exists() else None
    return PredictionService(FeatureBuilder(serving), Predictor(release), replay)


def get_service() -> PredictionService:
    """Service du conteneur ; reconstruit seulement si le bundle actif a changé."""
    global _service, _service_version, _store
    if _store is None and os.environ.get("AEROPULSE_BUNDLE_BUCKET"):
        _store = store_from_environment()
    if _store is not None:
        info = _store.current()  # BundleUnavailableError si aucun bundle valide
        if _service is None or _service_version != info.model_version:
            _service = _build(info.serving_dir, info.release_dir)
            _service_version = info.model_version
        return _service
    if _service is None:
        serving = Path(os.environ.get("AEROPULSE_SERVING_DIR", "data/serving"))
        release = Path(os.environ.get("AEROPULSE_RELEASE_DIR", "data/ml/release"))
        _service = _build(serving, release)
    return _service


def parse_body(event: dict[str, Any]) -> Any:
    body = event.get("body")
    if body is None:
        raise InvalidRequestError("corps de requête manquant")
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8", errors="replace")
    if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_BODY_BYTES:
        raise InvalidRequestError("corps de requête trop volumineux ou invalide")
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise InvalidRequestError("corps JSON invalide") from exc


def _health(service: PredictionService) -> dict[str, Any]:
    return _response(
        200,
        {
            "status": "ok",
            "model_versions": {"classification": service.model_version},
            "prediction_modes": service.modes,
            "inference": "in-process (Lambda), aucun endpoint SageMaker",
        },
    )


def handler(
    event: dict[str, Any], context: Any = None, service: PredictionService | None = None
) -> dict[str, Any]:
    cid = _correlation_id(event)
    try:
        if event.get("httpMethod") == "GET":
            return _health(service or get_service())
        request = parse_body(event)
        result = (service or get_service()).handle(request)
        return _response(200, result)
    except ServingError as exc:
        return _error(exc.status, exc.code, str(exc), cid)
    except BundleUnavailableError:
        return _error(503, "model_unavailable", "modèle indisponible", cid)
    except Exception:  # noqa: BLE001 - jamais de détail interne dans la réponse
        return _error(500, "internal_error", "erreur interne", cid)
