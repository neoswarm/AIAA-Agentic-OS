#!/usr/bin/env python3
"""Regression tests for Claude auth token validation in chat routes."""

from __future__ import annotations

import hashlib
import os
import tempfile

import pytest

# Configure environment before importing app modules.
os.environ["FLASK_ENV"] = "testing"
os.environ["DASHBOARD_USERNAME"] = "testadmin"
os.environ["DASHBOARD_PASSWORD_HASH"] = hashlib.sha256(b"testpass123").hexdigest()
os.environ["FLASK_SECRET_KEY"] = hashlib.sha256(b"chat-token-test-secret").hexdigest()
_TEST_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DB_PATH"] = _TEST_DB.name

from app import create_app
import database
import models
import routes.chat as chat_routes


SETUP_TOKEN_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMifQ.signature"
SETUP_TOKEN_OAT = "sk-ant-oat01-example-example-example"


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


@pytest.mark.parametrize("token", [SETUP_TOKEN_JWT, SETUP_TOKEN_OAT])
def test_validate_setup_token_returns_unsupported_without_rest_probe(
    monkeypatch, token
):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "false")
    monkeypatch.delenv("CHAT_BACKEND", raising=False)

    def _unexpected_get(*args, **kwargs):
        raise AssertionError(
            "REST endpoint should not be called for setup-token artifacts"
        )

    monkeypatch.setattr(chat_routes.http_requests, "get", _unexpected_get)

    result = chat_routes.validate_claude_token(token)

    assert result["status"] == "unsupported"
    assert result["http_status"] is None
    assert "gateway mode is disabled" in result["message"].lower()


@pytest.mark.parametrize("token", [SETUP_TOKEN_JWT, SETUP_TOKEN_OAT])
def test_validate_setup_token_returns_unknown_when_gateway_mode_enabled(
    monkeypatch, token
):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "true")
    monkeypatch.delenv("CHAT_BACKEND", raising=False)

    def _unexpected_get(*args, **kwargs):
        raise AssertionError(
            "REST endpoint should not be called for setup-token artifacts"
        )

    monkeypatch.setattr(chat_routes.http_requests, "get", _unexpected_get)

    result = chat_routes.validate_claude_token(token)

    assert result["status"] == "unknown"
    assert result["http_status"] is None
    assert "gateway mode" in result["message"].lower()


@pytest.mark.parametrize("token", [SETUP_TOKEN_JWT, SETUP_TOKEN_OAT])
def test_validate_setup_token_skips_hard_block_for_gateway_backend(monkeypatch, token):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "false")
    monkeypatch.setenv("CHAT_BACKEND", "gateway")

    def _unexpected_get(*args, **kwargs):
        raise AssertionError(
            "REST endpoint should not be called for setup-token artifacts"
        )

    monkeypatch.setattr(chat_routes.http_requests, "get", _unexpected_get)

    result = chat_routes.validate_claude_token(token)

    assert result["status"] == "unknown"
    assert result["http_status"] is None
    assert "gateway mode" in result["message"].lower()


def test_validate_non_setup_token_keeps_rest_behavior(monkeypatch):
    class _Resp:
        status_code = 401

    monkeypatch.setattr(
        chat_routes.http_requests, "get", lambda *args, **kwargs: _Resp()
    )

    result = chat_routes.validate_claude_token("not-a-jwt-token")

    assert result["status"] == "expired"
    assert result["http_status"] == 401


@pytest.mark.parametrize("token", [SETUP_TOKEN_JWT, SETUP_TOKEN_OAT])
def test_save_token_rejects_setup_token_with_unsupported_validation(
    auth_client, app, monkeypatch, token
):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "false")
    monkeypatch.delenv("CHAT_BACKEND", raising=False)
    app.config.pop("CHAT_BACKEND", None)
    monkeypatch.setattr(chat_routes, "_persist_to_railway_async", lambda *_: False)
    monkeypatch.setattr(chat_routes, "init_chat_runner", lambda *_: None)

    resp = auth_client.post("/api/chat/token", json={"token": token})

    assert resp.status_code == 400
    body = resp.get_json()
    assert body["status"] == "error"
    assert body["validation"]["status"] == "unsupported"

    with app.app_context():
        assert models.get_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY) in ("", None)


@pytest.mark.parametrize("token", [SETUP_TOKEN_JWT, SETUP_TOKEN_OAT])
def test_save_token_accepts_setup_token_when_gateway_mode_enabled(
    auth_client, app, monkeypatch, token
):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "true")
    monkeypatch.delenv("CHAT_BACKEND", raising=False)
    app.config.pop("CHAT_BACKEND", None)
    monkeypatch.setattr(chat_routes, "_persist_to_railway_async", lambda *_: False)
    monkeypatch.setattr(chat_routes, "init_chat_runner", lambda *_: None)

    resp = auth_client.post("/api/chat/token", json={"token": token})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["validation"] == "unknown"

    with app.app_context():
        assert models.get_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY) == token


@pytest.mark.parametrize("token", [SETUP_TOKEN_JWT, SETUP_TOKEN_OAT])
def test_save_token_accepts_setup_token_when_backend_gateway(
    auth_client, app, monkeypatch, token
):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "false")
    monkeypatch.delenv("CHAT_BACKEND", raising=False)
    monkeypatch.setitem(app.config, "CHAT_BACKEND", "gateway")
    monkeypatch.setattr(chat_routes, "_persist_to_railway_async", lambda *_: False)
    monkeypatch.setattr(chat_routes, "init_chat_runner", lambda *_: None)

    resp = auth_client.post("/api/chat/token", json={"token": token})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["validation"] == "unknown"

    with app.app_context():
        assert models.get_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY) == token


