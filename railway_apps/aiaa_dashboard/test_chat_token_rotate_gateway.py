#!/usr/bin/env python3
"""Tests for gateway-backed Claude token rotate flow."""

from __future__ import annotations

import os

import pytest
from flask import Flask

import routes.chat as chat_routes


@pytest.fixture()
def app():
    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "chat-token-rotate-test-secret"
    application.register_blueprint(chat_routes.chat_bp)
    return application


@pytest.fixture()
def auth_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "test-admin"
    return client


def test_rotate_token_returns_409_for_current_token_mismatch(
    auth_client, monkeypatch
):
    monkeypatch.setenv("CLAUDE_SETUP_TOKEN", "old-token-123456")
    monkeypatch.setattr(
        chat_routes,
        "validate_claude_token",
        lambda _token: {"status": "unknown", "message": "accepted"},
    )
    upsert_calls = []
    monkeypatch.setattr(
        chat_routes,
        "_gateway_upsert_setup_token",
        lambda token: upsert_calls.append(token) or {"status": "ok"},
    )

    response = auth_client.post(
        "/api/chat/token/rotate",
        json={
            "current_token": "different-token",
            "new_token": "new-token-abcdef",
        },
    )

    assert response.status_code == 409
    assert response.get_json()["status"] == "error"
    assert os.getenv("CLAUDE_SETUP_TOKEN") == "old-token-123456"
    assert upsert_calls == []


def test_rotate_token_keeps_local_state_when_gateway_update_fails(
    auth_client, monkeypatch
):
    monkeypatch.setenv("CLAUDE_SETUP_TOKEN", "old-token-123456")
    monkeypatch.setattr(
        chat_routes,
        "validate_claude_token",
        lambda _token: {"status": "unknown", "message": "accepted"},
    )
    monkeypatch.setattr(
        chat_routes,
        "_gateway_upsert_setup_token",
        lambda _token: (_ for _ in ()).throw(RuntimeError("gateway unavailable")),
    )
    set_calls = []
    monkeypatch.setattr(
        chat_routes.models,
        "set_setting",
        lambda *args, **kwargs: set_calls.append((args, kwargs)),
        raising=False,
    )

    response = auth_client.post(
        "/api/chat/token/rotate",
        json={
            "current_token": "old-token-123456",
            "new_token": "new-token-abcdef",
        },
    )

    assert response.status_code == 502
    body = response.get_json()
    assert body["status"] == "error"
    assert "Gateway token update failed" in body["message"]
    assert os.getenv("CLAUDE_SETUP_TOKEN") == "old-token-123456"
    assert set_calls == []


def test_rotate_token_rolls_back_gateway_when_local_persist_fails(
    auth_client, monkeypatch
):
    old_token = "old-token-123456"
    new_token = "new-token-abcdef"
    monkeypatch.setenv("CLAUDE_SETUP_TOKEN", old_token)
    monkeypatch.setattr(
        chat_routes,
        "validate_claude_token",
        lambda _token: {"status": "unknown", "message": "accepted"},
    )

    upsert_calls = []
    monkeypatch.setattr(
        chat_routes,
        "_gateway_upsert_setup_token",
        lambda token: upsert_calls.append(token) or {"status": "ok"},
    )
    monkeypatch.setattr(
        chat_routes.models,
        "set_setting",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("db down")),
        raising=False,
    )

    response = auth_client.post(
        "/api/chat/token/rotate",
        json={"current_token": old_token, "new_token": new_token},
    )

    assert response.status_code == 500
    body = response.get_json()
    assert body["status"] == "error"
    assert body["rollback"]["status"] == "ok"
    assert upsert_calls == [new_token, old_token]
    assert os.getenv("CLAUDE_SETUP_TOKEN") == old_token


def test_rotate_token_updates_gateway_and_local_state_on_success(
    auth_client, monkeypatch
):
    old_token = "old-token-123456"
    new_token = "new-token-abcdef"
    monkeypatch.setenv("CLAUDE_SETUP_TOKEN", old_token)
    monkeypatch.setattr(
        chat_routes,
        "validate_claude_token",
        lambda _token: {"status": "unknown", "message": "accepted"},
    )

    upsert_calls = []
    monkeypatch.setattr(
        chat_routes,
        "_gateway_upsert_setup_token",
        lambda token: upsert_calls.append(token) or {"status": "ok"},
    )

    set_calls = []
    monkeypatch.setattr(
        chat_routes.models,
        "set_setting",
        lambda key, value: set_calls.append((key, value)) or 1,
        raising=False,
    )
    monkeypatch.setattr(chat_routes, "_persist_to_railway_async", lambda *_args: True)
    monkeypatch.setattr(chat_routes, "init_chat_runner", lambda *_args, **_kwargs: None)

    response = auth_client.post(
        "/api/chat/token/rotate",
        json={"current_token": old_token, "new_token": new_token},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["persisted_to_railway"] is True
    assert os.getenv("CLAUDE_SETUP_TOKEN") == new_token
    assert upsert_calls == [new_token]
    assert set_calls == [(chat_routes.CLAUDE_TOKEN_SETTING_KEY, new_token)]
