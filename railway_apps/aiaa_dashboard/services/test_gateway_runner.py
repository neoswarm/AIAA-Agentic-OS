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


def _parse_sse_payload(chunk: str) -> dict[str, object]:
    assert chunk.startswith("data: ")
    return json.loads(chunk[len("data: ") :].strip())


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


def test_gateway_runner_stream_emits_success_event_before_terminal_done() -> None:
    runner = _runner()
    session_id = runner.create_session()["id"]

    runner._output_queues[session_id].put(
        {"type": "text", "content": "Hello", "timestamp": "2026-01-01T00:00:00Z"}
    )
    runner._output_queues[session_id].put(
        {"type": "done", "timestamp": "2026-01-01T00:00:01Z"}
    )

    chunks = list(runner.get_stream(session_id, keepalive_seconds=1))
    payloads = [_parse_sse_payload(chunk) for chunk in chunks]
    assert payloads == [
        {"type": "text", "content": "Hello", "timestamp": "2026-01-01T00:00:00Z"},
        {"type": "done", "timestamp": "2026-01-01T00:00:01Z"},
    ]


def test_gateway_runner_stream_emits_terminal_error_and_stops() -> None:
    runner = _runner()
    session_id = runner.create_session()["id"]

    runner._output_queues[session_id].put(
        {"type": "error", "content": "stream failed", "timestamp": "2026-01-01T00:00:00Z"}
    )
    runner._output_queues[session_id].put(
        {"type": "done", "timestamp": "2026-01-01T00:00:01Z"}
    )

    chunks = list(runner.get_stream(session_id, keepalive_seconds=1))
    payloads = [_parse_sse_payload(chunk) for chunk in chunks]
    assert payloads == [
        {
            "type": "error",
            "content": "stream failed",
            "timestamp": "2026-01-01T00:00:00Z",
        }
    ]


def test_gateway_runner_stream_emits_terminal_done_and_stops() -> None:
    runner = _runner()
    session_id = runner.create_session()["id"]

    runner._output_queues[session_id].put(
        {"type": "done", "timestamp": "2026-01-01T00:00:00Z"}
    )
    runner._output_queues[session_id].put(
        {"type": "text", "content": "late", "timestamp": "2026-01-01T00:00:01Z"}
    )

    chunks = list(runner.get_stream(session_id, keepalive_seconds=1))
    payloads = [_parse_sse_payload(chunk) for chunk in chunks]
    assert payloads == [{"type": "done", "timestamp": "2026-01-01T00:00:00Z"}]


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


def test_gateway_runner_maps_gateway_session_and_correlation_ids() -> None:
    runner = _runner()
    local_session_id = "dashboard-session-1"
    runner.ensure_session(local_session_id)

    runner._capture_sdk_session_id(
        local_session_id,
        raw_message=object(),
        payload={
            "session_id": "gateway-session-1",
            "correlation_id": "corr-1",
        },
    )

    assert runner.has_session("gateway-session-1")
    assert runner.has_session("corr-1")

    mapped_by_session = runner.get_session("gateway-session-1")
    assert mapped_by_session is not None
    assert mapped_by_session["id"] == local_session_id
    assert mapped_by_session["sdk_session_id"] == "gateway-session-1"

    mapped_by_correlation = runner.get_session("corr-1")
    assert mapped_by_correlation is not None
    assert mapped_by_correlation["id"] == local_session_id


def test_gateway_runner_parse_message_includes_mapped_ids() -> None:
    runner = _runner()
    local_session_id = "dashboard-session-2"
    runner.ensure_session(local_session_id)
    runner._capture_sdk_session_id(
        local_session_id,
        raw_message=object(),
        payload={
            "session_id": "gateway-session-2",
            "correlation_id": "corr-2",
        },
    )

    event = runner._parse_message(
        {
            "type": "assistant_message",
            "content": "hello",
            "session_id": "gateway-session-2",
            "correlation_id": "corr-2",
        }
    )

    assert event is not None
    assert event["type"] == "text"
    assert event["session_id"] == local_session_id
    assert event["correlation_id"] == "corr-2"


def test_gateway_runner_stream_continues_with_correlation_alias() -> None:
    runner = _runner()
    local_session_id = "dashboard-session-3"
    runner.ensure_session(local_session_id)
    runner._capture_sdk_session_id(
        local_session_id,
        raw_message=object(),
        payload={
            "session_id": "gateway-session-3",
            "correlation_id": "corr-3",
        },
    )

    runner._output_queues[local_session_id].put(
        {
            "type": "text",
            "content": "continuing stream",
            "timestamp": "2026-01-01T00:00:00Z",
        }
    )

    chunk = next(runner.get_stream("corr-3"))
    assert chunk.startswith("data: ")
    payload = json.loads(chunk[len("data: ") :].strip())
    assert payload["type"] == "text"
    assert payload["content"] == "continuing stream"


def test_gateway_runner_stream_suppresses_duplicate_and_delayed_chunks() -> None:
    runner = _runner()
    session_id = runner.create_session()["id"]
    queue = runner._output_queues[session_id]

    queue.put(
        {
            "type": "text",
            "content": "Hel",
            "payload": {"chunk_id": "chunk-1", "sequence": 1},
        }
    )
    queue.put(
        {
            "type": "text",
            "content": "Hel",
            "payload": {"chunk_id": "chunk-1", "sequence": 1},
        }
    )
    queue.put(
        {
            "type": "text",
            "content": "lo",
            "payload": {"chunk_id": "chunk-0", "sequence": 0},
        }
    )
    queue.put(
        {
            "type": "text",
            "content": "lo",
            "payload": {"chunk_id": "chunk-2", "sequence": 2},
        }
    )
    queue.put({"type": "done", "timestamp": "2026-01-01T00:00:00Z"})

    frames = list(runner.get_stream(session_id, keepalive_seconds=1))
    payloads = [_parse_sse_payload(frame) for frame in frames]

    text_payloads = [payload for payload in payloads if payload.get("type") == "text"]
    assert [payload.get("content") for payload in text_payloads] == ["Hel", "lo"]
    assert payloads[-1]["type"] == "done"


def test_gateway_runner_stream_keeps_chunks_without_reconnect_metadata() -> None:
    runner = _runner()
    session_id = runner.create_session()["id"]
    queue = runner._output_queues[session_id]

    queue.put({"type": "text", "content": "ha"})
    queue.put({"type": "text", "content": "ha"})
    queue.put({"type": "done", "timestamp": "2026-01-01T00:00:00Z"})

    frames = list(runner.get_stream(session_id, keepalive_seconds=1))
    payloads = [_parse_sse_payload(frame) for frame in frames]

    text_payloads = [payload for payload in payloads if payload.get("type") == "text"]
    assert [payload.get("content") for payload in text_payloads] == ["ha", "ha"]
