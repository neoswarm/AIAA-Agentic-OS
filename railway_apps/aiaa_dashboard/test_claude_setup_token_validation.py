#!/usr/bin/env python3
"""Regression tests for Claude setup-token validation in chat routes."""

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


def test_validate_setup_token_skips_rest_models_probe(monkeypatch):
    def _unexpected_get(*args, **kwargs):
        raise AssertionError("REST endpoint should not be called for setup-token JWTs")

    monkeypatch.setattr(chat_routes.http_requests, "get", _unexpected_get)

    result = chat_routes.validate_claude_token(SETUP_TOKEN_JWT)

    assert result["status"] == "unknown"
    assert result["http_status"] is None


def test_validate_non_setup_token_keeps_rest_behavior(monkeypatch):
    class _Resp:
        status_code = 401

    monkeypatch.setattr(chat_routes.http_requests, "get", lambda *args, **kwargs: _Resp())

    result = chat_routes.validate_claude_token("not-a-jwt-token")

    assert result["status"] == "expired"
    assert result["http_status"] == 401


def test_save_token_accepts_setup_token_with_unknown_validation(
    auth_client, app, monkeypatch
):
    monkeypatch.setattr(chat_routes, "_persist_to_railway_async", lambda *_: False)
    monkeypatch.setattr(chat_routes, "init_chat_runner", lambda *_: None)

    resp = auth_client.post("/api/chat/token", json={"token": SETUP_TOKEN_JWT})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["validation"] == "unknown"

    with app.app_context():
        assert (
            models.get_setting(chat_routes.CLAUDE_TOKEN_SETTING_KEY) == SETUP_TOKEN_JWT
        )

