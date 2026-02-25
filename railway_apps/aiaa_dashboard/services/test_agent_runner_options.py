#!/usr/bin/env python3
"""Unit tests for AgentRunner SDK option compatibility helpers."""

from __future__ import annotations

import asyncio
import itertools
import json

import pytest

import services.agent_runner as agent_runner_module
from services.agent_runner import (
    AgentRunner,
    RunnerError,
    _frame_sse_done_event,
    _frame_sse_error_event,
    _frame_sse_ping_event,
    _redact_token_like_text,
)
from services.chat_store import InMemoryChatStore


class RecordingStore:
    def __init__(self):
        self.events = []
        self.messages = []
        self.updates = []

    def append_event(self, session_id, event):
        self.events.append((session_id, dict(event)))

    def append_message(self, session_id, message):
        self.messages.append((session_id, dict(message)))

    def update_session(self, session_id, updates):
        self.updates.append((session_id, dict(updates)))


class MessageObject:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


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


class ModernOptionsWithWorkspace:
    def __init__(
        self,
        *,
        allowed_tools=None,
        permission_mode=None,
        setting_sources=None,
        workspace=None,
        cwd=None,
        resume=None,
        env=None,
    ):
        self.kwargs = {
            "allowed_tools": allowed_tools,
            "permission_mode": permission_mode,
            "setting_sources": setting_sources,
            "workspace": workspace,
            "cwd": cwd,
            "resume": resume,
            "env": env,
        }


