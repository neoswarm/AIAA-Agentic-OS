#!/usr/bin/env python3
"""Tests for session-scoped override behavior on login/session creation."""

import hashlib

import pytest
from flask import Flask

from config import Config
import routes.views as views_module
from routes.views import views_bp


@pytest.fixture()
def client(monkeypatch):
    """Create a lightweight app client for login route testing."""
    monkeypatch.setattr(Config, "DASHBOARD_USERNAME", "testadmin")
    monkeypatch.setattr(
        Config,
        "DASHBOARD_PASSWORD_HASH",
        hashlib.sha256(b"testpass123").hexdigest(),
    )
    monkeypatch.setattr(views_module.models, "log_event", lambda *args, **kwargs: 1)

    app = Flask(__name__)
    app.secret_key = "test-secret-key"
    app.config["TESTING"] = True
    app.register_blueprint(views_bp)
    return app.test_client()


def test_login_sets_chat_profile_override_on_new_session(client):
    """POST /login stores chat_profile_override when provided."""
    resp = client.post(
        "/login",
        data={
            "username": "testadmin",
            "password": "testpass123",
            "chat_profile_override": "safe",
        },
        follow_redirects=False,
    )

    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess.get("logged_in") is True
        assert sess.get("chat_profile_override") == "safe"


def test_login_clears_chat_profile_override_when_not_provided(client):
    """POST /login removes chat_profile_override if omitted/empty."""
    with client.session_transaction() as sess:
        sess["chat_profile_override"] = "full"

    resp = client.post(
        "/login",
        data={
            "username": "testadmin",
            "password": "testpass123",
        },
        follow_redirects=False,
    )

    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert "chat_profile_override" not in sess
