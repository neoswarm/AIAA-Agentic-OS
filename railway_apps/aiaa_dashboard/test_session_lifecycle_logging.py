#!/usr/bin/env python3
"""
Tests for structured session lifecycle logging.
"""

import hashlib
import json
import logging
from pathlib import Path

import pytest
from flask import Flask

import routes.views as views


@pytest.fixture
def app(monkeypatch):
    """Minimal app for testing view auth routes and logging."""
    application = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
    )
    application.config["TESTING"] = True
    application.config["SESSION_COOKIE_SECURE"] = False
    application.secret_key = "test-secret"

    monkeypatch.setattr(views.Config, "DASHBOARD_USERNAME", "testadmin")
    monkeypatch.setattr(
        views.Config,
        "DASHBOARD_PASSWORD_HASH",
        hashlib.sha256(b"testpass123").hexdigest(),
    )
    monkeypatch.setattr(views.models, "log_event", lambda *args, **kwargs: 1)

    application.register_blueprint(views.views_bp)
    return application


def _session_lifecycle_payloads(caplog):
    """Extract session lifecycle JSON payloads from captured records."""
    payloads = []
    for record in caplog.records:
        try:
            payload = json.loads(record.getMessage())
        except (TypeError, json.JSONDecodeError):
            continue
        if payload.get("event") == "session_lifecycle":
            payloads.append(payload)
    return payloads


def test_login_success_emits_structured_session_log(app, caplog):
    test_client = app.test_client()
    caplog.set_level(logging.INFO, logger="routes.views")
    caplog.clear()

    resp = test_client.post(
        "/login",
        data={"username": "testadmin", "password": "testpass123"},
        follow_redirects=False,
    )

    assert resp.status_code == 302
    payloads = _session_lifecycle_payloads(caplog)
    assert any(
        payload.get("action") == "login"
        and payload.get("status") == "success"
        and payload.get("username") == "testadmin"
        and payload.get("path") == "/login"
        and payload.get("method") == "POST"
        for payload in payloads
    )


def test_login_failure_emits_structured_session_log(app, caplog):
    test_client = app.test_client()
    caplog.set_level(logging.INFO, logger="routes.views")
    caplog.clear()

    resp = test_client.post(
        "/login",
        data={"username": "testadmin", "password": "wrong-password"},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    payloads = _session_lifecycle_payloads(caplog)
    assert any(
        payload.get("action") == "login"
        and payload.get("status") == "error"
        and payload.get("username") == "testadmin"
        and payload.get("path") == "/login"
        and payload.get("method") == "POST"
        for payload in payloads
    )


def test_logout_emits_structured_session_log(app, caplog):
    test_client = app.test_client()
    with test_client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testadmin"

    caplog.set_level(logging.INFO, logger="routes.views")
    caplog.clear()

    resp = test_client.get("/logout", follow_redirects=False)

    assert resp.status_code == 302
    payloads = _session_lifecycle_payloads(caplog)
    assert any(
        payload.get("action") == "logout"
        and payload.get("status") == "success"
        and payload.get("username") == "testadmin"
        and payload.get("path") == "/logout"
        and payload.get("method") == "GET"
        for payload in payloads
    )


def test_missing_session_redirect_emits_structured_session_log(app, caplog):
    test_client = app.test_client()
    caplog.set_level(logging.INFO, logger="routes.views")
    caplog.clear()

    resp = test_client.get("/workflows", follow_redirects=False)

    assert resp.status_code == 302
    payloads = _session_lifecycle_payloads(caplog)
    assert any(
        payload.get("action") == "missing_session"
        and payload.get("status") == "redirected"
        and payload.get("path") == "/workflows"
        and payload.get("method") == "GET"
        for payload in payloads
    )
