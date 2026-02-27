#!/usr/bin/env python3
"""Tests for POST /api/chat/token/validate gateway profile delegation."""

from __future__ import annotations

import pytest
from flask import Flask

import routes.api_v1 as api_v1_routes
import routes.chat as chat_routes


@pytest.fixture()
def app():
    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "chat-token-validate-test-secret"
    application.register_blueprint(chat_routes.chat_bp)
    return application


@pytest.fixture()
def auth_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "test-admin"
    return client


def test_chat_token_validate_uses_gateway_profile_validation(auth_client, monkeypatch):
    captured = {}

    def _validate_profile_token(profile_id: str, token: str = ""):
        captured["profile_id"] = profile_id
        captured["token"] = token
        return (
            {
                "status": "ok",
                "profile_id": "default",
                "validation": "valid",
                "validation_detail": {"status": "valid", "message": "Gateway ok"},
            },
            200,
        )

    def _unexpected_provider_validation(_token: str):
        raise AssertionError("Direct provider validation should not be called")

    monkeypatch.setattr(
        api_v1_routes,
        "validate_profile_token",
        _validate_profile_token,
    )
    monkeypatch.setattr(
        chat_routes,
        "validate_claude_token",
        _unexpected_provider_validation,
    )

    resp = auth_client.post(
        "/api/chat/token/validate",
        json={"token": "sk-ant-oat01-example-example"},
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["configured"] is True
    assert body["validation"] == "valid"
    assert body["validation_detail"]["status"] == "valid"
    assert body["redacted"] == "sk-ant...mple"
    assert captured == {
        "profile_id": "default",
        "token": "sk-ant-oat01-example-example",
    }


def test_chat_token_validate_propagates_gateway_runtime_failures(
    auth_client, monkeypatch
):
    monkeypatch.setattr(
        api_v1_routes,
        "validate_profile_token",
        lambda profile_id, token="": (
            {
                "status": "error",
                "profile_id": profile_id,
                "validation": "runtime_unavailable",
                "validation_detail": {
                    "status": "runtime_unavailable",
                    "message": "Claude runtime is not installed on this host",
                },
                "message": "Gateway runtime canary failed",
            },
            502,
        ),
    )

    resp = auth_client.post(
        "/api/chat/token/validate",
        json={"token": "sk-ant-oat01-example-example"},
    )

    assert resp.status_code == 502
    body = resp.get_json()
    assert body["status"] == "error"
    assert body["configured"] is True
    assert body["validation"] == "runtime_unavailable"
    assert body["message"] == "Gateway runtime canary failed"
    assert body["validation_detail"]["status"] == "runtime_unavailable"


def test_chat_token_validate_missing_token_skips_gateway_validation(
    auth_client, monkeypatch
):
    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "")

    def _unexpected_validate_profile_token(*_args, **_kwargs):
        raise AssertionError(
            "Gateway profile validation should not run without a token"
        )

    monkeypatch.setattr(
        api_v1_routes,
        "validate_profile_token",
        _unexpected_validate_profile_token,
    )

    resp = auth_client.post("/api/chat/token/validate", json={})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["configured"] is False
    assert body["validation"] == "missing"
    assert body["validation_detail"]["status"] == "missing"
