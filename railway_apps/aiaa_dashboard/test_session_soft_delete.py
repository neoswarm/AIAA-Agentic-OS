#!/usr/bin/env python3
"""Tests for the session soft-delete API endpoint."""

from flask import Flask
import pytest

from routes.api_v2 import api_v2_bp


@pytest.fixture(autouse=True)
def stub_log_event(monkeypatch):
    """Avoid filesystem side effects from auth event logging."""
    monkeypatch.setattr("routes.api_v2.models.log_event", lambda *args, **kwargs: 1)


@pytest.fixture()
def client():
    """Create a lightweight test client with only API v2 routes."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["SESSION_COOKIE_SECURE"] = False
    app.register_blueprint(api_v2_bp)
    return app.test_client()


def test_soft_delete_session_requires_auth(client):
    """DELETE /api/v2/session without auth returns 401."""
    response = client.delete("/api/v2/session")

    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "error"
    assert data["message"] == "Authentication required"


def test_soft_delete_session_marks_session_deleted(client):
    """Soft-delete marks session state and blocks subsequent protected calls."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testadmin"

    response = client.delete("/api/v2/session")
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "ok"
    assert data["session"]["status"] == "deleted"
    assert data["session"]["deleted_at"]

    with client.session_transaction() as sess:
        assert sess.get("logged_in") is False
        assert sess.get("session_status") == "deleted"
        assert sess.get("session_deleted_at")

    # Confirm auth is no longer accepted after soft-delete.
    follow_up = client.get("/api/v2/executions")
    assert follow_up.status_code == 401
