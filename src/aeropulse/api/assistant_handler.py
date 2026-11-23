"""Route de l'assistant ``POST /v1/chat`` : appelle l'orchestrateur (FR-19, version de test).

Désactivée tant que ``AEROPULSE_BEDROCK_MODEL_ID`` n'est pas défini (503
``assistant_unavailable``) : le modèle Bedrock n'est pas choisi (ADR-0012). Corps accepté :
``{"message": "...", "session_id": "..."}`` (historique géré côté client, D-09 ; la version de
test ne renvoie pas l'historique au modèle). Aucune question n'est écrite dans les journaux.
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from typing import Any

from aeropulse.api import predict_handler, stats_handler
from aeropulse.assistant.orchestrator import Assistant
from aeropulse.tools import build_registry

MAX_BODY_BYTES = 4096
MAX_MESSAGE_CHARS = 1000
ALLOWED_FIELDS = frozenset({"message", "session_id"})
HEADERS = {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"}

_assistant: Assistant | None = None


class BadRequestError(ValueError):
    pass


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": HEADERS,
        "body": json.dumps(payload, ensure_ascii=False),
    }


def _error(status: int, code: str, message: str, event: dict[str, Any]) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    ctx = event.get("requestContext")
    if isinstance(ctx, dict) and ctx.get("requestId"):
        error["correlation_id"] = str(ctx["requestId"])
    return _response(status, {"error": error})


def get_assistant() -> Assistant | None:
    """Assistant configuré par l'environnement, ou ``None`` si aucun modèle n'est fourni."""
    global _assistant
    model_id = os.environ.get("AEROPULSE_BEDROCK_MODEL_ID", "").strip()
    if not model_id:
        return None
    if _assistant is None:
        import boto3  # fourni par le runtime Lambda

        def predict(request: Mapping[str, Any]) -> dict[str, Any]:
            return predict_handler.get_service().handle(request)

        registry = build_registry(stats_handler.get_engine(), predict)
        _assistant = Assistant(
            boto3.client("bedrock-runtime"),
            model_id,
            registry,
            max_rounds=int(os.environ.get("AEROPULSE_ASSISTANT_MAX_ROUNDS", "4")),
            max_tokens=int(os.environ.get("AEROPULSE_ASSISTANT_MAX_TOKENS", "800")),
        )
    return _assistant


def parse_message(event: dict[str, Any]) -> str:
    body = event.get("body")
    if body is None:
        raise BadRequestError("corps de requête manquant")
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8", errors="replace")
    if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_BODY_BYTES:
        raise BadRequestError("corps de requête trop volumineux ou invalide")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise BadRequestError("corps JSON invalide") from exc
    if not isinstance(data, dict):
        raise BadRequestError("le corps doit être un objet JSON")
    unknown = sorted(set(data) - ALLOWED_FIELDS)
    if unknown:
        raise BadRequestError(f"champs non autorisés : {unknown}")
    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        raise BadRequestError("message : texte attendu")
    if len(message) > MAX_MESSAGE_CHARS:
        raise BadRequestError(f"message : {MAX_MESSAGE_CHARS} caractères au plus")
    session = data.get("session_id")
    if session is not None and (not isinstance(session, str) or len(session) > 64):
        raise BadRequestError("session_id : texte de 64 caractères au plus")
    return message.strip()


def handler(
    event: dict[str, Any], context: Any = None, assistant: Assistant | None = None
) -> dict[str, Any]:
    try:
        if event.get("httpMethod") not in (None, "POST"):
            return _error(405, "method_not_allowed", "méthode non autorisée", event)
        message = parse_message(event)
        bot = assistant or get_assistant()
        if bot is None:
            return _error(
                503, "assistant_unavailable", "assistant non configuré (modèle non choisi)", event
            )
        return _response(200, bot.answer(message).as_dict())
    except BadRequestError as exc:
        return _error(400, "invalid_parameter", str(exc), event)
    except Exception as exc:  # noqa: BLE001 - jamais de détail interne dans la réponse
        if type(exc).__name__ in ("ClientError", "EndpointConnectionError", "ReadTimeoutError"):
            return _error(503, "model_unavailable", "modèle de langage indisponible", event)
        return _error(500, "internal_error", "erreur interne", event)
