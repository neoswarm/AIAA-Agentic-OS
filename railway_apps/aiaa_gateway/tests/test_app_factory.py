"""Tests for the AIAA Gateway app factory scaffold."""

from pathlib import Path
import sys

from flask import Flask
import pytest


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aiaa_gateway import create_app


@pytest.fixture(autouse=True)
def _set_required_encryption_key(monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "gateway-startup-test-key")


def _create_test_app(test_config: dict | None = None):
    config = {
        "TESTING": True,
        "ANTHROPIC_API_KEY": "test-anthropic-key",
    }
    if test_config:
        config.update(test_config)
    return create_app(config)


def test_create_app_returns_flask_instance():
    app = _create_test_app()

    assert isinstance(app, Flask)
    assert app.config["SERVICE_NAME"] == "aiaa_gateway"


def test_create_app_allows_config_override():
    app = _create_test_app({"SERVICE_NAME": "custom_gateway"})

    assert app.config["SERVICE_NAME"] == "custom_gateway"


def test_health_endpoint_uses_factory_config():
    app = _create_test_app({"SERVICE_NAME": "test_gateway"})
    client = app.test_client()

    response = client.get("/health")
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "healthy"
    assert data["service"] == "test_gateway"
    assert data["timestamp"]


def test_create_app_raises_when_anthropic_secret_missing():
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        create_app({"TESTING": True, "ANTHROPIC_API_KEY": "   "})


def test_create_app_raises_when_encryption_key_missing(monkeypatch):
    monkeypatch.delenv("CHAT_TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="Missing encryption key"):
        create_app({"TESTING": True, "ANTHROPIC_API_KEY": "test-anthropic-key"})
