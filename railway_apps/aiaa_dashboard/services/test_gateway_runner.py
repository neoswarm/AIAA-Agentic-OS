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
