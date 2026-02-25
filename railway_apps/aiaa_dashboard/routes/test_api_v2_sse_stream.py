#!/usr/bin/env python3
"""Tests for API v2 execution SSE stream event IDs."""

from flask import Flask
import pytest

import routes.api_v2 as api_v2_routes


@pytest.fixture()
def app():
    """Lightweight Flask app with only API v2 routes registered."""
    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "test-secret"
    application.register_blueprint(api_v2_routes.api_v2_bp)
    return application


@pytest.fixture()
def client(app):
    """Unauthenticated client."""
    return app.test_client()


@pytest.fixture()
def auth_client(app):
    """Authenticated client with session-based auth."""
    test_client = app.test_client()
    with test_client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testadmin"
    return test_client


def test_execution_stream_requires_auth(client):
    """GET stream endpoint requires auth."""
    response = client.get("/api/v2/executions/exec-1/stream")
    assert response.status_code == 401


def test_execution_stream_not_found(auth_client, monkeypatch):
    """GET stream endpoint returns 404 when execution does not exist."""
    monkeypatch.setattr(api_v2_routes, "get_execution_status", lambda _: None)

    response = auth_client.get("/api/v2/executions/missing/stream")
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["status"] == "error"


def test_execution_stream_includes_server_event_id(auth_client, monkeypatch):
    """SSE payload includes server event IDs for reconnect support."""
    monkeypatch.setattr(
        api_v2_routes,
        "get_execution_status",
        lambda execution_id: {
            "execution_id": execution_id,
            "status": "running",
            "skill_name": "blog-post",
        },
    )

    response = auth_client.get("/api/v2/executions/exec-1/stream")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/event-stream")

    body = response.get_data(as_text=True)
    assert "id: 1\n" in body
    assert "event: execution\n" in body
    assert '"execution_id": "exec-1"' in body
