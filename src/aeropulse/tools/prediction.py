"""Outils de prédiction et d'explication (FR-19) : ils appellent le service de prédiction injecté.

``tools/`` ne dépend pas de ``api/`` : le service est passé sous forme de fonction par l'appelant
(la route ``/v1/chat``). Les erreurs du service (saisie invalide, vol inconnu, date hors
couverture) deviennent des erreurs d'outil lisibles par le modèle de langage.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from aeropulse.features.serving import ServingError
from aeropulse.tools.schemas import AIRPORT, ToolError, ToolSpec

PredictFn = Callable[[Mapping[str, Any]], dict[str, Any]]

_FLIGHT = {
    "airline": {"type": "string", "description": "Code compagnie IATA"},
    "origin": AIRPORT,
    "destination": {"type": "string", "description": "Code IATA de destination"},
    "scheduled_departure": {
        "type": "string",
        "description": "Départ prévu, ISO 8601 avec fuseau, ex. 2025-03-14T08:30:00-04:00",
    },
    "flight_id": {
        "type": "string",
        "description": "Ou bien : vol de 2025 à rejouer, ex. 2025-03-14_AA100_JFK_0830",
    },
}
PREDICT = ToolSpec(
    name="predict_flight_delay",
    description="Probabilité qu'un vol parte avec plus de 15 min de retard, estimée 2 h avant "
    "le départ (saisie d'un vol, ou rejeu d'un vol de 2025 par flight_id).",
    properties=_FLIGHT,
)
EXPLAIN = ToolSpec(
    name="explain_prediction",
    description="Principales influences (SHAP) sur la prédiction d'un vol : influence, pas cause.",
    properties=_FLIGHT,
)


def _request(args: dict[str, Any]) -> dict[str, Any]:
    if "flight_id" in args:
        if len(args) > 1:
            raise ToolError("flight_id s'utilise seul")
        return {"flight_id": args["flight_id"]}
    missing = [
        k for k in ("airline", "origin", "destination", "scheduled_departure") if k not in args
    ]
    if missing:
        raise ToolError(f"paramètres manquants {missing} (ou bien flight_id)")
    return dict(args)


def _call(predict: PredictFn, args: dict[str, Any]) -> dict[str, Any]:
    try:
        return predict(_request(args))
    except ServingError as exc:
        raise ToolError(str(exc)) from exc


def predict_flight_delay(predict: PredictFn, args: dict[str, Any]) -> dict[str, Any]:
    result = _call(predict, args)
    keep = (
        "mode",
        "delay_probability",
        "is_delayed_predicted",
        "threshold",
        "model_versions",
        "weather",
        "observed",
        "disclaimer",
    )
    return {
        "source": "modèle de classification AeroPulse",
        **{k: result[k] for k in keep if k in result},
    }


def explain_prediction(predict: PredictFn, args: dict[str, Any]) -> dict[str, Any]:
    result = _call(predict, args)
    return {
        "source": "contributions SHAP du modèle AeroPulse",
        "delay_probability": result.get("delay_probability"),
        "explanation": result.get("explanation", []),
        "note": "influence sur le modèle, pas une cause",
    }
