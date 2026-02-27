"""Contract tests for GatewayRunner compatibility with AgentRunner."""

from __future__ import annotations

import inspect
import json
from typing import Any

import pytest

from services.agent_runner import AgentRunner
from services.gateway_client import GatewayClientError
from services.gateway_runner import GatewayRunner, RunnerError


CONTRACT_METHODS = (
    "create_session",
    "attach_store",
    "ensure_session",
    "list_sessions",
    "get_session",
    "has_session",
    "send_message",
    "get_stream",
)


class FakeGatewayClient:
    """Minimal scripted gateway client for runner transport tests."""

    def __init__(self, scripted_responses: list[dict[str, Any] | Exception]) -> None:
        self._scripted = list(scripted_responses)
        self.calls: list[dict[str, Any]] = []

    def post_json(
        self,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: Any = None,
        headers: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        del params, timeout_seconds
        self.calls.append(
            {
                "path": path,
                "payload": dict(payload or {}),
                "headers": dict(headers or {}),
            }
        )
        if not self._scripted:
            raise AssertionError("No scripted gateway response available")
        item = self._scripted.pop(0)
        if isinstance(item, Exception):
            raise item
        return dict(item)


def _runner() -> GatewayRunner:
    return GatewayRunner(cwd="/tmp", token_provider=lambda: "test-token")


def _drain_events(runner: GatewayRunner, session_id: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    q = runner._output_queues[session_id]
    while not q.empty():
        events.append(q.get())
    return events


@pytest.mark.parametrize("method_name", CONTRACT_METHODS)
def test_gateway_runner_matches_agent_runner_method_signatures(
    method_name: str,
) -> None:
    gateway_method = getattr(GatewayRunner, method_name)
    agent_method = getattr(AgentRunner, method_name)
    assert inspect.signature(gateway_method) == inspect.signature(agent_method)


def test_gateway_runner_session_lifecycle_contract() -> None:
    runner = _runner()

    session = runner.create_session(title="My Session")
    session_id = session["id"]
    assert runner.has_session(session_id)

    stored = runner.get_session(session_id)
    assert stored is not None
    assert stored["title"] == "My Session"

    ensured = runner.ensure_session(
        session_id,
        title="Renamed Session",
        sdk_session_id="sdk-session-123",
    )
    assert ensured["id"] == session_id
    assert ensured["title"] == "Renamed Session"

    stored = runner.get_session(session_id)
    assert stored is not None
    assert stored["sdk_session_id"] == "sdk-session-123"

    sessions = runner.list_sessions()
    assert sessions
    assert sessions[0]["id"] == session_id


def test_gateway_runner_send_message_errors_follow_contract() -> None:
    runner = _runner()

    with pytest.raises(ValueError, match="Message cannot be empty"):
        runner.send_message("missing-session", "")

    with pytest.raises(KeyError, match="Session not found"):
        runner.send_message("missing-session", "hello")

    session_id = runner.create_session()["id"]
    runner._sessions[session_id]["status"] = "running"

    with pytest.raises(RunnerError, match="already running"):
        runner.send_message(session_id, "hello")


def test_gateway_runner_stream_emits_sse_payload() -> None:
    runner = _runner()
    session_id = runner.create_session()["id"]

    runner._output_queues[session_id].put(
        {"type": "done", "timestamp": "2026-01-01T00:00:00Z"}
    )

    chunk = next(runner.get_stream(session_id))
    assert chunk.startswith("data: ")
    payload = json.loads(chunk[len("data: ") :].strip())
    assert payload["type"] == "done"


def test_gateway_runner_transport_calls_gateway_client_and_emits_result() -> None:
    gateway_client = FakeGatewayClient([{"output_text": "hello from gateway"}])
    runner = GatewayRunner(
        cwd="/tmp",
        token_provider=lambda: "sk-ant-test-token",
        gateway_client=gateway_client,
    )
    session_id = runner.create_session()["id"]

    runner._run_agent(session_id, "hello")

    assert len(gateway_client.calls) == 1
    call = gateway_client.calls[0]
    assert call["path"] == "/v1/responses"
    assert call["payload"] == {"input": "hello", "stream": False}
    assert call["headers"]["X-Anthropic-Api-Key"] == "sk-ant-test-token"

    events = _drain_events(runner, session_id)
    assert [event["type"] for event in events] == ["result", "done"]
    assert events[0]["content"] == "hello from gateway"

    session = runner.get_session(session_id)
    assert session is not None
    assert session["status"] == "idle"
    assert session["last_error"] is None
    assert session["messages"][-1]["content"] == "hello from gateway"


def test_gateway_runner_transport_emits_error_when_gateway_fails() -> None:
    gateway_client = FakeGatewayClient([GatewayClientError("gateway unavailable")])
    runner = GatewayRunner(
        cwd="/tmp",
        token_provider=lambda: "sk-ant-test-token",
        gateway_client=gateway_client,
    )
    session_id = runner.create_session()["id"]

    runner._run_agent(session_id, "hello")

    events = _drain_events(runner, session_id)
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "gateway unavailable" in events[0]["content"]

    session = runner.get_session(session_id)
    assert session is not None
    assert session["status"] == "error"
    assert "gateway unavailable" in str(session["last_error"])
