#!/usr/bin/env python3
"""Tests for API token metadata fields in settings API key flows."""

from flask import Flask
import pytest

import database
import models
from routes.api_v2 import api_v2_bp


@pytest.fixture()
def app(tmp_path):
    """Create a minimal test app with API v2 routes and isolated DB."""
    db_path = tmp_path / "token-metadata.db"

    existing_conn = getattr(database._thread_local, "connection", None)
    if existing_conn is not None:
        existing_conn.close()
        delattr(database._thread_local, "connection")

    database.set_db_path(str(db_path))

    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "token-metadata-test-secret"
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
    """Authenticated test client."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "test-admin"
    return client


def test_save_api_key_persists_validation_metadata(auth_client):
    """Saving a key marks token metadata as validated and clears errors."""
    resp = auth_client.post(
        "/api/v2/settings/api-keys",
        json={"key_name": "openrouter", "key_value": "sk-or-test-1234567890"},
    )
    assert resp.status_code == 200

    metadata = models.get_setting_metadata("api_key.OPENROUTER_API_KEY")
    assert metadata["validation_status"] == "valid"
    assert metadata["last_error"] is None
    assert metadata["last_validated_at"]


def test_invalid_key_format_updates_last_error(auth_client):
    """Invalid prefix marks validation as invalid without replacing saved key value."""
    save_resp = auth_client.post(
        "/api/v2/settings/api-keys",
        json={"key_name": "openrouter", "key_value": "sk-or-test-abcdef1234"},
    )
    assert save_resp.status_code == 200

    invalid_resp = auth_client.post(
        "/api/v2/settings/api-keys",
        json={"key_name": "openrouter", "key_value": "invalid-prefix-value"},
    )
    assert invalid_resp.status_code == 400

    metadata = models.get_setting_metadata("api_key.OPENROUTER_API_KEY")
    assert metadata["validation_status"] == "invalid"
    assert "Invalid format" in (metadata["last_error"] or "")
    assert models.get_setting("api_key.OPENROUTER_API_KEY") == "sk-or-test-abcdef1234"


def test_api_key_status_returns_token_metadata(auth_client):
    """Status endpoint includes last_validated_at, validation_status, and last_error."""
    models.set_setting(
        "api_key.PERPLEXITY_API_KEY",
        "pplx-test-xyz",
        last_validated_at="2026-02-24T10:15:00",
        validation_status="invalid",
        last_error="Provider rejected token",
    )

    resp = auth_client.get("/api/v2/settings/api-keys/status")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    perplexity = data["keys"]["perplexity"]
    assert perplexity["configured"] is True
    assert perplexity["last_validated_at"] == "2026-02-24T10:15:00"
    assert perplexity["validation_status"] == "invalid"
    assert perplexity["last_error"] == "Provider rejected token"
