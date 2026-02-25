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

    def _unexpected_get(*args, **kwargs):
        raise AssertionError(
            "REST endpoint should not be called for setup-token artifacts"
        )

    monkeypatch.setattr(chat_routes.http_requests, "get", _unexpected_get)

    result = chat_routes.validate_claude_token(token)

    assert result["status"] == "unknown"
    assert result["http_status"] is None
    assert "format accepted" in result["message"].lower()


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
    with app.app_context():
        models.set_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY, SETUP_TOKEN_OAT)

    resp = auth_client.post("/api/chat/sessions", json={})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["status"] == "ok"