@pytest.mark.parametrize("endpoint", ["/api/chat/sessions", "/api/chat/message"])
def test_chat_endpoints_block_unsupported_setup_token(
    auth_client, app, endpoint, monkeypatch
):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "false")
    monkeypatch.delenv("CHAT_BACKEND", raising=False)
    app.config.pop("CHAT_BACKEND", None)
    with app.app_context():
        models.set_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY, SETUP_TOKEN_OAT)

    payload = (
        {"session_id": "abc", "message": "hello"}
        if endpoint.endswith("message")
        else {}
    )
    resp = auth_client.post(endpoint, json=payload)
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["status"] == "error"
    assert "gateway mode is disabled" in body["message"].lower()


def test_create_session_allows_setup_token_when_gateway_mode_enabled(
    auth_client, app, monkeypatch
):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "true")
    monkeypatch.delenv("CHAT_BACKEND", raising=False)
    app.config.pop("CHAT_BACKEND", None)

    class _Runner:
        def ensure_session(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(chat_routes, "_get_runner", lambda: _Runner())

    with app.app_context():
        models.set_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY, SETUP_TOKEN_OAT)

    resp = auth_client.post("/api/chat/sessions", json={"title": "Flag chat"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["session"]["title"] == "Flag chat"


def test_create_session_does_not_hard_block_setup_token_for_gateway(
    auth_client, app, monkeypatch
):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "false")
    monkeypatch.setitem(app.config, "CHAT_BACKEND", "gateway")

    class _Runner:
        def ensure_session(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(chat_routes, "_get_runner", lambda: _Runner())

    with app.app_context():
        models.set_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY, SETUP_TOKEN_OAT)

    resp = auth_client.post("/api/chat/sessions", json={"title": "Gateway chat"})

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["session"]["title"] == "Gateway chat"


def test_send_message_does_not_hard_block_setup_token_for_gateway(auth_client, app, monkeypatch):
    monkeypatch.setenv(chat_routes.GATEWAY_MODE_FLAG, "false")
    monkeypatch.setitem(app.config, "CHAT_BACKEND", "gateway")
    with app.app_context():
        models.set_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY, SETUP_TOKEN_OAT)

    resp = auth_client.post(
        "/api/chat/message",
        json={"session_id": "missing-session", "message": "hello"},
    )

    assert resp.status_code == 404
    body = resp.get_json()
    assert body["status"] == "error"
    assert "gateway mode is disabled" not in body["message"].lower()


def test_revoke_token_requires_auth(app):
    client = app.test_client()
    response = client.post("/api/chat/token/revoke")
    assert response.status_code == 401


def test_revoke_token_calls_gateway_and_syncs_local_metadata(
    auth_client, app, monkeypatch
):
    captured: dict[str, str | dict[str, str]] = {}

    class FakeGatewayClient:
        def __init__(self, base_url, api_key=None, **_kwargs):
            captured["base_url"] = base_url
            captured["api_key"] = api_key

        def post_json(self, path, *, payload=None, **_kwargs):
            captured["path"] = path
            captured["payload"] = payload or {}
            return {"status": "ok", "revoked": True}

    monkeypatch.setattr(chat_routes, "GatewayClient", FakeGatewayClient)
    monkeypatch.setenv("GATEWAY_BASE_URL", "https://gateway.example.test")
    monkeypatch.setenv("GATEWAY_API_KEY", "gateway-test-key")
    monkeypatch.setenv("CLAUDE_SETUP_TOKEN", SETUP_TOKEN_OAT)

    with app.app_context():
        models.set_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY, SETUP_TOKEN_OAT)
        assert models.get_setup_token_profile("default")["status"] == "active"

    response = auth_client.post("/api/chat/token/revoke")
    assert response.status_code == 200

    body = response.get_json()
    assert body["status"] == "ok"
    assert body["profile_id"] == "default"
    assert body["revoked"] is True
    assert captured["base_url"] == "https://gateway.example.test"
    assert captured["api_key"] == "gateway-test-key"
    assert captured["path"] == "/v1/profiles/revoke"
    assert captured["payload"] == {"profile_id": "default"}
    assert "CLAUDE_SETUP_TOKEN" not in os.environ

    with app.app_context():
        assert models.get_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY) in ("", None)
        profile = models.get_setup_token_profile("default")
        assert profile is not None
        assert profile["status"] == "revoked"
        assert profile["token"] == ""


def test_revoke_token_keeps_local_token_when_gateway_call_fails(
    auth_client, app, monkeypatch
):
    class FailingGatewayClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def post_json(self, *_args, **_kwargs):
            raise chat_routes.GatewayClientError("gateway unavailable")

    monkeypatch.setattr(chat_routes, "GatewayClient", FailingGatewayClient)
    monkeypatch.setenv("GATEWAY_BASE_URL", "https://gateway.example.test")
    monkeypatch.setenv("GATEWAY_API_KEY", "gateway-test-key")
    monkeypatch.setenv("CLAUDE_SETUP_TOKEN", SETUP_TOKEN_OAT)

    with app.app_context():
        models.set_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY, SETUP_TOKEN_OAT)
        assert models.get_setup_token_profile("default")["status"] == "active"

    response = auth_client.post("/api/chat/token/revoke")
    assert response.status_code == 502
    body = response.get_json()
    assert body["status"] == "error"
    assert "gateway profile revoke failed" in body["message"].lower()
    assert os.environ.get("CLAUDE_SETUP_TOKEN") == SETUP_TOKEN_OAT

    with app.app_context():
        assert models.get_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY) == SETUP_TOKEN_OAT
        assert models.get_setup_token_profile("default")["status"] == "active"
