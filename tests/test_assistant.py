"""Outils nommés, orchestrateur borné et route /v1/chat (FR-19 à FR-22, AC-14, AC-15, AC-17).

Aucun appel à AWS : le client Bedrock est remplacé par un faux client scénarisé.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from aeropulse.analytics.engine import Analytics
from aeropulse.api import assistant_handler
from aeropulse.assistant import grounding
from aeropulse.assistant.orchestrator import TRUNCATED, WITHHELD, Assistant
from aeropulse.features.serving import NotFoundError
from aeropulse.tools import ToolError, ToolRegistry, build_registry
from test_analytics import _flights


@pytest.fixture
def analytics(tmp_path: Path) -> Analytics:
    target = tmp_path / "flights"
    _flights().to_parquet(target, partition_cols=["year", "month"], index=False)
    return Analytics(target)


def fake_predict(request: Mapping[str, Any]) -> dict[str, Any]:
    if request.get("flight_id") == "2025-03-14_AA999_JFK_0830":
        raise NotFoundError("vol introuvable dans la période de test")
    return {
        "mode": "replay" if "flight_id" in request else "manual",
        "delay_probability": 0.37,
        "is_delayed_predicted": True,
        "threshold": 0.2,
        "model_versions": {"classification": "clf-test"},
        "explanation": [{"feature": "departure_hour", "contribution": 0.08}],
    }


@pytest.fixture
def registry(analytics: Analytics) -> ToolRegistry:
    return build_registry(analytics, fake_predict)


# --------------------------------------------------------------------------- outils
def test_registry_exposes_the_seven_tools(registry: ToolRegistry) -> None:
    assert registry.names == sorted(
        [
            "explain_prediction",
            "generate_delay_report",
            "get_airline_delay_statistics",
            "get_airport_delay_statistics",
            "get_flight_statistics",
            "get_route_delay_statistics",
            "predict_flight_delay",
        ]
    )
    for spec in registry.specs():
        assert spec.input_schema()["additionalProperties"] is False


def test_statistics_tools_return_source_and_sample_size(registry: ToolRegistry) -> None:
    out = registry.call("get_airline_delay_statistics", {"airline": "AA"}, [])
    assert out["source"] and out["n_flights"] == 41
    assert out["rows"][0]["delay_rate"] == pytest.approx(0.25)
    overview = registry.call("get_flight_statistics", {"year": 2024}, [])
    assert overview["n_flights"] == 46 and overview["overall_delay_rate"] == pytest.approx(0.25)
    small = registry.call("get_route_delay_statistics", {"origin": "LGA", "destination": "BOS"}, [])
    assert small["rows"][0]["delay_rate"] is None  # < 30 vols : données insuffisantes


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("get_airline_delay_statistics", {"airline": "AA", "sql": "SELECT 1"}),
        ("get_airline_delay_statistics", {"airline": "AA'; DROP TABLE flights;--"}),
        ("get_airline_delay_statistics", {"airline": "QQ"}),
        ("get_airline_delay_statistics", {}),
        ("get_airport_delay_statistics", {"airport": "BOS"}),
        ("get_airport_delay_statistics", {"airport": "JFK", "year": "2024"}),
        ("get_airport_delay_statistics", {"airport": "JFK", "month": 13}),
        ("get_flight_statistics", {"year": True}),
        ("run_sql", {"query": "SELECT * FROM flights"}),
        ("predict_flight_delay", {"flight_id": "2025-03-14_AA100_JFK_0830", "origin": "JFK"}),
        ("predict_flight_delay", {"airline": "AA"}),
        ("predict_flight_delay", {"flight_id": "2025-03-14_AA999_JFK_0830"}),
        ("generate_delay_report", {"title": "Rapport"}),  # aucun résultat préalable
    ],
)
def test_tools_reject_invalid_calls(
    registry: ToolRegistry, name: str, args: dict[str, Any]
) -> None:
    with pytest.raises(ToolError):
        registry.call(name, args, [])


def test_prediction_tools_use_injected_service(registry: ToolRegistry) -> None:
    out = registry.call("predict_flight_delay", {"flight_id": "2025-01-01_AA1_JFK_0659"}, [])
    assert out["delay_probability"] == 0.37 and out["mode"] == "replay"
    assert "explanation" not in out
    why = registry.call("explain_prediction", {"flight_id": "2025-01-01_AA1_JFK_0659"}, [])
    assert why["explanation"][0]["feature"] == "departure_hour"


def test_report_contains_no_number_absent_from_its_inputs(registry: ToolRegistry) -> None:
    first = registry.call("get_airline_delay_statistics", {"airline": "AA"}, [])
    history = [{"tool": "get_airline_delay_statistics", "result": first}]
    report = registry.call("generate_delay_report", {"title": "Retards AA"}, history)
    allowed = grounding.allowed_numbers([first], "")
    assert grounding.ungrounded_numbers(report["report_markdown"], allowed) == []  # AC-17


def test_without_predict_service_only_statistics_tools(analytics: Analytics) -> None:
    assert "predict_flight_delay" not in build_registry(analytics).names


# --------------------------------------------------------------------------- garde-fou
def test_grounding_accepts_roundings_and_rejects_inventions() -> None:
    allowed = grounding.allowed_numbers([{"delay_rate": 0.2413, "n_flights": 621512}], "en 2024 ?")
    assert (
        grounding.ungrounded_numbers("24,1 % sur 621 512 vols en 2024, seuil 15 min", allowed) == []
    )
    assert grounding.ungrounded_numbers("environ 24 %", allowed) == []
    assert grounding.ungrounded_numbers("37 % des vols", allowed) == [37.0]
    assert grounding.ungrounded_numbers("621 000 vols", allowed) == [621000.0]


# --------------------------------------------------------------------------- orchestrateur
class FakeClient:
    """Rejoue une suite de réponses Converse et garde les requêtes reçues."""

    def __init__(self, replies: list[dict[str, Any]]) -> None:
        self.replies = replies
        self.requests: list[dict[str, Any]] = []

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        self.requests.append(kwargs)
        return self.replies[min(len(self.requests) - 1, len(self.replies) - 1)]


def tool_result_of(client: FakeClient) -> dict[str, Any]:
    """Premier résultat d'outil renvoyé au modèle (la liste des messages est partagée)."""
    for message in client.requests[-1]["messages"]:
        for block in message["content"]:
            if "toolResult" in block:
                return dict(block["toolResult"])
    raise AssertionError("aucun résultat d'outil")


