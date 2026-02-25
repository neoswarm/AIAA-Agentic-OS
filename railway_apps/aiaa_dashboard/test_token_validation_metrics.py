#!/usr/bin/env python3
"""Tests for token validation status metric counters."""

import database
import pytest
import routes.api_v2 as api_v2_module
from flask import Flask
from routes.api_v2 import _API_KEY_NAMES, api_v2_bp


@pytest.fixture()
def app(tmp_path):
    """Create a minimal app with isolated database."""
    db_path = tmp_path / "token-validation-metrics.db"

    existing_conn = getattr(database._thread_local, "connection", None)
    if existing_conn is not None:
        existing_conn.close()
        delattr(database._thread_local, "connection")

    database.set_db_path(str(db_path))

    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "token-validation-metrics-test"
    application.register_blueprint(api_v2_bp)

    with application.app_context():
        database.init_db(application)

    yield application

    conn = getattr(database._thread_local, "connection", None)
    if conn is not None:
        conn.close()
        delattr(database._thread_local, "connection")


@pytest.fixture()
def auth_client(app):
    """Authenticated client."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "metrics-test-admin"
    return client


def _clear_api_key_env(monkeypatch):
    for env_var in _API_KEY_NAMES.values():
        monkeypatch.delenv(env_var, raising=False)


def test_token_validation_metrics_by_status(auth_client, monkeypatch):
    """Status endpoint returns counters for valid/expired/invalid/unreachable."""
    _clear_api_key_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-valid-token")
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-expired-token")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-invalid-token")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/unreachable-token")

    metadata_by_key = {
        "api_key.OPENROUTER_API_KEY": {"validation_status": "valid"},
        "api_key.PERPLEXITY_API_KEY": {"validation_status": "expired"},
        "api_key.OPENAI_API_KEY": {"validation_status": "invalid"},
        "api_key.SLACK_WEBHOOK_URL": {"validation_status": "unreachable"},
    }

    monkeypatch.setattr(api_v2_module.models, "get_setting", lambda _key: "", raising=False)
    monkeypatch.setattr(
        api_v2_module.models,
        "get_setting_metadata",
        lambda key: metadata_by_key.get(key, {}),
        raising=False,
    )

    resp = auth_client.get("/api/v2/settings/api-keys/status")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["token_validation_metrics"] == {
        "valid": 1,
        "expired": 1,
        "invalid": 1,
        "unreachable": 1,
    }
    assert data["metrics"]["token_validation_by_status"] == data["token_validation_metrics"]


def test_configured_key_without_metadata_counts_as_valid(auth_client, monkeypatch):
    """Configured keys without metadata default to valid for counter compatibility."""
    _clear_api_key_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-fallback-token")

    monkeypatch.setattr(api_v2_module.models, "get_setting", lambda _key: "", raising=False)
    monkeypatch.setattr(api_v2_module.models, "get_setting_metadata", lambda _key: {}, raising=False)

    resp = auth_client.get("/api/v2/settings/api-keys/status")
    assert resp.status_code == 200

    metrics = resp.get_json()["token_validation_metrics"]
    assert metrics["valid"] == 1
    assert metrics["expired"] == 0
    assert metrics["invalid"] == 0
    assert metrics["unreachable"] == 0


def test_status_metrics_include_stream_and_runtime_error_counters(auth_client, monkeypatch):
    """Status endpoint includes stream failure + runtime error counters."""
    _clear_api_key_env(monkeypatch)

    monkeypatch.setattr(api_v2_module.models, "get_setting", lambda _key: "", raising=False)
    monkeypatch.setattr(api_v2_module.models, "get_setting_metadata", lambda _key: {}, raising=False)
    monkeypatch.setattr(
        api_v2_module,
        "_list_chat_sessions_for_metrics",
        lambda: [
            {
                "id": "stream-failed-session",
                "status": "error",
                "last_error": "SSE stream disconnected by client",
            },
            {
                "id": "runtime-error-session",
                "status": "error",
                "last_error": "RuntimeError: failed to execute tool",
            },
            {
                "id": "healthy-session",
                "status": "idle",
                "last_error": "",
            },
        ],
        raising=False,
    )

    resp = auth_client.get("/api/v2/settings/api-keys/status")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["stream_failure_count"] == 1
    assert data["runtime_error_count"] == 2
    assert data["metrics"]["stream_failures"] == 1
    assert data["metrics"]["runtime_errors"] == 2
