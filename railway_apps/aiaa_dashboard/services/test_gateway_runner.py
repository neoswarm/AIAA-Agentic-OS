"""Contract tests for GatewayRunner compatibility with AgentRunner."""

from __future__ import annotations

import inspect
import json

import pytest

from services.agent_runner import AgentRunner
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


def _runner() -> GatewayRunner:
    return GatewayRunner(cwd="/tmp", token_provider=lambda: "test-token")


def _parse_sse_payload(chunk: str) -> dict[str, object]:
    assert chunk.startswith("data: ")
    return json.loads(chunk[len("data: ") :].strip())


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
