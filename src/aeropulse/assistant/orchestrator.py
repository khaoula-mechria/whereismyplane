"""Boucle LLM et outils, bornée et journalisée (CMP-12, FR-19, NFR-06).

Utilise l'API Converse de Bedrock (appel d'outils). Le client est injecté : un faux client sert
aux tests, ``boto3.client("bedrock-runtime")`` en production. Le modèle est un paramètre
(ADR-0012 : non choisi). Bornes : nombre de tours d'outils, jetons de sortie, durée totale.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from aeropulse.assistant import grounding
from aeropulse.assistant.prompts import SYSTEM_PROMPT
from aeropulse.tools import ToolError, ToolRegistry

LOG = logging.getLogger("aeropulse.assistant")
WITHHELD = (
    "Je ne peux pas vous donner cette réponse de façon fiable : elle contenait des chiffres "
    "absents des données consultées. Reformulez la question ou consultez les statistiques."
)
TRUNCATED = "Je n'ai pas pu terminer l'analyse dans les limites prévues. Précisez la question."


class ConverseClient(Protocol):
    def converse(self, **kwargs: Any) -> dict[str, Any]: ...


@dataclass
class AssistantResult:
    answer: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: int = 0
    truncated: bool = False
    grounded: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": self.sources,
            "tool_calls": self.tool_calls,
            "truncated": self.truncated,
            "grounded": self.grounded,
        }


class Assistant:
    def __init__(
        self,
        client: ConverseClient,
        model_id: str,
        registry: ToolRegistry,
        *,
        max_rounds: int = 4,
        max_tokens: int = 800,
        time_budget_s: float = 24.0,
    ) -> None:
        self._client = client
        self._model_id = model_id
        self._registry = registry
        self._max_rounds = max_rounds
        self._max_tokens = max_tokens
        self._time_budget_s = time_budget_s

    def _tool_config(self) -> dict[str, Any]:
        return {
            "tools": [
                {
                    "toolSpec": {
                        "name": spec.name,
                        "description": spec.description,
                        "inputSchema": {"json": spec.input_schema()},
                    }
                }
                for spec in self._registry.specs()
            ]
        }

    def _run_tool(self, block: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
        use = block["toolUse"]
        name = str(use.get("name"))
        content: list[dict[str, Any]]
        try:
            result = self._registry.call(name, use.get("input"), history)
            history.append({"tool": name, "result": result})
            content, status = [{"json": result}], "success"
        except ToolError as exc:
            history.append({"tool": name, "error": str(exc)})
            content, status = [{"text": f"Erreur d'outil : {exc}"}], "error"
        LOG.info(json.dumps({"event": "tool_call", "tool": name, "status": status}))
        return {
            "toolResult": {"toolUseId": use.get("toolUseId"), "content": content, "status": status}
        }

    def answer(self, message: str) -> AssistantResult:
        started = time.monotonic()
        messages: list[dict[str, Any]] = [{"role": "user", "content": [{"text": message}]}]
        history: list[dict[str, Any]] = []
        for round_index in range(self._max_rounds + 1):
            response = self._client.converse(
                modelId=self._model_id,
                system=[{"text": SYSTEM_PROMPT}],
                messages=messages,
                toolConfig=self._tool_config(),
                inferenceConfig={"maxTokens": self._max_tokens, "temperature": 0},
            )
            output = response["output"]["message"]
            messages.append(output)
            uses = [b for b in output.get("content", []) if "toolUse" in b]
            if response.get("stopReason") != "tool_use" or not uses:
                text = " ".join(b["text"] for b in output.get("content", []) if "text" in b)
                return self._finish(text.strip(), message, history)
            out_of_rounds = round_index >= self._max_rounds
            if out_of_rounds or time.monotonic() - started > self._time_budget_s:
                break
            messages.append({"role": "user", "content": [self._run_tool(b, history) for b in uses]})
        return AssistantResult(
            answer=TRUNCATED,
            sources=self._sources(history),
            tool_calls=len(history),
            truncated=True,
        )

    @staticmethod
    def _sources(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for item in history:
            if "result" in item:
                result = item["result"]
                out.append({"tool": item["tool"], "source": result.get("source")})
        return out

    def _finish(self, text: str, message: str, history: list[dict[str, Any]]) -> AssistantResult:
        results = [h["result"] for h in history if "result" in h]
        bad = grounding.ungrounded_numbers(text, grounding.allowed_numbers(results, message))
        if bad:
            LOG.warning(json.dumps({"event": "answer_withheld", "ungrounded": len(bad)}))
            return AssistantResult(
                answer=WITHHELD,
                sources=self._sources(history),
                tool_calls=len(history),
                grounded=False,
            )
        return AssistantResult(answer=text, sources=self._sources(history), tool_calls=len(history))
