#!/usr/bin/env python3
"""Tests for API token redaction in JSON responses."""

import json

import pytest
from flask import Flask

import routes.api_v2 as api_v2
from routes.api_v2 import api_v2_bp


@pytest.fixture
def auth_client():
    """Create a Flask test client with an authenticated session."""
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.register_blueprint(api_v2_bp)

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    return client


def _assert_redacted(payload, raw_token):
    """Ensure raw token material is not present in serialized payloads."""
    assert raw_token not in json.dumps(payload)


@pytest.mark.parametrize(
    ("raw_token", "message"),
    [
        (
            "sk-or-test-1234567890abcdef",
            "provider error: Authorization: Bearer sk-or-test-1234567890abcdef",
        ),
        (
            "token-value-1234567890abcdef",
            "provider error: api_key=token-value-1234567890abcdef",
        ),
        (
            "github_pat_1234567890abcdefghijklmno",
            "provider error: github_pat_1234567890abcdefghijklmno",
        ),
    ],
)
def test_execution_status_error_redacts_token_like_messages(
    auth_client, monkeypatch, raw_token, message
):
    """GET /api/v2/executions/<id>/status should redact token-like error text."""

    def _boom(_execution_id):
        raise RuntimeError(message)

    monkeypatch.setattr(api_v2, "get_execution_status", _boom)

    resp = auth_client.get("/api/v2/executions/exe-error/status")
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["status"] == "error"
    _assert_redacted(data, raw_token)


def test_execution_status_redacts_token_params(auth_client, monkeypatch):
    """GET /api/v2/executions/<id>/status should redact sensitive params."""
    raw_token = "sk-or-test-1234567890abcdef"

    monkeypatch.setattr(
        api_v2,
        "get_execution_status",
        lambda _execution_id: {
            "status": "success",
            "skill_name": "demo",
            "params": {
                "api_key": raw_token,
                "note": "safe-value",
            },
            "output_preview": f"Bearer {raw_token}",
        },
    )

    resp = auth_client.get("/api/v2/executions/exe-1/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["execution"]["params"]["api_key"] != raw_token
    _assert_redacted(data, raw_token)


def test_execution_output_redacts_token_params(auth_client, monkeypatch):
    """GET /api/v2/executions/<id>/output should redact sensitive params."""
    raw_token = "pplx-token-1234567890abcdef"

    monkeypatch.setattr(
        api_v2,
        "get_execution_status",
        lambda _execution_id: {
            "status": "success",
            "skill_name": "demo",
            "params": {
                "token": raw_token,
                "input": "hello",
            },
            "output_path": None,
            "output_preview": f"token={raw_token}",
        },
    )

    resp = auth_client.get("/api/v2/executions/exe-2/output")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["params"]["token"] != raw_token
    _assert_redacted(data, raw_token)


def test_execution_list_redacts_token_params(auth_client, monkeypatch):
    """GET /api/v2/executions should redact token-like param values."""
    raw_token = "sk-ant-token-1234567890abcdef"

    monkeypatch.setattr(
        api_v2.models,
        "get_skill_executions",
        lambda skill_name=None, status=None, limit=50: [
            {
                "execution_id": "exe-3",
                "skill_name": "demo",
                "params": {
                    "secret_token": raw_token,
                    "query": "safe",
                },
            }
        ],
        raising=False,
    )

    resp = auth_client.get("/api/v2/executions")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["executions"][0]["params"]["secret_token"] != raw_token
    _assert_redacted(data, raw_token)
