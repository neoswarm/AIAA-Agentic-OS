#!/usr/bin/env python3
"""Unit tests for webhook API guardrail branches."""

import os
import tempfile

import pytest
from flask import Flask

import database
import models
import routes.api as api_routes


@pytest.fixture
def app():
    """Create an isolated Flask app + temp DB for each test."""
    # Reset any previous thread-local connection before changing DB path.
    if hasattr(database._thread_local, "connection"):
        database._thread_local.connection.close()
        del database._thread_local.connection

    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "test-secret-key"
    application.register_blueprint(api_routes.api_bp)

    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp_db.name
    tmp_db.close()

    database.set_db_path(db_path)
    with application.app_context():
        database.init_db(application)

    yield application

    if hasattr(database._thread_local, "connection"):
        database._thread_local.connection.close()
        del database._thread_local.connection

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def client(app):
    """Unauthenticated test client."""
    return app.test_client()


@pytest.fixture
def auth_client(app):
    """Authenticated test client."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "tester"
    return c


def seed_webhook(app, slug="test-webhook", status="active"):
    """Insert one webhook workflow into the test DB."""
    with app.app_context():
        models.upsert_workflow(
            workflow_id=slug,
            name="Test Webhook",
            description="Webhook for tests",
            workflow_type="webhook",
            status=status,
            webhook_slug=slug,
        )


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/webhook-workflows", None),
        ("post", "/api/webhook-workflows/register", {"slug": "s", "name": "Webhook"}),
        ("post", "/api/webhook-workflows/unregister", {"slug": "s"}),
        ("post", "/api/webhook-workflows/toggle", {"slug": "s"}),
        ("post", "/api/webhook-workflows/test", {"slug": "s"}),
    ],
)
def test_webhook_endpoints_require_auth(client, method, path, payload):
    """Guardrail: all webhook management endpoints require auth."""
    kwargs = {"json": payload} if payload is not None else {}
    resp = getattr(client, method)(path, **kwargs)
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["status"] == "error"
    assert "Authentication required" in data["message"]


def test_register_webhook_requires_slug_and_name(auth_client):
    """Guardrail: register rejects missing required fields."""
    resp = auth_client.post("/api/webhook-workflows/register", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"] == "slug and name are required"


def test_unregister_webhook_requires_slug(auth_client):
    """Guardrail: unregister rejects empty slug."""
    resp = auth_client.post("/api/webhook-workflows/unregister", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"] == "slug is required"


def test_unregister_webhook_not_found(auth_client):
    """Guardrail: unregister returns 404 for unknown webhook."""
    resp = auth_client.post("/api/webhook-workflows/unregister", json={"slug": "missing"})
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["status"] == "error"
    assert "not found" in data["message"]


def test_toggle_webhook_requires_slug(auth_client):
    """Guardrail: toggle rejects empty slug."""
    resp = auth_client.post("/api/webhook-workflows/toggle", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"] == "slug is required"


def test_toggle_webhook_not_found(auth_client):
    """Guardrail: toggle returns 404 for unknown webhook."""
    resp = auth_client.post("/api/webhook-workflows/toggle", json={"slug": "missing"})
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["status"] == "error"
    assert "not found" in data["message"]


def test_test_webhook_requires_slug(auth_client):
    """Guardrail: test endpoint rejects empty slug."""
    resp = auth_client.post("/api/webhook-workflows/test", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"] == "slug is required"


def test_test_webhook_not_found(auth_client):
    """Guardrail: test endpoint returns 404 for unknown webhook."""
    resp = auth_client.post("/api/webhook-workflows/test", json={"slug": "missing"})
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["status"] == "error"
    assert "not found" in data["message"]


def test_test_webhook_handles_failed_upstream_response(app, auth_client, monkeypatch):
    """Guardrail: non-2xx upstream responses are surfaced as failed."""
    seed_webhook(app, slug="hook-failed")

    class DummyResponse:
        ok = False
        status_code = 503
        text = "upstream unavailable"

    monkeypatch.setattr(api_routes.http_requests, "post", lambda *args, **kwargs: DummyResponse())

    resp = auth_client.post("/api/webhook-workflows/test", json={"slug": "hook-failed"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["test_status"] == "failed"
    assert data["status_code"] == 503
    assert "upstream unavailable" in data["response"]


def test_test_webhook_handles_request_exception(app, auth_client, monkeypatch):
    """Guardrail: network exceptions are converted to structured error payload."""
    seed_webhook(app, slug="hook-error")

    def raise_request_error(*args, **kwargs):
        raise api_routes.http_requests.RequestException("network down")

    monkeypatch.setattr(api_routes.http_requests, "post", raise_request_error)

    resp = auth_client.post("/api/webhook-workflows/test", json={"slug": "hook-error"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["test_status"] == "error"
    assert data["status_code"] == 0
    assert "network down" in data["response"]
