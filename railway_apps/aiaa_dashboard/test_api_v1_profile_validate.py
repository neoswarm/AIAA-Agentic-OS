#!/usr/bin/env python3
"""Tests for POST /v1/profiles/validate."""

from __future__ import annotations

import pytest
from flask import Flask

from routes.api_v1 import api_v1_bp
import routes.api_v1 as api_v1_routes


@pytest.fixture
def app():
    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "test-secret"
    application.register_blueprint(api_v1_bp)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app):
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "tester"
    return c


def test_validate_profile_requires_auth(client):
    resp = client.post("/v1/profiles/validate", json={"profile_id": "default"})
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"] == "Authentication required"


def test_validate_profile_requires_json_object_payload(auth_client):
    resp = auth_client.post("/v1/profiles/validate", json=["not", "an", "object"])
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"] == "Validation failed"
    assert data["errors"]["body"] == "Request body must be a JSON object"


def test_validate_profile_requires_profile_id(auth_client):
    resp = auth_client.post("/v1/profiles/validate", json={"token": "token-123"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["errors"]["profile_id"] == "profile_id is required"


def test_validate_profile_loads_token_from_profile_setting(auth_client, monkeypatch):
    monkeypatch.setattr(api_v1_routes.models, "get_setting", lambda key: "stored-token")
    captured = {}

    def _capture_metadata(setting_key, validation_status, last_error=None):
        captured["setting_key"] = setting_key
        captured["validation_status"] = validation_status
        captured["last_error"] = last_error
        return 1

    monkeypatch.setattr(
        api_v1_routes.models, "update_setting_metadata", _capture_metadata
    )
    monkeypatch.setattr(
        api_v1_routes,
        "run_gateway_runtime_canary",
        lambda token: {
            "status": "valid",
            "message": "Gateway runtime canary succeeded",
            "output": "OK",
        },
    )

    resp = auth_client.post("/v1/profiles/validate", json={"profile_id": "default"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["validation"] == "valid"
    assert captured["setting_key"] == "claude_setup_token"
    assert captured["validation_status"] == "valid"
    assert captured["last_error"] is None


def test_validate_profile_returns_ok_for_invalid_canary(auth_client, monkeypatch):
    monkeypatch.setattr(api_v1_routes.models, "get_setting", lambda key: "stored-token")
    monkeypatch.setattr(
        api_v1_routes.models,
        "update_setting_metadata",
        lambda *args, **kwargs: 1,
    )
    monkeypatch.setattr(
        api_v1_routes,
        "run_gateway_runtime_canary",
        lambda token: {
            "status": "invalid",
            "message": "Gateway runtime canary failed",
            "error": "auth failed",
        },
    )

    resp = auth_client.post("/v1/profiles/validate", json={"profile_id": "student-a"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["validation"] == "invalid"
    assert data["validation_detail"]["error"] == "auth failed"


def test_validate_profile_returns_502_for_runtime_failures(auth_client, monkeypatch):
    monkeypatch.setattr(api_v1_routes.models, "get_setting", lambda key: "stored-token")
    monkeypatch.setattr(
        api_v1_routes.models,
        "update_setting_metadata",
        lambda *args, **kwargs: 1,
    )
    monkeypatch.setattr(
        api_v1_routes,
        "run_gateway_runtime_canary",
        lambda token: {
            "status": "runtime_unavailable",
            "message": "Claude runtime is not installed on this host",
        },
    )

    resp = auth_client.post("/v1/profiles/validate", json={"profile_id": "student-a"})
    assert resp.status_code == 502
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["validation"] == "runtime_unavailable"
