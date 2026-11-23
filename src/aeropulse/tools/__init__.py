"""Outils nommés de l'assistant (CMP-10) ; ne dépend ni de Bedrock ni de ``api/``.

``build_registry`` assemble les sept outils de l'API (api-design §3) à partir du moteur
analytique et d'une fonction de prédiction injectée. Le registre est le **seul** moyen pour le
modèle de langage d'obtenir des données : pas de SQL libre, paramètres en liste blanche.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from aeropulse.analytics.engine import Analytics
from aeropulse.tools import delay_report, prediction, statistics
from aeropulse.tools.schemas import ToolError, ToolSpec, check_args

Runner = Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]]


@dataclass(frozen=True)
class Tool:
    spec: ToolSpec
    run: Runner


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {t.spec.name: t for t in tools}

    @property
    def names(self) -> list[str]:
        return sorted(self._tools)

    def specs(self) -> list[ToolSpec]:
        return [self._tools[name].spec for name in self.names]

    def call(self, name: str, args: object, history: list[dict[str, Any]]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError(f"outil inconnu : {name}")
        return tool.run(check_args(tool.spec, args), history)


def build_registry(
    analytics: Analytics, predict: prediction.PredictFn | None = None
) -> ToolRegistry:
    def stats(fn: Callable[[Analytics, dict[str, Any]], dict[str, Any]]) -> Runner:
        return lambda args, _history: fn(analytics, args)

    tools = [
        Tool(statistics.AIRLINE, stats(statistics.airline_statistics)),
        Tool(statistics.AIRPORT_SPEC, stats(statistics.airport_statistics)),
        Tool(statistics.ROUTE, stats(statistics.route_statistics)),
        Tool(statistics.OVERVIEW, stats(statistics.flight_statistics)),
        Tool(delay_report.REPORT, delay_report.generate_delay_report),
    ]
    if predict is not None:
        p = predict
        tools.append(
            Tool(prediction.PREDICT, lambda args, _h: prediction.predict_flight_delay(p, args))
        )
        tools.append(
            Tool(prediction.EXPLAIN, lambda args, _h: prediction.explain_prediction(p, args))
        )
    return ToolRegistry(tools)


__all__ = ["Tool", "ToolError", "ToolRegistry", "ToolSpec", "build_registry"]
