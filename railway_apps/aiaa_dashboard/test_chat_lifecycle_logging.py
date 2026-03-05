#!/usr/bin/env python3
"""Tests for structured token and chat session lifecycle logs in chat routes."""

from __future__ import annotations

import json
import logging
import os

import pytest
from flask import Flask

import routes.chat as chat_routes


class _FakeStore:
    def create_session(
        self,
        session_id: str,
        *,
        title: str = "New chat",
        status: str = "idle",
        sdk_session_id: str | None = None,
    ) -> dict:
        return {
            "id": session_id,
            "title": title,
            "status": status,
            "sdk_session_id": sdk_session_id,
        }


class _FakeRunner:
    def ensure_session(
        self,
        session_id: str,
        *,
        title: str | None = None,
        sdk_session_id: str | None = None,
    ) -> dict:
        return {"id": session_id, "title": title, "sdk_session_id": sdk_session_id}


def _lifecycle_payloads(caplog, event_name: str) -> list[dict]:
    payloads: list[dict] = []
    for record in caplog.records:
        try:
            payload = json.loads(record.getMessage())
        except (TypeError, json.JSONDecodeError):
            continue
        if payload.get("event") == event_name:
            payloads.append(payload)
    return payloads


@pytest.fixture()
def app():
    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "chat-lifecycle-test-secret"
    application.register_blueprint(chat_routes.chat_bp)
    return application


@pytest.fixture()
def auth_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "test-admin"
    return client


def test_save_token_emits_structured_token_lifecycle_log(
    auth_client, monkeypatch, caplog
):
    token = "sk-ant-test-token-1234567890"
    monkeypatch.delenv("CLAUDE_SETUP_TOKEN", raising=False)

    monkeypatch.setattr(
        chat_routes,
        "validate_claude_token",
        lambda _token: {
            "status": "valid",
            "http_status": 200,
            "message": "Token is valid",
        },
    )
    monkeypatch.setattr(chat_routes.models, "set_setting", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(
        chat_routes, "_persist_to_railway_async", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr(chat_routes, "init_chat_runner", lambda *_args, **_kwargs: None)

    caplog.set_level(logging.INFO, logger="routes.chat")
    caplog.clear()

    response = auth_client.post("/api/chat/token", json={"token": token})

    assert response.status_code == 200
    payloads = _lifecycle_payloads(caplog, "token_lifecycle")
    assert any(
        payload.get("action") == "save"
        and payload.get("status") == "success"
        and payload.get("validation") == "valid"
        and payload.get("username") == "test-admin"
        and payload.get("method") == "POST"
        and payload.get("path") == "/api/chat/token"
        and payload.get("redacted") == "sk-ant...7890"
        for payload in payloads
    )
    assert token not in "\n".join(record.getMessage() for record in caplog.records)
    os.environ.pop("CLAUDE_SETUP_TOKEN", None)


def test_create_session_emits_structured_chat_session_lifecycle_log(
    auth_client, monkeypatch, caplog
):
    monkeypatch.setattr(chat_routes, "_get_chat_store", lambda: _FakeStore())
    monkeypatch.setattr(chat_routes, "_get_runner", lambda: _FakeRunner())
    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "sk-ant-valid-token")
    monkeypatch.setattr(
        chat_routes.secrets, "token_hex", lambda _size: "chat-session-1"
    )

    caplog.set_level(logging.INFO, logger="routes.chat")
    caplog.clear()

    response = auth_client.post(
        "/api/chat/sessions", json={"title": "Lifecycle Session"}
    )

    assert response.status_code == 201
    payloads = _lifecycle_payloads(caplog, "chat_session_lifecycle")
    assert any(
        payload.get("action") == "create"
        and payload.get("status") == "success"
        and payload.get("session_id") == "chat-session-1"
        and payload.get("username") == "test-admin"
        and payload.get("method") == "POST"
        and payload.get("path") == "/api/chat/sessions"
        for payload in payloads
    )