class ModernOptionsWithRuntimeLauncher:
    def __init__(
        self,
        *,
        allowed_tools=None,
        permission_mode=None,
        setting_sources=None,
        cwd=None,
        resume=None,
        env=None,
        runtime_launcher=None,
    ):
        self.kwargs = {
            "allowed_tools": allowed_tools,
            "permission_mode": permission_mode,
            "setting_sources": setting_sources,
            "cwd": cwd,
            "resume": resume,
            "env": env,
            "runtime_launcher": runtime_launcher,
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

def _drain_queue(runner: AgentRunner, session_id: str):
    events = []
    q = runner._output_queues[session_id]
    while not q.empty():
        events.append(q.get())
    return events


def test_runner_defaults_cwd_to_app_when_missing():
    runner = AgentRunner(cwd=None, token_provider=lambda: "unused")
    assert runner.cwd == "/app"


def test_runner_rejects_non_allowlisted_cwd():
    runner = AgentRunner(
        cwd="/tmp/not-allowed",
        token_provider=lambda: "unused",
        cwd_allowlist=["/app"],
    )
    assert runner.cwd == "/app"


def test_runner_accepts_allowlisted_cwd():
    runner = AgentRunner(
        cwd="/workspace/demo",
        token_provider=lambda: "unused",
        cwd_allowlist=["/workspace"],
    )
    assert runner.cwd == "/workspace/demo"


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

def test_build_options_sets_workspace_when_sdk_supports_it():
    runner = _runner()

    options = runner._build_options(
        options_cls=ModernOptionsWithWorkspace,
        token="sk-ant-oat01-example-token",
        resume_id="resume-3",
    )

    assert options.kwargs["workspace"] == "/app"
    assert options.kwargs["cwd"] == "/app"
    assert options.kwargs["resume"] == "resume-3"


def test_build_options_includes_runtime_launcher_when_supported():
    runner = _runner()
    token = "sk-ant-oat01-example-token"

    options = runner._build_options(
        options_cls=ModernOptionsWithRuntimeLauncher,
        token=token,
        resume_id=None,
    )

    assert callable(options.kwargs["runtime_launcher"])


def test_runtime_launcher_executes_claude_with_setup_token_env(monkeypatch):
    runner = _runner()
    token = "sk-ant-oat01-example-token"
    launcher = runner._build_runtime_launcher(token)
    captured = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

        class _DummyProcess:
            pass

        return _DummyProcess()

    monkeypatch.setattr(
        agent_runner_module.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    asyncio.run(launcher("--print", "json", env={"CUSTOM": "1"}))

    assert captured["args"] == ("claude", "--print", "json")
    assert captured["kwargs"]["env"]["CUSTOM"] == "1"
    assert captured["kwargs"]["env"]["CLAUDE_SETUP_TOKEN"] == token
    assert captured["kwargs"]["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == token
    assert captured["kwargs"]["env"]["ANTHROPIC_AUTH_TOKEN"] == token


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


def test_persist_event_normalizes_gateway_event_types():
    store = InMemoryChatStore()
    runner = AgentRunner(
        cwd="/app", token_provider=lambda: "unused", session_store=store
    )
    session_id = "persist-normalized"

    runner._persist_event(
        session_id, {"type": "tool_use", "tool": "Read", "input": "foo.py"}
    )
    runner._persist_event(session_id, {"type": "tool_result", "content": "ok"})
    runner._persist_event(session_id, {"type": "text", "content": "chunk"})
    runner._persist_event(session_id, {"type": "result", "content": "final"})
    runner._persist_event(session_id, {"type": "error", "content": "boom"})
    runner._persist_event(session_id, {"type": "done"})

    events = store.get_events(session_id)
    assert [event["type"] for event in events] == [
        "tool_use",
        "tool_result",
        "text",
        "result",
        "error",
        "done",
    ]


def test_persist_event_skips_unknown_types():
    store = InMemoryChatStore()
    runner = AgentRunner(
        cwd="/app", token_provider=lambda: "unused", session_store=store
    )
    session_id = "persist-unknown"

    runner._persist_event(session_id, {"type": "unsupported", "content": "noop"})
    assert store.get_events(session_id) == []


def test_redact_token_like_text_masks_common_gateway_patterns():
    raw_bearer = "Bearer sk-ant-api03-super-secret-token-1234567890"
    raw_prefix = "github_pat_1234567890abcdefghijklmno"
    raw_kv = "token=pplx-super-secret-token-1234567890"
    raw_jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ."
        "signedpayload1234567890"
    )
    sample = f"{raw_bearer} {raw_prefix} {raw_kv} {raw_jwt}"

    redacted = _redact_token_like_text(sample)

    assert raw_bearer not in redacted
    assert raw_prefix not in redacted
    assert raw_kv not in redacted
    assert raw_jwt not in redacted
    assert "Bearer " in redacted
    assert "token=" in redacted


def test_parse_message_redacts_token_like_result_content():
    runner = _runner()
    raw = "Authorization: Bearer sk-or-secret-token-1234567890"

    event = runner._parse_message({"type": "result", "result": raw, "is_error": True})

    assert event is not None
    assert event["type"] == "error"
    assert raw not in event["content"]
    assert "Bearer " in event["content"]


def test_run_agent_redacts_token_like_values_from_runtime_errors():
    runner = AgentRunner(cwd="/app", token_provider=lambda: "sk-ant-oat01-example-token")
    session = runner.create_session()
    session_id = session["id"]
    leaked_stderr = "Authorization: Bearer sk-ant-api03-super-secret-token-123456"
    leaked_error = "gateway failed: api_key=sk-or-secret-token-1234567890"

    class DummyOptions:
        def __init__(self, *, stderr=None, **kwargs):
            self.kwargs = {"stderr": stderr}
            self.kwargs.update(kwargs)

    async def fake_query(*, prompt, options):
        del prompt
        stderr_callback = options.kwargs.get("stderr")
        if callable(stderr_callback):
            stderr_callback(leaked_stderr)
        if False:  # pragma: no cover - keeps async-generator shape
            yield {}
        raise RuntimeError(leaked_error)

    runner._load_sdk = lambda: {"query": fake_query, "options_cls": DummyOptions}
    runner._run_agent(session_id, "test")

    events = _drain_queue(runner, session_id)
    error_events = [event for event in events if event.get("type") == "error"]
    assert len(error_events) == 1
    assert leaked_stderr not in error_events[0]["content"]
    assert leaked_error not in error_events[0]["content"]
    assert "Bearer " in error_events[0]["content"]

    session_state = runner.get_session(session_id)
    assert session_state is not None
    assert leaked_stderr not in session_state["last_error"]
    assert leaked_error not in session_state["last_error"]


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

    events = _drain_queue(runner, session_id)
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

    events = _drain_queue(runner, session_id)
    error_event = next(event for event in events if event.get("type") == "error")
    assert error_event["metrics"] == {
        "queue_wait_ms": 250,
        "first_event_latency_ms": None,
        "total_runtime_ms": 750,
    }


def test_run_agent_streams_success_sequence_from_mocked_sdk_payloads():
    store = RecordingStore()
    runner = AgentRunner(
        cwd="/app",
        token_provider=lambda: "sk-ant-api03-example-token",
        session_store=store,
    )
    session_id = runner.create_session()["id"]

    class DummyOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    async def fake_query(*, prompt, options):
        del prompt, options
        yield MessageObject(
            session_id="sdk-session-123",
            tool_name="Read",
            tool_input={"file_path": "README.md"},
        )
        yield {"tool_result": {"lines": 3}}
        yield {"type": "assistant_message", "content": [{"text": "Working"}]}
        yield {"type": "result", "result": {"status": "ok"}}

    runner._load_sdk = lambda: {"query": fake_query, "options_cls": DummyOptions}
    runner._run_agent(session_id, "test")

    events = _drain_queue(runner, session_id)
    assert [event.get("type") for event in events] == [
        "tool_use",
        "tool_result",
        "text",
        "result",
        "done",
    ]
    assert events[0]["input"] == "Reading README.md"
    assert events[1]["content"] == '{"lines": 3}'
    assert events[2]["content"] == "Working"
    assert events[3]["content"] == '{"status": "ok"}'

    session_state = runner.get_session(session_id)
    assert session_state is not None
    assert session_state["status"] == "idle"
    assert session_state["last_error"] is None
    assert session_state["sdk_session_id"] == "sdk-session-123"
    assert session_state["messages"][-1]["content"] == 'Working\n{"status": "ok"}'

    assert [event["type"] for _, event in store.events] == [
        "tool_use",
        "tool_result",
        "text",
        "result",
    ]
    assert [event["payload"]["kind"] for _, event in store.events] == [
        "tool_use",
        "tool_result",
        "text",
        "result",
    ]


def test_run_agent_uses_cli_stream_error_payload_once():
    runner = AgentRunner(cwd="/app", token_provider=lambda: "sk-ant-oat01-example-token")
    session_id = runner.create_session()["id"]

    class DummyOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    async def fake_query(*, prompt, options):
        del prompt, options
        yield {"type": "error", "message": "CLI auth failed"}
        raise RuntimeError(
            "Command failed with exit code 1 (exit code: 1)\n"
            "Error output: Check stderr output for details"
        )

    runner._load_sdk = lambda: {"query": fake_query, "options_cls": DummyOptions}
    runner._run_agent(session_id, "test")

    events = _drain_queue(runner, session_id)
    assert [event.get("type") for event in events] == ["error"]
    assert events[0]["content"] == "CLI auth failed"

    session_state = runner.get_session(session_id)
    assert session_state is not None
    assert session_state["status"] == "error"
    assert session_state["last_error"] == "CLI auth failed"


def test_ensure_session_updates_title_without_overwriting_sdk_session_id():
    runner = _runner()

    created = runner.ensure_session(
        "session-flow-1",
        title="Initial Title",
        sdk_session_id="sdk-initial",
    )
    updated = runner.ensure_session(
        "session-flow-1",
        title="Renamed Title",
        sdk_session_id="sdk-new",
    )

    assert created["id"] == "session-flow-1"
    assert created["sdk_session_id"] == "sdk-initial"
    assert updated["title"] == "Renamed Title"
    assert updated["sdk_session_id"] == "sdk-initial"


def test_capture_sdk_session_id_persists_only_once():
    updates: list[tuple[str, dict[str, object]]] = []

    class SessionStoreSpy:
        def update_session(self, session_id, payload):
            updates.append((session_id, dict(payload)))

    runner = AgentRunner(
        cwd="/app",
        token_provider=lambda: "unused",
        session_store=SessionStoreSpy(),
    )
    runner.ensure_session("session-flow-2")

    runner._capture_sdk_session_id(
        "session-flow-2",
        raw_message=object(),
        payload={"session_id": "sdk-first"},
    )
    runner._capture_sdk_session_id(
        "session-flow-2",
        raw_message=object(),
        payload={"session_id": "sdk-second"},
    )

    session_state = runner.get_session("session-flow-2")
    assert session_state is not None
    assert session_state["sdk_session_id"] == "sdk-first"
    assert updates[0][0] == "session-flow-2"
    assert updates[0][1]["sdk_session_id"] == "sdk-first"
    assert len(updates) == 1


def test_send_message_transitions_session_to_running_before_thread_starts(monkeypatch):
    updates: list[tuple[str, dict[str, object]]] = []
    started: list[tuple[str, str]] = []

    class SessionStoreSpy:
        def update_session(self, session_id, payload):
            updates.append((session_id, dict(payload)))

    class DummyThread:
        def __init__(self, *, target, args=(), daemon=False):
            self._target = target
            self._args = args
            self.daemon = daemon

        def start(self):
            started.append((self._args[0], self._args[1]))

    runner = AgentRunner(
        cwd="/app",
        token_provider=lambda: "unused",
        session_store=SessionStoreSpy(),
    )
    runner.ensure_session("session-flow-3")

    monkeypatch.setattr("services.agent_runner.threading.Thread", DummyThread)

    runner.send_message("session-flow-3", "hello")

    session_state = runner.get_session("session-flow-3")
    assert session_state is not None
    assert session_state["status"] == "running"
    assert started == [("session-flow-3", "hello")]
    assert updates[0][0] == "session-flow-3"
    assert updates[0][1]["status"] == "running"

    with pytest.raises(RunnerError, match="already running"):
        runner.send_message("session-flow-3", "second")


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
