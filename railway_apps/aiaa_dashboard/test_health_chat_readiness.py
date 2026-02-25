#!/usr/bin/env python3
"""Health endpoint tests for chat subsystem readiness metadata."""

import sys
from pathlib import Path

import pytest
from flask import Flask

# Allow importing app modules from railway_apps/aiaa_dashboard
sys.path.insert(0, str(Path(__file__).parent))

import database
from routes.api import api_bp
from routes.views import views_bp


_CHAT_ENV_KEYS = (
    "CHAT_BACKEND",
    "GATEWAY_BASE_URL",
    "GATEWAY_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "PERPLEXITY_API_KEY",
)


@pytest.fixture()
def client(tmp_path):
    """Minimal Flask app with API + views blueprints for endpoint testing."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"

    database.set_db_path(str(tmp_path / "dashboard.db"))
    with app.app_context():
        database.init_db(app)

    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)

    return app.test_client()


def _clear_chat_env(monkeypatch):
    for key in _CHAT_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_api_health_includes_chat_readiness_fields(client, monkeypatch):
    _clear_chat_env(monkeypatch)

    response = client.get("/api/health")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["chat_subsystem_ready"] is False
    assert payload["chat_subsystem"]["ready"] is False
    assert payload["chat_subsystem"]["status"] == "not_ready"
    assert payload["chat_subsystem"]["providers"] == []


def test_api_health_reports_ready_when_provider_configured(client, monkeypatch):
    _clear_chat_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-ready")

    response = client.get("/api/health")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["chat_subsystem_ready"] is True
    assert payload["chat_subsystem"]["ready"] is True
    assert payload["chat_subsystem"]["status"] == "ready"
    assert "openrouter" in payload["chat_subsystem"]["providers"]


def test_views_health_includes_chat_readiness(client, monkeypatch):
    _clear_chat_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-ready")

    response = client.get("/health")
    assert response.status_code == 200

    payload = response.get_json()
    assert "chat_subsystem_ready" in payload
    assert "chat_subsystem" in payload
    assert payload["chat_subsystem_ready"] is True
    assert payload["chat_subsystem"]["ready"] is True
    assert "openai" in payload["chat_subsystem"]["providers"]


def test_api_health_gateway_backend_requires_gateway_env_vars(client, monkeypatch):
    _clear_chat_env(monkeypatch)
    monkeypatch.setenv("CHAT_BACKEND", "gateway")

    response = client.get("/api/health")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["chat_subsystem_ready"] is False
    assert payload["chat_subsystem"]["backend"] == "gateway"
    assert payload["chat_subsystem"]["missing_env_vars"] == [
        "GATEWAY_BASE_URL",
        "GATEWAY_API_KEY",
    ]


def test_api_health_gateway_backend_reports_ready_with_gateway_env_vars(client, monkeypatch):
    _clear_chat_env(monkeypatch)
    monkeypatch.setenv("CHAT_BACKEND", "gateway")
    monkeypatch.setenv("GATEWAY_BASE_URL", "https://gateway.example.test")
    monkeypatch.setenv("GATEWAY_API_KEY", "gateway-test-key")

    response = client.get("/api/health")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["chat_subsystem_ready"] is True
    assert payload["chat_subsystem"]["backend"] == "gateway"
    assert payload["chat_subsystem"]["providers"] == ["gateway"]
    assert payload["chat_subsystem"]["missing_env_vars"] == []
