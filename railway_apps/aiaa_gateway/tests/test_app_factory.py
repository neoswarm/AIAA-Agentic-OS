"""Tests for the AIAA Gateway app factory scaffold."""

from pathlib import Path
import sys

from flask import Flask


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aiaa_gateway import create_app
from aiaa_gateway import routes


def test_create_app_returns_flask_instance():
    app = create_app({"TESTING": True})

    assert isinstance(app, Flask)
    assert app.config["SERVICE_NAME"] == "aiaa_gateway"


def test_create_app_allows_config_override():
    app = create_app({"TESTING": True, "SERVICE_NAME": "custom_gateway"})

    assert app.config["SERVICE_NAME"] == "custom_gateway"


def test_health_endpoint_reports_not_ready_details(monkeypatch, tmp_path):
    for env_var in routes._PROFILE_STORE_KEY_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)

    monkeypatch.setenv("GATEWAY_WORKSPACE_ROOT", str(tmp_path / "missing-workspace"))
    monkeypatch.setattr(routes.shutil, "which", lambda _name: None)

    app = create_app({"TESTING": True, "SERVICE_NAME": "test_gateway"})
    client = app.test_client()

    response = client.get("/health")
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "healthy"
    assert data["service"] == "test_gateway"
    assert data["timestamp"]
    assert data["ready"] is False
    assert data["profile_store_ready"] is False
    assert data["runtime_ready"] is False
    assert data["profile_store"]["status"] == "not_ready"
    assert data["profile_store"]["missing_env_vars"] == list(
        routes._PROFILE_STORE_KEY_ENV_VARS
    )
    assert data["runtime"]["status"] == "not_ready"
    assert data["runtime"]["workspace_accessible"] is False
    assert data["runtime"]["claude_cli_available"] is False


def test_health_endpoint_reports_ready_details(monkeypatch, tmp_path):
    for relative_path in routes._RUNTIME_WORKSPACE_REQUIRED_PATHS:
        (tmp_path / relative_path).mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "x" * 32)
    monkeypatch.setenv("GATEWAY_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(
        routes.shutil,
        "which",
        lambda name: "/usr/local/bin/claude" if name == "claude" else None,
    )

    app = create_app({"TESTING": True, "SERVICE_NAME": "test_gateway"})
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
