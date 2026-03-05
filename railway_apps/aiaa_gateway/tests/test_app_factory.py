"""Tests for the AIAA Gateway app factory scaffold."""

from datetime import datetime
from pathlib import Path
import sys

from flask import Flask
import pytest


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aiaa_gateway import create_app
from aiaa_gateway import routes


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


def test_health_endpoint_reports_not_ready_details(monkeypatch, tmp_path):
    monkeypatch.setenv("GATEWAY_WORKSPACE_ROOT", str(tmp_path / "missing-workspace"))
    monkeypatch.setattr(routes.shutil, "which", lambda _name: None)

    app = _create_test_app({"SERVICE_NAME": "test_gateway"})
    for env_var in routes._PROFILE_STORE_KEY_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)
    client = app.test_client()

    response = client.get("/health")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "healthy"
    assert payload["service"] == "test_gateway"
    assert payload["timestamp"]
    assert payload["ready"] is False
    assert payload["profile_store_ready"] is False
    assert payload["runtime_ready"] is False
    assert payload["profile_store"]["status"] == "not_ready"
    assert payload["profile_store"]["missing_env_vars"] == list(
        routes._PROFILE_STORE_KEY_ENV_VARS
    )
    assert payload["runtime"]["status"] == "not_ready"
    assert payload["runtime"]["workspace_accessible"] is False
    assert payload["runtime"]["claude_cli_available"] is False


def test_health_endpoint_emits_iso8601_utc_timestamp():
    app = _create_test_app()
    client = app.test_client()

    response = client.get("/health")
    payload = response.get_json()

    assert response.status_code == 200
    timestamp = payload["timestamp"]
    parsed = datetime.fromisoformat(timestamp)
    assert parsed.tzinfo is not None


def test_health_endpoint_reports_ready_details(monkeypatch, tmp_path):
    for relative_path in routes._RUNTIME_WORKSPACE_REQUIRED_PATHS:
        target = tmp_path / relative_path
        if target.suffix:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok", encoding="utf-8")
        else:
            target.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "x" * 32)
    monkeypatch.setenv("GATEWAY_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(
        routes.shutil,
        "which",
        lambda name: "/usr/local/bin/claude" if name == "claude" else None,
    )

    app = _create_test_app({"SERVICE_NAME": "test_gateway"})
    client = app.test_client()

    response = client.get("/health")
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "healthy"
    assert data["service"] == "test_gateway"
    assert data["timestamp"]
    assert data["ready"] is True
    assert data["profile_store_ready"] is True
    assert data["runtime_ready"] is True
    assert data["profile_store"]["status"] == "ready"
    assert (
        data["profile_store"]["encryption_key_source"]
        == "CHAT_TOKEN_ENCRYPTION_KEY"
    )
    assert data["profile_store"]["missing_env_vars"] == []
    assert data["runtime"]["status"] == "ready"
    assert data["runtime"]["workspace_accessible"] is True
    assert data["runtime"]["claude_cli_available"] is True
    assert data["runtime"]["missing_workspace_paths"] == []


def test_health_endpoint_uses_factory_config():
    app = _create_test_app({"SERVICE_NAME": "test_gateway"})
    client = app.test_client()

    response = client.get("/health")
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "healthy"
    assert data["service"] == "test_gateway"
    assert data["timestamp"]


def test_create_app_allows_missing_anthropic_secret_with_warning(caplog):
    caplog.set_level("WARNING")

    app = create_app({"TESTING": True, "ANTHROPIC_API_KEY": "   "})

    assert isinstance(app, Flask)
    assert any(
        "ANTHROPIC_API_KEY is not configured" in record.getMessage()
        for record in caplog.records
    )


def test_create_app_raises_when_encryption_key_missing(monkeypatch):
    monkeypatch.delenv("CHAT_TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="Missing encryption key"):
        create_app({"TESTING": True, "ANTHROPIC_API_KEY": "test-anthropic-key"})
