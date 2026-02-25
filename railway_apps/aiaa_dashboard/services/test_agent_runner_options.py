#!/usr/bin/env python3
"""Unit tests for AgentRunner SDK option compatibility helpers."""

from __future__ import annotations

import itertools

from services.agent_runner import AgentRunner


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
    event = runner._parse_message({"type": "result", "result": "Auth failed", "is_error": True})
    assert event is not None
    assert event["type"] == "error"
    assert event["content"] == "Auth failed"


def test_run_agent_prefers_streamed_error_over_generic_process_error():
    runner = AgentRunner(cwd="/app", token_provider=lambda: "sk-ant-oat01-example-token")
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


def _set_perf_counter_values(monkeypatch, values):
    counter = itertools.chain(values)
    monkeypatch.setattr(
        "services.agent_runner.time.perf_counter",
        lambda: next(counter),
    )


def test_run_agent_emits_timing_metrics_for_success(monkeypatch):
    runner = AgentRunner(cwd="/app", token_provider=lambda: "sk-ant-oat01-example-token")
    session = runner.create_session()
    session_id = session["id"]

    with runner._lock:
        runner._sessions[session_id]["status"] = "running"
        runner._run_timing[session_id] = {
            "enqueued_at": 10.0,
            "started_at": None,
            "first_event_recorded": False,
        }

    _set_perf_counter_values(monkeypatch, [10.25, 10.75, 13.25])

    class DummyOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    async def fake_query(*, prompt, options):
        del prompt, options
        yield {"type": "assistant", "content": "Hello"}

    runner._load_sdk = lambda: {"query": fake_query, "options_cls": DummyOptions}
    runner._run_agent(session_id, "test")

    session_state = runner.get_session(session_id)
    assert session_state is not None
    assert session_state["queue_wait_ms"] == 250
    assert session_state["first_event_latency_ms"] == 750
    assert session_state["total_runtime_ms"] == 3000
    assert session_state["status"] == "idle"

    events = []
    q = runner._output_queues[session_id]
    while not q.empty():
        events.append(q.get())
    done = next(event for event in events if event.get("type") == "done")
    assert done["metrics"] == {
        "queue_wait_ms": 250,
        "first_event_latency_ms": 750,
        "total_runtime_ms": 3000,
    }


def test_run_agent_emits_timing_metrics_for_error_without_events(monkeypatch):
    runner = AgentRunner(cwd="/app", token_provider=lambda: "sk-ant-oat01-example-token")
    session = runner.create_session()
    session_id = session["id"]

    with runner._lock:
        runner._sessions[session_id]["status"] = "running"
        runner._run_timing[session_id] = {
            "enqueued_at": 5.0,
            "started_at": None,
            "first_event_recorded": False,
        }

    _set_perf_counter_values(monkeypatch, [5.25, 6.0])

    class DummyOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    async def fake_query(*, prompt, options):
        del prompt, options
        raise RuntimeError("boom")
        yield  # pragma: no cover

    runner._load_sdk = lambda: {"query": fake_query, "options_cls": DummyOptions}
    runner._run_agent(session_id, "test")

    session_state = runner.get_session(session_id)
    assert session_state is not None
    assert session_state["status"] == "error"
    assert session_state["queue_wait_ms"] == 250
    assert session_state["first_event_latency_ms"] is None
    assert session_state["total_runtime_ms"] == 750

    events = []
    q = runner._output_queues[session_id]
    while not q.empty():
        events.append(q.get())
    error_event = next(event for event in events if event.get("type") == "error")
    assert error_event["metrics"] == {
        "queue_wait_ms": 250,
        "first_event_latency_ms": None,
        "total_runtime_ms": 750,
    }
