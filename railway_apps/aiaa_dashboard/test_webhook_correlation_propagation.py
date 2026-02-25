#!/usr/bin/env python3
"""Tests for webhook correlation id propagation to forwarded gateway requests."""

import pytest
from flask import Flask

import database
import models
import routes.views as views_routes
from routes.views import views_bp


@pytest.fixture()
def app(tmp_path):
    """Create an isolated Flask app with views routes and a temp database."""
    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "test-secret-key"

    database.set_db_path(str(tmp_path / "dashboard.db"))
    with application.app_context():
        database.init_db(application)

    application.register_blueprint(views_bp)
    return application


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


def _seed_forwarding_webhook(app, slug: str = "gateway-hook") -> None:
    with app.app_context():
        models.upsert_workflow(
            workflow_id=slug,
            name="Gateway Hook",
            description="Webhook that forwards to gateway",
            workflow_type="webhook",
            status="active",
            webhook_slug=slug,
            forward_url="https://gateway.example/logs",
            slack_notify=False,
        )


class _DummyResponse:
    status_code = 202
    text = "accepted"


def test_webhook_forward_propagates_incoming_correlation_id(app, client, monkeypatch):
    """Incoming X-Correlation-ID is forwarded to downstream gateway request."""
    _seed_forwarding_webhook(app)
    captured = {}

    def _fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _DummyResponse()

    monkeypatch.setattr(views_routes.http_requests, "post", _fake_post)

    response = client.post(
        "/webhook/gateway-hook",
        json={"hello": "world"},
        headers={views_routes.CORRELATION_HEADER: "corr-123"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["correlation_id"] == "corr-123"
    assert response.headers.get(views_routes.CORRELATION_HEADER) == "corr-123"
    assert captured["headers"][views_routes.CORRELATION_HEADER] == "corr-123"
    assert captured["headers"][views_routes.REQUEST_ID_HEADER] == "corr-123"


def test_webhook_forward_generates_correlation_id_when_missing(
    app, client, monkeypatch
):
    """Webhook forwarding generates a correlation id when request is missing one."""
    _seed_forwarding_webhook(app)
    captured = {}

    def _fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _DummyResponse()

    monkeypatch.setattr(views_routes.http_requests, "post", _fake_post)

    response = client.post("/webhook/gateway-hook", json={"hello": "world"})

    assert response.status_code == 200
    body = response.get_json()
    correlation_id = body["correlation_id"]

    assert correlation_id
    assert len(correlation_id) == 32
    assert response.headers.get(views_routes.CORRELATION_HEADER) == correlation_id
    assert captured["headers"][views_routes.CORRELATION_HEADER] == correlation_id
    assert captured["headers"][views_routes.REQUEST_ID_HEADER] == correlation_id
