#!/usr/bin/env python3
"""Tests for API v2 gateway readiness health endpoint."""

import sys
from pathlib import Path

import pytest
from flask import Flask


sys.path.insert(0, str(Path(__file__).parent.parent))
from routes.api_v2 import api_v2_bp


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
def client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(api_v2_bp)
    return app.test_client()


def _clear_chat_env(monkeypatch):
    for key in _CHAT_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_api_v2_health_includes_readiness_contract(client, monkeypatch):
    _clear_chat_env(monkeypatch)

    response = client.get("/api/v2/health")
    assert response.status_code == 200

    payload = response.get_json()
    assert set(payload) == {
        "status",
        "ready",
        "timestamp",
        "service",
        "chat_subsystem_ready",
        "chat_subsystem",
    }
    assert payload["status"] == "ok"
    assert payload["service"] == "aiaa-dashboard-gateway"
    assert isinstance(payload["timestamp"], str)
    assert payload["ready"] is False
    assert payload["chat_subsystem_ready"] is False
    assert payload["ready"] is payload["chat_subsystem_ready"]

    chat_subsystem = payload["chat_subsystem"]
    assert set(chat_subsystem) == {
        "ready",
        "status",
        "backend",
        "providers",
        "missing_providers",
        "missing_env_vars",
    }
    assert chat_subsystem["ready"] is False
    assert chat_subsystem["status"] == "not_ready"
    assert chat_subsystem["backend"] == "provider"
    assert chat_subsystem["providers"] == []
    assert chat_subsystem["missing_providers"] == [
        "openrouter",
        "openai",
        "anthropic",
        "perplexity",
    ]
    assert chat_subsystem["missing_env_vars"] == []


def test_api_v2_health_reports_ready_when_provider_configured(client, monkeypatch):
    _clear_chat_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-ready")

    response = client.get("/api/v2/health")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["ready"] is True
    assert payload["chat_subsystem_ready"] is True
    assert payload["ready"] is payload["chat_subsystem_ready"]

    chat_subsystem = payload["chat_subsystem"]
    assert chat_subsystem["ready"] is True
    assert chat_subsystem["status"] == "ready"
    assert chat_subsystem["backend"] == "provider"
    assert chat_subsystem["providers"] == ["openrouter"]
    assert chat_subsystem["missing_providers"] == ["openai", "anthropic", "perplexity"]
    assert chat_subsystem["missing_env_vars"] == []


def test_api_v2_health_gateway_backend_reports_missing_gateway_env_vars(
    client, monkeypatch
):
    _clear_chat_env(monkeypatch)
    monkeypatch.setenv("CHAT_BACKEND", "gateway")

    response = client.get("/api/v2/health")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["ready"] is False
    assert payload["chat_subsystem_ready"] is False
    assert payload["chat_subsystem"]["backend"] == "gateway"
    assert payload["chat_subsystem"]["providers"] == []
    assert payload["chat_subsystem"]["missing_providers"] == ["gateway"]
    assert payload["chat_subsystem"]["missing_env_vars"] == [
        "GATEWAY_BASE_URL",
        "GATEWAY_API_KEY",
    ]


def test_api_v2_health_gateway_backend_reports_ready_when_env_vars_set(
    client, monkeypatch
):
    _clear_chat_env(monkeypatch)
    monkeypatch.setenv("CHAT_BACKEND", "gateway")
    monkeypatch.setenv("GATEWAY_BASE_URL", "https://gateway.example.test")
    monkeypatch.setenv("GATEWAY_API_KEY", "gateway-test-key")

    response = client.get("/api/v2/health")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["ready"] is True
    assert payload["chat_subsystem_ready"] is True
    assert payload["chat_subsystem"]["backend"] == "gateway"
    assert payload["chat_subsystem"]["providers"] == ["gateway"]
    assert payload["chat_subsystem"]["missing_providers"] == []
    assert payload["chat_subsystem"]["missing_env_vars"] == []
