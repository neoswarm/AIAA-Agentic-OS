#!/usr/bin/env python3
"""Chat route tests for store-backed session/message state."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from typing import Any

import pytest

# Test env must be configured before importing Flask app modules.
os.environ["FLASK_ENV"] = "testing"
os.environ["DASHBOARD_USERNAME"] = "testadmin"
os.environ["DASHBOARD_PASSWORD_HASH"] = hashlib.sha256(b"testpass123").hexdigest()
os.environ["FLASK_SECRET_KEY"] = hashlib.sha256(b"chat-test-secret").hexdigest()
_TEST_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DB_PATH"] = _TEST_DB.name

from app import create_app
import database
import routes.chat as chat_routes


class FakeStore:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}
        self.messages: dict[str, list[dict[str, Any]]] = {}
        self.calls: list[tuple[str, Any]] = []

    def create_session(
        self,
        session_id: str,
        *,
        title: str = "New Chat",
        status: str = "idle",
        sdk_session_id: str | None = None,
    ) -> dict[str, Any]:
        session = {
            "id": session_id,
            "title": title,
            "status": status,
            "sdk_session_id": sdk_session_id,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        self.sessions[session_id] = dict(session)
        self.messages.setdefault(session_id, [])
        self.calls.append(("create_session", session_id))
        return dict(session)

    def list_sessions(self, limit: int | None = None) -> list[dict[str, Any]]:
        self.calls.append(("list_sessions", limit))
        rows = [dict(item) for item in self.sessions.values()]
        return rows if limit is None else rows[:limit]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        self.calls.append(("get_session", session_id))
        session = self.sessions.get(session_id)
        return dict(session) if session is not None else None

    def update_session(
        self, session_id: str, updates: dict[str, Any]
    ) -> dict[str, Any] | None:
        self.calls.append(("update_session", session_id))
        session = self.sessions.get(session_id)
        if session is None:
            return None
        session.update(dict(updates))
        return dict(session)

    def append_message(
        self,
        session_id: str,
        message: dict[str, Any],
        session_updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(("append_message", session_id))
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        if session_updates:
            session.update(dict(session_updates))
        record = dict(message)
        self.messages.setdefault(session_id, []).append(record)
        return record

    def get_messages(
        self, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append(("get_messages", session_id))
        rows = [dict(item) for item in self.messages.get(session_id, [])]
        return rows if limit is None else rows[:limit]

    def append_event(
        self,
        session_id: str,
        event: dict[str, Any],
        session_updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(("append_event", session_id))
        if session_updates:
            session = self.sessions.get(session_id)
            if session is not None:
                session.update(dict(session_updates))
        return dict(event)

    def get_events(
        self, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append(("get_events", session_id))
        return []


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self._active: set[str] = set()

    def ensure_session(
        self,
        session_id: str,
        *,
        title: str | None = None,
        sdk_session_id: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(("ensure_session", session_id))
        self._active.add(session_id)
        return {"id": session_id, "title": title, "sdk_session_id": sdk_session_id}

    def has_session(self, session_id: str) -> bool:
        self.calls.append(("has_session", session_id))
        return session_id in self._active

    def send_message(self, session_id: str, user_message: str) -> None:
        self.calls.append(("send_message", session_id, user_message))

    def get_stream(self, session_id: str):
        self.calls.append(("get_stream", session_id))
        yield 'data: {"type":"done"}\n\n'


class FactoryRunner(FakeRunner):
    def __init__(self) -> None:
        super().__init__()
        self.cwd = "/initial"
        self.attached_stores: list[FakeStore] = []

    def attach_store(self, session_store) -> None:
        self.attached_stores.append(session_store)


class FakeGatewayRunner(FakeRunner):
    def __init__(self) -> None:
        super().__init__()
        self.stream_chunks: dict[str, list[str]] = {}

    def send_message(self, session_id: str, user_message: str) -> None:
        super().send_message(session_id, user_message)
        self.stream_chunks[session_id] = [
            'data: {"type":"text","content":"Gateway says hi"}\n\n',
            'data: {"type":"done","timestamp":"2026-02-27T00:00:00Z"}\n\n',
        ]

    def get_stream(self, session_id: str):
        self.calls.append(("get_stream", session_id))
        for chunk in self.stream_chunks.get(session_id, []):
            yield chunk


@pytest.fixture(scope="module")
def app():
    application = create_app()
    application.config["TESTING"] = True
    with application.app_context():
        database.init_db(application)
    yield application
    try:
        os.unlink(_TEST_DB.name)
    except OSError:
        pass


@pytest.fixture()
def auth_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testadmin"
    return client


@pytest.fixture(autouse=True)
def reset_rate_limits():
    chat_routes._reset_message_rate_limits()
    yield
    chat_routes._reset_message_rate_limits()


def test_list_sessions_reads_from_store(auth_client, monkeypatch):
    store = FakeStore()
    store.create_session("s-1", title="Stored session")

    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(
        chat_routes,
        "_get_runner",
        lambda: (_ for _ in ()).throw(AssertionError("runner should not be used")),
    )

    resp = auth_client.get("/api/chat/sessions")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["sessions"][0]["id"] == "s-1"
    assert ("list_sessions", None) in store.calls


def test_get_session_reads_store_messages(auth_client, monkeypatch):
    store = FakeStore()
    store.create_session("s-2", title="History")
    store.append_message(
        "s-2",
        {"role": "user", "content": "hello", "type": "message", "metadata": {}},
        None,
    )

    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)

    resp = auth_client.get("/api/chat/sessions/s-2")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["session"]["id"] == "s-2"
    assert body["session"]["messages"][0]["content"] == "hello"
    assert ("get_session", "s-2") in store.calls
    assert ("get_messages", "s-2") in store.calls


def test_create_session_uses_store_and_runner(auth_client, monkeypatch):
    store = FakeStore()
    runner = FakeRunner()

    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "_get_runner", lambda: runner)
    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "eyJ.valid.token")
    monkeypatch.setattr(chat_routes.secrets, "token_hex", lambda _: "session-new")

    resp = auth_client.post("/api/chat/sessions", json={"title": "New Session"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["session_id"] == "session-new"
    assert body["session"]["title"] == "New Session"
    assert ("create_session", "session-new") in store.calls
    assert ("ensure_session", "session-new") in runner.calls


def test_send_message_uses_store_state_then_runner(auth_client, monkeypatch):
    store = FakeStore()
    store.create_session("s-3", title="New chat")
    runner = FakeRunner()

    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "_get_runner", lambda: runner)
    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "eyJ.valid.token")

    resp = auth_client.post(
        "/api/chat/message",
        json={"session_id": "s-3", "message": "hello from user"},
    )
    assert resp.status_code == 202
    assert resp.get_json()["status"] == "ok"

    assert store.messages["s-3"][0]["content"] == "hello from user"
    assert ("append_message", "s-3") in store.calls
    assert ("ensure_session", "s-3") in runner.calls
    assert ("send_message", "s-3", "hello from user") in runner.calls


@pytest.mark.parametrize(
    ("gateway_mode_enabled", "chat_backend"),
    [
        (True, "sdk"),
        (False, "gateway"),
    ],
)
def test_send_message_gateway_mode_uses_gateway_runner(
    auth_client,
    monkeypatch,
    gateway_mode_enabled,
    chat_backend,
):
    store = FakeStore()
    store.create_session("s-gateway", title="Gateway chat")
    sdk_runner = FakeRunner()

    class GatewayRunner(FakeRunner):
        pass

    gateway_runner = GatewayRunner()
    factory_calls: list[dict[str, Any]] = []

    def fake_build_chat_runner(*, cwd, token_provider, session_store, backend):
        factory_calls.append(
            {
                "cwd": cwd,
                "token_provider": token_provider,
                "session_store": session_store,
                "backend": backend,
            }
        )
        return gateway_runner

    monkeypatch.setattr(chat_routes, "_runner", sdk_runner)
    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "eyJ.valid.token")
    monkeypatch.setattr(
        chat_routes,
        "_is_gateway_mode_enabled",
        lambda: gateway_mode_enabled,
    )
    monkeypatch.setattr(chat_routes, "_chat_backend", lambda: chat_backend)
    monkeypatch.setattr(chat_routes, "build_chat_runner", fake_build_chat_runner)

    resp = auth_client.post(
        "/api/chat/message",
        json={"session_id": "s-gateway", "message": "route me through gateway"},
    )

    assert resp.status_code == 202
    assert resp.get_json()["status"] == "ok"
    assert factory_calls
    assert factory_calls[0]["backend"] == "gateway"
    assert factory_calls[0]["session_store"] is store
    assert (
        "send_message",
        "s-gateway",
        "route me through gateway",
    ) not in sdk_runner.calls
    assert (
        "send_message",
        "s-gateway",
        "route me through gateway",
    ) in gateway_runner.calls
    assert chat_routes._runner is gateway_runner


def test_send_message_rate_limited_per_user(auth_client, app, monkeypatch):
    store = FakeStore()
    store.create_session("s-limit", title="Rate limit")
    runner = FakeRunner()

    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "_get_runner", lambda: runner)
    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "eyJ.valid.token")

    monotonic_values = iter([100.0, 101.0, 102.0])
    monkeypatch.setattr(chat_routes.time, "monotonic", lambda: next(monotonic_values))

    app.config["CHAT_MESSAGE_RATE_LIMIT_PER_MINUTE"] = 2
    app.config["CHAT_MESSAGE_RATE_LIMIT_WINDOW_SECONDS"] = 60

    first = auth_client.post(
        "/api/chat/message",
        json={"session_id": "s-limit", "message": "first"},
    )
    second = auth_client.post(
        "/api/chat/message",
        json={"session_id": "s-limit", "message": "second"},
    )
    third = auth_client.post(
        "/api/chat/message",
        json={"session_id": "s-limit", "message": "third"},
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert third.status_code == 429
    body = third.get_json()
    assert body["error_code"] == "rate_limited"
    assert body["retry_after_seconds"] >= 1
    assert third.headers["Retry-After"] == str(body["retry_after_seconds"])
    assert runner.calls.count(("send_message", "s-limit", "first")) == 1
    assert runner.calls.count(("send_message", "s-limit", "second")) == 1
    assert runner.calls.count(("send_message", "s-limit", "third")) == 0


def test_send_message_rate_limit_isolated_per_user(app, monkeypatch):
    store = FakeStore()
    store.create_session("s-isolated", title="Rate limit users")
    runner = FakeRunner()

    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "_get_runner", lambda: runner)
    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "eyJ.valid.token")

    monotonic_values = iter([200.0, 201.0, 202.0])
    monkeypatch.setattr(chat_routes.time, "monotonic", lambda: next(monotonic_values))

    app.config["CHAT_MESSAGE_RATE_LIMIT_PER_MINUTE"] = 1
    app.config["CHAT_MESSAGE_RATE_LIMIT_WINDOW_SECONDS"] = 60

    user_one = app.test_client()
    with user_one.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "user-one"

    user_two = app.test_client()
    with user_two.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "user-two"

    one_first = user_one.post(
        "/api/chat/message",
        json={"session_id": "s-isolated", "message": "hello one"},
    )
    two_first = user_two.post(
        "/api/chat/message",
        json={"session_id": "s-isolated", "message": "hello two"},
    )
    one_second = user_one.post(
        "/api/chat/message",
        json={"session_id": "s-isolated", "message": "hello one again"},
    )

    assert one_first.status_code == 202
    assert two_first.status_code == 202
    assert one_second.status_code == 429


def test_stream_uses_store_for_session_lookup(auth_client, monkeypatch):
    store = FakeStore()
    store.create_session("s-4", title="Streamable")
    runner = FakeRunner()

    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "_get_runner", lambda: runner)

    resp = auth_client.get("/api/chat/stream/s-4")
    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"
    assert b'"type":"done"' in resp.data
    assert ("get_session", "s-4") in store.calls
    assert ("ensure_session", "s-4") in runner.calls


def test_gateway_mock_message_stream_done_lifecycle(auth_client, monkeypatch):
    store = FakeStore()
    store.create_session("s-gateway", title="Gateway lifecycle")
    runner = FakeGatewayRunner()

    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "_get_runner", lambda: runner)
    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "eyJ.valid.token")

    send_resp = auth_client.post(
        "/api/chat/message",
        json={"session_id": "s-gateway", "message": "hello gateway"},
    )
    assert send_resp.status_code == 202

    stream_resp = auth_client.get("/api/chat/stream/s-gateway")
    assert stream_resp.status_code == 200
    assert stream_resp.mimetype == "text/event-stream"

    events: list[dict[str, Any]] = []
    for line in stream_resp.get_data(as_text=True).splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    assert [event["type"] for event in events] == ["text", "done"]
    assert events[0]["content"] == "Gateway says hi"
    assert ("send_message", "s-gateway", "hello gateway") in runner.calls
    assert ("get_stream", "s-gateway") in runner.calls
    assert runner.calls.count(("ensure_session", "s-gateway")) == 1


def test_stream_exposes_tool_events_in_sse(auth_client, monkeypatch):
    store = FakeStore()
    store.create_session("s-tools", title="Tool stream")
    runner = FakeRunner()

    def fake_stream(session_id: str):
        runner.calls.append(("get_stream", session_id))
        yield 'data: {"type":"tool_use","tool":"Read","input":"README.md"}\n\n'
        yield 'data: {"type":"tool_result","content":"Read complete"}\n\n'
        yield 'data: {"type":"done"}\n\n'

    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "_get_runner", lambda: runner)
    monkeypatch.setattr(runner, "get_stream", fake_stream)

    resp = auth_client.get("/api/chat/stream/s-tools")
    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"

    body = resp.get_data(as_text=True)
    assert '"type":"tool_use"' in body
    assert '"tool":"Read"' in body
    assert '"type":"tool_result"' in body
    assert '"content":"Read complete"' in body
    assert '"type":"done"' in body


def test_stream_translates_gateway_events_to_dashboard_model(auth_client, monkeypatch):
    store = FakeStore()
    store.create_session("s-gateway-translate", title="Gateway Stream")
    runner = FakeRunner()

    def fake_stream(session_id: str):
        runner.calls.append(("get_stream", session_id))
        yield (
            'data: {"type":"tool","payload":{"kind":"tool_use","tool":"Bash","input":"npm test"}}\n\n'
        )
        yield 'data: {"type":"response.output_text.delta","delta":"Hello"}\n\n'
        yield (
            'data: {"type":"response.output_item.added","item":{"type":"function_call_output","output":"All tests passed"}}\n\n'
        )
        yield 'data: {"type":"response.completed"}\n\n'

    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "_get_runner", lambda: runner)
    monkeypatch.setattr(runner, "get_stream", fake_stream)

    resp = auth_client.get("/api/chat/stream/s-gateway-translate")
    assert resp.status_code == 200

    payloads = []
    for line in resp.get_data(as_text=True).splitlines():
        if not line.startswith("data: "):
            continue
        payloads.append(json.loads(line[6:]))

    assert [item["type"] for item in payloads] == [
        "tool_use",
        "text",
        "tool_result",
        "done",
    ]
    assert payloads[0]["tool"] == "Bash"
    assert payloads[0]["input"] == "npm test"
    assert payloads[1]["content"] == "Hello"
    assert payloads[2]["content"] == "All tests passed"


def test_v1_responses_stream_requires_auth(app):
    client = app.test_client()
    resp = client.post("/v1/responses", json={"input": "hi", "stream": True})
    assert resp.status_code == 401
    assert resp.headers["WWW-Authenticate"] == "Bearer"


def test_v1_responses_stream_rejects_unauthorized_bearer_api_key(app, monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_KEY", "dashboard-key-123")
    client = app.test_client()

    resp = client.post(
        "/v1/responses",
        headers={"Authorization": "Bearer wrong-key"},
        json={"input": "hi", "stream": True},
    )

    assert resp.status_code == 401
    assert resp.headers["WWW-Authenticate"] == "Bearer"
    assert resp.get_json()["error"]["message"] == "Authentication required"


def test_v1_responses_stream_rejects_malformed_bearer_auth_header(app, monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_KEY", "dashboard-key-123")
    client = app.test_client()

    resp = client.post(
        "/v1/responses",
        headers={"Authorization": "Bearer"},
        json={"input": "hi", "stream": True},
    )

    assert resp.status_code == 401
    assert resp.headers["WWW-Authenticate"] == "Bearer"
    assert resp.get_json()["error"]["message"] == "Authentication required"


def test_v1_responses_stream_returns_sse_events(auth_client, monkeypatch):
    store = FakeStore()
    runner = FakeRunner()

    def fake_stream(session_id: str):
        runner.calls.append(("get_stream", session_id))
        yield 'data: {"type":"text","content":"Hello"}\n\n'
        yield 'data: {"type":"done"}\n\n'

    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "_get_runner", lambda: runner)
    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "sk-ant-test-token")
    monkeypatch.setattr(runner, "get_stream", fake_stream)

    token_values = iter(["session-v1-1", "response-v1-1"])
    monkeypatch.setattr(chat_routes.secrets, "token_hex", lambda _: next(token_values))

    resp = auth_client.post(
        "/v1/responses",
        json={"model": "claude-3-7-sonnet", "input": "Say hello", "stream": True},
    )
    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"

    payloads = []
    for line in resp.get_data(as_text=True).splitlines():
        if not line.startswith("data: "):
            continue
        chunk = line[6:]
        if chunk == "[DONE]":
            payloads.append(chunk)
            continue
        payloads.append(json.loads(chunk))

    assert payloads[-1] == "[DONE]"
    typed_events = [event for event in payloads if isinstance(event, dict)]
    assert typed_events[0]["type"] == "response.created"
    assert typed_events[-1]["type"] == "response.completed"
    assert any(
        event.get("type") == "response.output_text.delta"
        and event.get("delta") == "Hello"
        for event in typed_events
    )
    assert ("create_session", "session-v1-1") in store.calls
    assert ("send_message", "session-v1-1", "Say hello") in runner.calls


def test_v1_responses_stream_accepts_bearer_api_key(app, monkeypatch):
    store = FakeStore()
    runner = FakeRunner()
    monkeypatch.setenv("DASHBOARD_API_KEY", "dashboard-key-123")

    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "_get_runner", lambda: runner)
    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "sk-ant-test-token")

    client = app.test_client()
    resp = client.post(
        "/v1/responses",
        headers={"Authorization": "Bearer dashboard-key-123"},
        json={"input": "hi", "stream": True},
    )
    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"


def test_v1_responses_stream_proxies_gateway_mode_when_enabled(
    auth_client, app, monkeypatch
):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "true")
    monkeypatch.setitem(app.config, "GATEWAY_BASE_URL", "https://gateway.example")
    monkeypatch.setitem(app.config, "GATEWAY_API_KEY", "gateway-internal-key")
    monkeypatch.setattr(
        chat_routes, "get_claude_token", lambda: "sk-ant-oat-setup-token"
    )
    monkeypatch.setattr(
        chat_routes,
        "_get_chat_store",
        lambda: (_ for _ in ()).throw(AssertionError("store should not be used")),
    )
    monkeypatch.setattr(
        chat_routes,
        "_get_runner",
        lambda: (_ for _ in ()).throw(AssertionError("runner should not be used")),
    )

    captured: dict[str, Any] = {}

    class FakeUpstreamResponse:
        status_code = 200
        headers = {"Content-Type": "text/event-stream"}
        text = ""

        def iter_content(self, chunk_size: int = 1):
            captured["chunk_size"] = chunk_size
            yield b'data: {"type":"response.created"}\n\n'
            yield b"data: [DONE]\n\n"

        def json(self):
            return {}

        def close(self) -> None:
            captured["closed"] = True

    def fake_post(url: str, **kwargs):
        captured["url"] = url
        captured["kwargs"] = dict(kwargs)
        return FakeUpstreamResponse()

    monkeypatch.setattr(chat_routes.http_requests, "post", fake_post)

    resp = auth_client.post(
        "/v1/responses",
        headers={"X-Correlation-ID": "corr-test-123"},
        json={"input": "Gateway hello", "stream": True},
    )

    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"
    body = resp.get_data(as_text=True)
    assert 'data: {"type":"response.created"}' in body
    assert "data: [DONE]" in body
    assert captured["url"] == "https://gateway.example/v1/responses"
    assert captured["kwargs"]["stream"] is True
    assert captured["kwargs"]["json"] == {"input": "Gateway hello", "stream": True}
    assert (
        captured["kwargs"]["headers"]["Authorization"] == "Bearer gateway-internal-key"
    )
    assert (
        captured["kwargs"]["headers"]["X-Anthropic-Api-Key"] == "sk-ant-oat-setup-token"
    )
    assert captured["kwargs"]["headers"]["X-Correlation-ID"] == "corr-test-123"


def test_v1_responses_stream_accepts_setup_token_for_gateway_backend(
    auth_client, app, monkeypatch
):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "false")
    monkeypatch.setitem(app.config, "CHAT_BACKEND", "gateway")
    monkeypatch.setitem(app.config, "GATEWAY_BASE_URL", "https://gateway.example")
    monkeypatch.setattr(
        chat_routes, "get_claude_token", lambda: "sk-ant-oat01-example-example"
    )
    monkeypatch.setattr(
        chat_routes,
        "_get_chat_store",
        lambda: (_ for _ in ()).throw(AssertionError("store should not be used")),
    )
    monkeypatch.setattr(
        chat_routes,
        "_get_runner",
        lambda: (_ for _ in ()).throw(AssertionError("runner should not be used")),
    )

    captured: dict[str, Any] = {}

    class FakeUpstreamResponse:
        status_code = 200
        headers = {"Content-Type": "text/event-stream"}
        text = ""

        def iter_content(self, chunk_size: int = 1):
            captured["chunk_size"] = chunk_size
            yield b'data: {"type":"response.created"}\n\n'
            yield b"data: [DONE]\n\n"

        def json(self):
            return {}

        def close(self) -> None:
            captured["closed"] = True

    def fake_post(url: str, **kwargs):
        captured["url"] = url
        captured["kwargs"] = dict(kwargs)
        return FakeUpstreamResponse()

    monkeypatch.setattr(chat_routes.http_requests, "post", fake_post)

    resp = auth_client.post(
        "/v1/responses",
        json={"input": "hi", "stream": True},
    )

    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"
    body = resp.get_data(as_text=True)
    assert 'data: {"type":"response.created"}' in body
    assert "data: [DONE]" in body
    assert captured["url"] == "https://gateway.example/v1/responses"
    assert captured["kwargs"]["json"] == {"input": "hi", "stream": True}
    assert (
        captured["kwargs"]["headers"]["X-Anthropic-Api-Key"]
        == "sk-ant-oat01-example-example"
    )


def test_v1_responses_stream_gateway_proxy_handles_request_failure(
    auth_client, app, monkeypatch
):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "true")
    monkeypatch.setitem(app.config, "GATEWAY_BASE_URL", "https://gateway.example")
    monkeypatch.setattr(
        chat_routes, "get_claude_token", lambda: "sk-ant-oat-setup-token"
    )

    def fake_post(_url: str, **_kwargs):
        raise chat_routes.http_requests.RequestException("gateway timeout")

    monkeypatch.setattr(chat_routes.http_requests, "post", fake_post)

    resp = auth_client.post(
        "/v1/responses",
        json={"input": "Gateway hello", "stream": True},
    )

    assert resp.status_code == 502
    payload = resp.get_json()
    assert "failed to reach gateway" in payload["error"]["message"].lower()


def test_v1_responses_rejects_non_stream_mode(auth_client, monkeypatch):
    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "sk-ant-test-token")
    resp = auth_client.post(
        "/v1/responses",
        json={"input": "hi", "stream": False},
    )
    assert resp.status_code == 400
    payload = resp.get_json()
    assert "stream=true" in payload["error"]["message"]


def test_init_chat_runner_uses_backend_agnostic_factory(app, monkeypatch):
    store = FakeStore()
    factory_runner = FactoryRunner()
    factory_calls: list[tuple[str, Any, Any, str]] = []

    monkeypatch.setattr(chat_routes, "_runner", None)
    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "_project_root", lambda: "/tmp/project-root")
    app.config["CHAT_BACKEND"] = "gateway"

    def fake_build_chat_runner(*, cwd, token_provider, session_store, backend):
        factory_calls.append((cwd, token_provider, session_store, backend))
        return factory_runner

    monkeypatch.setattr(chat_routes, "build_chat_runner", fake_build_chat_runner)

    with app.app_context():
        runner = chat_routes.init_chat_runner()

    assert runner is factory_runner
    assert chat_routes._runner is factory_runner
    assert factory_calls == [
        ("/tmp/project-root", chat_routes.get_claude_token, store, "gateway")
    ]


def test_init_chat_runner_reuses_existing_runner_instance(app, monkeypatch):
    store = FakeStore()
    existing_runner = FactoryRunner()

    monkeypatch.setattr(chat_routes, "_runner", existing_runner)
    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: store)
    monkeypatch.setattr(chat_routes, "_project_root", lambda: "/tmp/new-root")
    monkeypatch.setattr(
        chat_routes,
        "build_chat_runner",
        lambda **_: (_ for _ in ()).throw(AssertionError("factory should not run")),
    )

    with app.app_context():
        runner = chat_routes.init_chat_runner()

    assert runner is existing_runner
    assert existing_runner.cwd == "/tmp/new-root"
    assert existing_runner.attached_stores == [store]


def test_init_chat_store_defaults_to_in_memory(monkeypatch):
    monkeypatch.setattr(chat_routes, "_store", None)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CHAT_STORE_PREFIX", raising=False)

    store = chat_routes.init_chat_store()

    assert isinstance(store, chat_routes.InMemoryChatStore)
    assert chat_routes._store is store


def test_init_chat_store_uses_redis_when_configured(monkeypatch):
    monkeypatch.setattr(chat_routes, "_store", None)
    monkeypatch.setenv("REDIS_URL", "redis://example.test:6379/0")
    monkeypatch.setenv("CHAT_STORE_PREFIX", "chat:test")

    captured: dict[str, str] = {}

    class FakeRedisStore:
        pass

    class FakeRedisChatStore:
        @classmethod
        def from_url(cls, redis_url, *, key_prefix):
            captured["redis_url"] = redis_url
            captured["key_prefix"] = key_prefix
            return FakeRedisStore()

    monkeypatch.setattr(chat_routes, "RedisChatStore", FakeRedisChatStore)

    store = chat_routes.init_chat_store()

    assert isinstance(store, FakeRedisStore)
    assert captured == {
        "redis_url": "redis://example.test:6379/0",
        "key_prefix": "chat:test",
    }


def test_init_chat_store_falls_back_when_redis_init_fails(monkeypatch):
    monkeypatch.setattr(chat_routes, "_store", None)
    monkeypatch.setenv("REDIS_URL", "redis://example.test:6379/0")

    class BrokenRedisChatStore:
        @classmethod
        def from_url(cls, redis_url, *, key_prefix):
            raise RuntimeError(f"cannot connect: {redis_url}:{key_prefix}")

    monkeypatch.setattr(chat_routes, "RedisChatStore", BrokenRedisChatStore)

    store = chat_routes.init_chat_store()

    assert isinstance(store, chat_routes.InMemoryChatStore)
