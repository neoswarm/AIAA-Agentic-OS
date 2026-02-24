#!/usr/bin/env python3
"""Tests for API v2 limit validation error responses."""

import sys
from pathlib import Path

import pytest
from flask import Flask


sys.path.insert(0, str(Path(__file__).parent.parent))
from routes.api_v2 import api_v2_bp
import routes.api_v2 as api_v2


@pytest.fixture
def client(monkeypatch):
    """Create a lightweight Flask test client with API v2 routes."""
    monkeypatch.setenv("DASHBOARD_API_KEY", "test-key")

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(api_v2_bp)

    return app.test_client()


def test_recommended_limit_above_max_returns_retry_guidance(client):
    """Over-limit values should return a clear 400 error with retry guidance."""
    resp = client.get("/api/v2/skills/recommended?role=marketing&limit=999")

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "limit" in data["errors"]
    assert "retry" in data["message"].lower()
    assert "retry" in data["retry_guidance"].lower()


def test_recommended_limit_non_integer_returns_retry_guidance(client):
    """Non-integer limits should return a clear 400 error with retry guidance."""
    resp = client.get("/api/v2/skills/recommended?role=marketing&limit=abc")

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "limit" in data["errors"]
    assert "retry" in data["message"].lower()
    assert "retry" in data["retry_guidance"].lower()


def test_executions_limit_violation_returns_retry_guidance(client, monkeypatch):
    """Executions endpoint should reject over-limit values before DB access."""

    def fail_if_called(*args, **kwargs):  # pragma: no cover - defensive guard
        raise AssertionError("models.get_skill_executions should not be called")

    monkeypatch.setattr(api_v2.models, "get_skill_executions", fail_if_called, raising=False)

    resp = client.get(
        "/api/v2/executions?limit=999",
        headers={"X-API-Key": "test-key"},
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "limit" in data["errors"]
    assert "retry" in data["message"].lower()
    assert "retry" in data["retry_guidance"].lower()
