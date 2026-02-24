#!/usr/bin/env python3
"""Tests for API v2 token revoke/clear endpoint."""

from flask import Flask
import pytest

from routes.api_v2 import api_v2_bp
import routes.api_v2 as api_v2


@pytest.fixture
def app(monkeypatch):
    """Create a minimal Flask app with the API v2 blueprint."""
    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "test-secret"

    delete_calls = []

    def fake_delete_setting(setting_key):
        delete_calls.append(setting_key)
        return 1

    monkeypatch.setattr(api_v2.models, "delete_setting", fake_delete_setting, raising=False)
    monkeypatch.setattr(api_v2.models, "set_setting", lambda _k, _v: 1, raising=False)

    application.register_blueprint(api_v2_bp)
    application.config["DELETE_CALLS"] = delete_calls
    return application


@pytest.fixture
def client(app):
    """Unauthenticated test client."""
    return app.test_client()


@pytest.fixture
def auth_client(app):
    """Authenticated test client with dashboard session."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testadmin"
    return c


def test_revoke_token_requires_auth(client):
    """Revoke endpoint should require authentication."""
    resp = client.post("/api/v2/settings/api-keys/revoke", json={"key_name": "openrouter"})
    assert resp.status_code == 401


def test_revoke_token_clears_env_and_storage(auth_client, app, monkeypatch):
    """Revoke removes the token from env and persistent settings."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-secret")

    resp = auth_client.post("/api/v2/settings/api-keys/revoke", json={"key_name": "openrouter"})
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["key_name"] == "OPENROUTER_API_KEY"
    assert "OPENROUTER_API_KEY" not in api_v2.os.environ
    assert app.config["DELETE_CALLS"][-1] == "api_key.OPENROUTER_API_KEY"


def test_clear_token_alias_invalidates_runner_token(auth_client, app, monkeypatch):
    """Clear alias should revoke runner token aliases too."""
    monkeypatch.setenv("DASHBOARD_API_KEY", "runner-secret")

    resp = auth_client.post("/api/v2/settings/api-keys/clear", json={"key_name": "runner_token"})
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["key_name"] == "DASHBOARD_API_KEY"
    assert "DASHBOARD_API_KEY" not in api_v2.os.environ
    assert app.config["DELETE_CALLS"][-1] == "api_key.DASHBOARD_API_KEY"