def tool_use(name: str, args: dict[str, Any], uid: str = "t1") -> dict[str, Any]:
    content = [{"toolUse": {"toolUseId": uid, "name": name, "input": args}}]
    return {
        "output": {"message": {"role": "assistant", "content": content}},
        "stopReason": "tool_use",
    }


def final(text: str) -> dict[str, Any]:
    msg = {"role": "assistant", "content": [{"text": text}]}
    return {"output": {"message": msg}, "stopReason": "end_turn"}


def test_assistant_calls_tool_then_answers_with_grounded_numbers(registry: ToolRegistry) -> None:
    client = FakeClient(
        [
            tool_use("get_airline_delay_statistics", {"airline": "AA"}),
            final("AA : 25 % de retards sur 40 vols."),
        ]
    )
    result = Assistant(client, "modele-de-test", registry).answer("Retards d'American ?")
    assert result.grounded and result.tool_calls == 1 and not result.truncated
    assert result.answer.startswith("AA : 25 %")
    assert result.sources[0]["tool"] == "get_airline_delay_statistics"
    first = client.requests[0]
    assert first["modelId"] == "modele-de-test" and first["inferenceConfig"]["maxTokens"] == 800
    assert len(first["toolConfig"]["tools"]) == 7
    tool_result = tool_result_of(client)
    assert tool_result["status"] == "success" and tool_result["toolUseId"] == "t1"


def test_invented_numbers_are_withheld(registry: ToolRegistry) -> None:
    client = FakeClient(
        [
            tool_use("get_airline_delay_statistics", {"airline": "AA"}),
            final("AA : 37 % de retards."),
        ]
    )
    result = Assistant(client, "m", registry).answer("Retards d'American ?")
    assert not result.grounded and result.answer == WITHHELD


def test_answer_without_any_tool_cannot_contain_numbers(registry: ToolRegistry) -> None:
    result = Assistant(
        FakeClient([final("Environ 42 % des vols sont en retard.")]), "m", registry
    ).answer("?")
    assert result.answer == WITHHELD and result.tool_calls == 0


def test_tool_loop_is_bounded(registry: ToolRegistry) -> None:
    client = FakeClient([tool_use("get_flight_statistics", {})])  # le modèle ne s'arrête jamais
    result = Assistant(client, "m", registry, max_rounds=3).answer("?")
    assert result.truncated and result.answer == TRUNCATED
    assert len(client.requests) == 4 and result.tool_calls == 3


def test_tool_errors_are_returned_to_the_model(registry: ToolRegistry) -> None:
    client = FakeClient(
        [tool_use("run_sql", {"query": "DROP TABLE flights"}), final("Je ne peux pas.")]
    )
    result = Assistant(client, "m", registry).answer("?")
    tool_result = tool_result_of(client)
    assert tool_result["status"] == "error" and result.grounded and result.sources == []


# --------------------------------------------------------------------------- route /v1/chat
def _event(body: Any) -> dict[str, Any]:
    return {"httpMethod": "POST", "body": body if isinstance(body, str) else json.dumps(body)}


def test_chat_is_unavailable_without_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AEROPULSE_BEDROCK_MODEL_ID", raising=False)
    res = assistant_handler.handler(_event({"message": "Bonjour"}))
    assert res["statusCode"] == 503
    assert json.loads(res["body"])["error"]["code"] == "assistant_unavailable"


@pytest.mark.parametrize(
    "body",
    [
        "{pas du json",
        {"message": ""},
        {"message": "x" * 1001},
        {"message": "ok", "sql": "x"},
        ["message"],
        {"message": 3},
    ],
)
def test_chat_rejects_invalid_bodies(body: Any) -> None:
    assert assistant_handler.handler(_event(body))["statusCode"] == 400


def test_chat_returns_contract_with_injected_assistant(registry: ToolRegistry) -> None:
    client = FakeClient(
        [tool_use("get_airline_delay_statistics", {"airline": "AA"}), final("AA : 25 %.")]
    )
    res = assistant_handler.handler(
        _event({"message": "Retards AA ?", "session_id": "abc"}),
        assistant=Assistant(client, "m", registry),
    )
    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert set(body) == {"answer", "sources", "tool_calls", "truncated", "grounded"}


def test_model_errors_map_to_503_without_details(registry: ToolRegistry) -> None:
    class ClientError(Exception):
        pass

    class Broken(FakeClient):
        def converse(self, **kwargs: Any) -> dict[str, Any]:
            raise ClientError("AccessDeniedException arn:aws:bedrock:secret")

    res = assistant_handler.handler(
        _event({"message": "?"}), assistant=Assistant(Broken([]), "m", registry)
    )
    assert res["statusCode"] == 503 and "secret" not in res["body"]
