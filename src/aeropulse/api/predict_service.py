"""Service de prédiction indépendant de l'hébergement (Lambda, local, tests).

Valide l'entrée, construit les variables T-2h, appelle un **backend de modèle** (en processus
aujourd'hui ; endpoint SageMaker plus tard, derrière le même contrat) et renvoie la réponse de
``POST /v1/predict`` : probabilité, décision au seuil figé, version, explications. Aucune durée de
retard n'est estimée (ADR-0017).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import pandas as pd

from aeropulse.features.serving import FeatureBuilder, InvalidRequestError, ReplayStore

DISCLAIMER = (
    "Modèle entraîné sur des données historiques 2023–2025 (JFK, EWR, LGA) ; "
    "pas une prévision en temps réel. Les explications indiquent une influence sur le modèle, "
    "pas une cause."
)


class ModelBackend(Protocol):
    """Contrat commun au modèle en processus et à l'endpoint SageMaker."""

    model_version: str
    threshold: float

    def predict(self, rows: pd.DataFrame) -> pd.DataFrame: ...

    def explain(self, rows: pd.DataFrame, top_k: int = 5) -> list[dict[str, Any]]: ...


class PredictionService:
    def __init__(
        self,
        builder: FeatureBuilder,
        backend: ModelBackend,
        replay: ReplayStore | None = None,
    ) -> None:
        self._builder = builder
        self._backend = backend
        self._replay = replay

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(request, Mapping):
            raise InvalidRequestError("le corps doit être un objet JSON")
        observed: bool | None = None
        if "flight_id" in request:
            if self._replay is None:
                raise InvalidRequestError("mode rejeu non disponible")
            features, observed = self._replay.get(request)
            mode = "replay"
        else:
            features = self._builder.build(request)
            mode = "manual"
        prediction = self._backend.predict(features).iloc[0]
        explanation = self._backend.explain(features)[0]
        response: dict[str, Any] = {
            "mode": mode,
            "delay_probability": round(float(prediction["delay_probability"]), 4),
            "is_delayed_predicted": bool(prediction["is_delayed_predicted"]),
            "threshold": round(float(self._backend.threshold), 4),
            "model_versions": {"classification": self._backend.model_version},
            "explanation": [
                {
                    "feature": c["feature"],
                    "contribution": round(float(c["shap"]), 4),
                    "direction": c["direction"],
                }
                for c in explanation["contributions"]
            ],
            "weather": self._builder.weather_summary(features),
            "disclaimer": DISCLAIMER,
        }
        if observed is not None:
            response["observed"] = {
                "is_delayed": observed,
                "note": "résultat historique réel, fourni pour comparaison avec la prédiction",
            }
        return response
