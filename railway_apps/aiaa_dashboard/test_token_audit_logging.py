#!/usr/bin/env python3
"""Tests for token audit event logging on save/rotate/revoke actions."""

from flask import Flask
import pytest

from routes.api_v2 import api_v2_bp
import routes.api_v2 as api_v2


@pytest.fixture()
def app(monkeypatch):
    """Create a minimal app with API v2 and stubbed model writes."""
    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "token-audit-test-secret"

    audit_events = []

    monkeypatch.setattr(api_v2.models, "set_setting", lambda *_args, **_kwargs: 1, raising=False)
    monkeypatch.setattr(api_v2.models, "delete_setting", lambda *_args, **_kwargs: 1, raising=False)
    monkeypatch.setattr(
        api_v2.models,
        "log_event",
        lambda event_type, status, data, source="system": audit_events.append(
            {
                "event_type": event_type,
                "status": status,
                "data": data,
                "source": source,
            }
        ),
        raising=False,
    )

    application.register_blueprint(api_v2_bp)
    application.config["AUDIT_EVENTS"] = audit_events
    return application


@pytest.fixture()
def auth_client(app):
    """Authenticated dashboard client."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testadmin"
    return client


def test_save_token_logs_audit_event(auth_client, app):
    """Saving a token emits a success audit event."""
    response = auth_client.post(
        "/api/v2/settings/api-keys",
        json={"key_name": "openrouter", "key_value": "sk-or-test-1234567890abcdef"},
    )

    assert response.status_code == 200
    event = app.config["AUDIT_EVENTS"][-1]
    assert event["event_type"] == "token"
    assert event["status"] == "success"
    assert event["source"] == "api"
    assert event["data"]["action"] == "save"
    assert event["data"]["key_name"] == "OPENROUTER_API_KEY"


def test_rotate_token_logs_audit_event_without_raw_tokens(auth_client, app, monkeypatch):
    """Rotating a token emits an audit event and does not log raw token values."""
    old_token = "old-token-123456"
    new_token = "new-token-abcdef"
    monkeypatch.setenv("DASHBOARD_API_KEY", old_token)

    response = auth_client.post(
        "/api/v2/settings/auth-token/rotate",
        json={"current_token": old_token, "new_token": new_token},
    )

    assert response.status_code == 200
    event = app.config["AUDIT_EVENTS"][-1]
    assert event["event_type"] == "token"
    assert event["status"] == "success"
    assert event["data"]["action"] == "rotate"
    assert event["data"]["key_name"] == "DASHBOARD_API_KEY"
    assert old_token not in str(event["data"])
    assert new_token not in str(event["data"])


def test_revoke_token_logs_audit_event(auth_client, app, monkeypatch):
    """Revoking a token emits a success audit event."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-secret-value")

    response = auth_client.post(
        "/api/v2/settings/api-keys/revoke",
        json={"key_name": "openrouter"},
    )

    assert response.status_code == 200
    event = app.config["AUDIT_EVENTS"][-1]
    assert event["event_type"] == "token"
    assert event["status"] == "success"
    assert event["data"]["action"] == "revoke"
    assert event["data"]["key_name"] == "OPENROUTER_API_KEY"
