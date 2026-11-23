"""Routes de statistiques : ``GET /v1/meta`` et ``GET /v1/stats/{dimension}`` (T7.2).

Réutilise le moteur analytique testé (``analytics.engine.Analytics`` : DuckDB en lecture seule,
requêtes prédéfinies, listes blanches, limite plafonnée, seuil de 30 vols). Sur AWS, le Parquet
préparé (``processed/flights/`` du bucket de données, ~28 Mo) est copié une fois par conteneur dans
``/tmp`` ; Athena reste disponible pour l'analyse ad hoc (même table, ADR-0018).

Paramètres de requête acceptés : ``carrier``, ``origin``, ``destination``, ``year``, ``month``,
``limit``. Tout autre paramètre est refusé (400).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from aeropulse import config
from aeropulse.analytics import queries
from aeropulse.analytics.engine import SOURCE, Analytics
from aeropulse.mlops.store import BundleUnavailableError, PrefixSync

HEADERS = {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"}
_INT_PARAMS = frozenset({"year", "month", "limit"})
_DIGITS = re.compile(r"^\d{1,4}$")

_engine: Analytics | None = None


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": HEADERS,
        "body": json.dumps(payload, ensure_ascii=False, default=str),
    }


def _error(status: int, code: str, message: str, event: dict[str, Any]) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    ctx = event.get("requestContext")
    if isinstance(ctx, dict) and ctx.get("requestId"):
        error["correlation_id"] = str(ctx["requestId"])
    return _response(status, {"error": error})


def get_engine() -> Analytics:
    global _engine
    if _engine is None:
        bucket = os.environ.get("AEROPULSE_DATA_BUCKET")
        if bucket:
            import boto3  # fourni par le runtime Lambda

            dest = Path(os.environ.get("AEROPULSE_WORK_DIR", "/tmp/aeropulse")) / "flights"
            prefix = os.environ.get("AEROPULSE_PROCESSED_PREFIX", "processed/flights/")
            PrefixSync(boto3.client("s3"), bucket, prefix, dest).sync()
            _engine = Analytics(dest)
        else:
            _engine = Analytics(
                Path(os.environ.get("AEROPULSE_PROCESSED_DIR", "data/processed/flights"))
            )
    return _engine


def parse_query(params: dict[str, Any] | None) -> tuple[dict[str, object], object]:
    """Convertit les paramètres de chaîne de requête ; la validation reste dans ``queries``."""
    filters: dict[str, object] = {}
    limit: object = None
    for name, raw in (params or {}).items():
        value: object = raw
        if name in _INT_PARAMS and isinstance(raw, str) and _DIGITS.fullmatch(raw):
            value = int(raw)
        if name == "limit":
            limit = value
        else:
            filters[name] = value
    return filters, limit


def meta(engine: Analytics) -> dict[str, Any]:
    allowed = engine.allowed
    return {
        "airports": sorted(allowed.airports),
        "carriers": sorted(allowed.carriers),
        "destinations": sorted(allowed.destinations),
        "dimensions": sorted(queries.DIMENSIONS),
        "filters": sorted(queries.FILTERS),
        "max_limit": queries.MAX_LIMIT,
        "min_sample_size": config.MIN_SAMPLE_SIZE,
        "period": {"start": str(config.STUDY_START), "end": str(config.STUDY_END)},
        "source": SOURCE,
        "note": "données historiques, pas des conditions actuelles",
    }


def handler(
    event: dict[str, Any], context: Any = None, engine: Analytics | None = None
) -> dict[str, Any]:
    try:
        if event.get("httpMethod") not in (None, "GET"):
            return _error(405, "method_not_allowed", "méthode non autorisée", event)
        resource = str(event.get("resource") or event.get("path") or "")
        if resource.endswith("/meta"):
            return _response(200, meta(engine or get_engine()))
        if "/stats/" in resource:
            dimension = (event.get("pathParameters") or {}).get("dimension")
            filters, limit = parse_query(event.get("queryStringParameters"))
            result = (engine or get_engine()).statistics(str(dimension), filters, limit)
            return _response(200, result)
        return _error(404, "not_found", "route inconnue", event)
    except queries.InvalidParameterError as exc:
        return _error(400, "invalid_parameter", str(exc), event)
    except BundleUnavailableError:
        return _error(503, "data_unavailable", "données indisponibles", event)
    except Exception:  # noqa: BLE001 - jamais de détail interne dans la réponse
        return _error(500, "internal_error", "erreur interne", event)
