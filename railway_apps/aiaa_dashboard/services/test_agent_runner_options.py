#!/usr/bin/env python3
"""Unit tests for AgentRunner SDK option compatibility helpers."""

from __future__ import annotations

from services.agent_runner import AgentRunner


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
        "tool",
        "tool",
        "result",
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
