#!/usr/bin/env python3
"""Tests for dashboard auth token rotation endpoint."""

import os

import pytest
from flask import Flask

from routes.api_v2 import api_v2_bp


@pytest.fixture()
def app(monkeypatch):
    """Create isolated test app with API v2 routes."""
    monkeypatch.setenv("DASHBOARD_API_KEY", "old-token-123456")

    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "test-secret"
    application.register_blueprint(api_v2_bp)
    return application


@pytest.fixture()
def auth_client(app):
    """Authenticated client via session cookie."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
    return client


def test_rotate_token_requires_auth(app):
    """Anonymous users cannot rotate the auth token."""
    client = app.test_client()
    response = client.post(
        "/api/v2/settings/auth-token/rotate",
        json={"new_token": "new-token-abcdef"},
    )
    assert response.status_code == 401


def test_rotate_token_requires_new_token(auth_client):
    """Endpoint validates new_token."""
    response = auth_client.post("/api/v2/settings/auth-token/rotate", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"
    assert "new_token" in data["errors"]


def test_rotate_token_rejects_mismatched_current_token(auth_client):
    """Compare-and-swap should fail when current_token does not match."""
    response = auth_client.post(
        "/api/v2/settings/auth-token/rotate",
        json={"current_token": "wrong-token", "new_token": "new-token-abcdef"},
    )
    assert response.status_code == 409
    assert response.get_json()["status"] == "error"
    assert os.getenv("DASHBOARD_API_KEY") == "old-token-123456"


def test_rotate_token_replaces_token_atomically(auth_client, app):
    """Old token is invalid immediately; new token works immediately."""
    old_token = os.getenv("DASHBOARD_API_KEY")
    new_token = "new-token-abcdef"

    rotate_response = auth_client.post(
        "/api/v2/settings/auth-token/rotate",
        json={"current_token": old_token, "new_token": new_token},
    )
    assert rotate_response.status_code == 200
    body = rotate_response.get_json()
    assert body["status"] == "ok"
    assert body["active_token"] != new_token
    assert os.getenv("DASHBOARD_API_KEY") == new_token

    # Old key can no longer authenticate.
    old_key_client = app.test_client()
    old_key_response = old_key_client.post(
        "/api/v2/settings/auth-token/rotate",
        headers={"X-API-Key": old_token},
        json={"new_token": "next-token-xyz"},
    )
    assert old_key_response.status_code == 401

    # New key can authenticate immediately.
    new_key_client = app.test_client()
    new_key_response = new_key_client.post(
        "/api/v2/settings/auth-token/rotate",
        headers={"X-API-Key": new_token},
        json={"new_token": "next-token-xyz"},
    )
    assert new_key_response.status_code == 200
    assert os.getenv("DASHBOARD_API_KEY") == "next-token-xyz"
