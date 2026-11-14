"""Route de prédiction : valide l'entrée, construit les variables, appelle le modèle.

Compatible AWS Lambda / API Gateway (événement proxy). Les ressources (tables, modèle) sont
chargées une fois par conteneur depuis ``AEROPULSE_SERVING_DIR`` et ``AEROPULSE_RELEASE_DIR``.
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
from aeropulse.models.predict import Predictor

MAX_BODY_BYTES = 4096
HEADERS = {"Content-Type": "application/json; charset=utf-8"}

_service: PredictionService | None = None


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": HEADERS,
        "body": json.dumps(payload, ensure_ascii=False),
    }


def _error(status: int, code: str, message: str) -> dict[str, Any]:
    return _response(status, {"error": {"code": code, "message": message}})


def get_service() -> PredictionService:
    global _service
    if _service is None:
        serving = Path(os.environ.get("AEROPULSE_SERVING_DIR", "data/serving"))
        release = Path(os.environ.get("AEROPULSE_RELEASE_DIR", "data/ml/release"))
        replay = ReplayStore(serving) if (serving / "replay.parquet").exists() else None
        _service = PredictionService(FeatureBuilder(serving), Predictor(release), replay)
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


def handler(
    event: dict[str, Any], context: Any = None, service: PredictionService | None = None
) -> dict[str, Any]:
    try:
        request = parse_body(event)
        result = (service or get_service()).handle(request)
        return _response(200, result)
    except ServingError as exc:
        return _error(exc.status, exc.code, str(exc))
    except Exception:  # noqa: BLE001 - jamais de détail interne dans la réponse
        return _error(500, "internal_error", "erreur interne")
