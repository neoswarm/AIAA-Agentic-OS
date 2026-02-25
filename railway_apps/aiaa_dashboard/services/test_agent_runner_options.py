#!/usr/bin/env python3
"""Unit tests for AgentRunner SDK option compatibility helpers."""

from __future__ import annotations

import json

from services.agent_runner import (
    AgentRunner,
    _frame_sse_done_event,
    _frame_sse_error_event,
    _frame_sse_ping_event,
)


class ModernOptions:
    def __init__(
        self,
        *,
        allowed_tools=None,
        permission_mode=None,
        setting_sources=None,
        cwd=None,
        resume=None,
        env=None,
    ):
        self.kwargs = {
            "allowed_tools": allowed_tools,
            "permission_mode": permission_mode,
            "setting_sources": setting_sources,
            "cwd": cwd,
            "resume": resume,
            "env": env,
        }


class ModernOptionsWithStderr:
    def __init__(
        self,
        *,
        allowed_tools=None,
        permission_mode=None,
        setting_sources=None,
        cwd=None,
        resume=None,
        env=None,
        stderr=None,
        extra_args=None,
    ):
        self.kwargs = {
            "allowed_tools": allowed_tools,
            "permission_mode": permission_mode,
            "setting_sources": setting_sources,
            "cwd": cwd,
            "resume": resume,
            "env": env,
            "stderr": stderr,
            "extra_args": extra_args,
        }


class LegacyOptions:
    def __init__(self, *, auth_token=None, cwd=None, allowed_tools=None, resume=None):
        self.kwargs = {
            "auth_token": auth_token,
            "cwd": cwd,
            "allowed_tools": allowed_tools,
            "resume": resume,
        }


def _runner() -> AgentRunner:
    return AgentRunner(cwd="/app", token_provider=lambda: "unused")


def _parse_sse_payload(frame: str) -> dict:
    assert frame.startswith("data: ")
    assert frame.endswith("\n\n")
    return json.loads(frame[len("data: ") : -2])


def test_build_options_modern_sdk_uses_env_auth_for_oat_token():
    runner = _runner()
    token = "sk-ant-oat01-example-token"

    options = runner._build_options(
        options_cls=ModernOptions, token=token, resume_id="resume-1"
    )

    assert options.kwargs["allowed_tools"] == list(runner.allowed_tools)
    assert options.kwargs["resume"] == "resume-1"
    assert options.kwargs["env"]["CLAUDE_SETUP_TOKEN"] == token
    assert options.kwargs["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == token
    assert options.kwargs["env"]["ANTHROPIC_AUTH_TOKEN"] == token


def test_build_options_legacy_sdk_uses_auth_token_field():
    runner = _runner()
    token = "sk-ant-oat01-example-token"

    options = runner._build_options(
        options_cls=LegacyOptions, token=token, resume_id="resume-2"
    )

    assert options.kwargs["auth_token"] == token
    assert options.kwargs["cwd"] == "/app"
    assert options.kwargs["resume"] == "resume-2"


def test_build_auth_env_maps_api_key_prefix():
    runner = _runner()
    token = "sk-ant-api03-example-token"

    env = runner._build_auth_env(token)

    assert env["CLAUDE_SETUP_TOKEN"] == token
    assert env["ANTHROPIC_API_KEY"] == token
    assert env["CLAUDE_API_KEY"] == token
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in env


def test_build_options_includes_stderr_and_debug_flag_when_supported():
    runner = _runner()
    token = "sk-ant-oat01-example-token"
    callback = lambda line: None

    options = runner._build_options(
        options_cls=ModernOptionsWithStderr,
        token=token,
        resume_id=None,
        stderr_callback=callback,
    )

    assert options.kwargs["stderr"] is callback
    assert options.kwargs["extra_args"] == {"debug-to-stderr": None}


def test_parse_message_maps_is_error_result_to_error_event():
    runner = _runner()
    event = runner._parse_message(
        {"type": "result", "result": "Auth failed", "is_error": True}
    )
    assert event is not None
    assert event["type"] == "error"
    assert event["content"] == "Auth failed"


def test_run_agent_prefers_streamed_error_over_generic_process_error():
    runner = AgentRunner(
        cwd="/app", token_provider=lambda: "sk-ant-oat01-example-token"
    )
    session = runner.create_session()
    session_id = session["id"]

    class DummyOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    async def fake_query(*, prompt, options):
        del prompt, options
        yield {"type": "result", "result": "Authentication failed", "is_error": True}
        raise RuntimeError(
            "Command failed with exit code 1 (exit code: 1)\n"
            "Error output: Check stderr output for details"
        )

    runner._load_sdk = lambda: {"query": fake_query, "options_cls": DummyOptions}
    runner._run_agent(session_id, "test")

    events = []
    q = runner._output_queues[session_id]
    while not q.empty():
        events.append(q.get())

    error_events = [event for event in events if event.get("type") == "error"]
    assert len(error_events) == 1
    assert error_events[0]["content"] == "Authentication failed"
    assert "Check stderr output for details" not in error_events[0]["content"]

    session_state = runner.get_session(session_id)
    assert session_state is not None
    assert session_state["status"] == "error"
    assert session_state["last_error"] == "Authentication failed"


def test_frame_sse_helpers_for_ping_error_and_done_events():
    ping = _parse_sse_payload(_frame_sse_ping_event("2026-02-25T10:00:00Z"))
    error = _parse_sse_payload(
        _frame_sse_error_event(
            content="stream failed",
            timestamp="2026-02-25T10:00:01Z",
        )
    )
    done = _parse_sse_payload(_frame_sse_done_event("2026-02-25T10:00:02Z"))

    assert ping == {"type": "ping", "timestamp": "2026-02-25T10:00:00Z"}
    assert error == {
        "type": "error",
        "content": "stream failed",
        "timestamp": "2026-02-25T10:00:01Z",
    }
    assert done == {"type": "done", "timestamp": "2026-02-25T10:00:02Z"}


def test_get_stream_frames_terminal_error_and_done_events():
    runner = _runner()

    error_session = runner.create_session()
    error_id = error_session["id"]
    runner._output_queues[error_id].put(
        {"type": "error", "content": "boom", "timestamp": "2026-02-25T11:00:00Z"}
    )
    error_frames = list(runner.get_stream(error_id, keepalive_seconds=1))
    assert len(error_frames) == 1
    assert _parse_sse_payload(error_frames[0]) == {
        "type": "error",
        "content": "boom",
        "timestamp": "2026-02-25T11:00:00Z",
    }

    done_session = runner.create_session()
    done_id = done_session["id"]
    runner._output_queues[done_id].put(
        {"type": "done", "timestamp": "2026-02-25T11:00:01Z"}
    )
    done_frames = list(runner.get_stream(done_id, keepalive_seconds=1))
    assert len(done_frames) == 1
    assert _parse_sse_payload(done_frames[0]) == {
        "type": "done",
        "timestamp": "2026-02-25T11:00:01Z",
    }
