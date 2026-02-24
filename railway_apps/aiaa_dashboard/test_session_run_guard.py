#!/usr/bin/env python3
"""
Tests for per-session pending/running run guard behavior.
"""

import os
import hashlib

import pytest
from flask import Flask

# Ensure stable test config before importing route modules.
os.environ["FLASK_ENV"] = "testing"
os.environ["DASHBOARD_USERNAME"] = "testadmin"
os.environ["DASHBOARD_PASSWORD_HASH"] = hashlib.sha256(b"testpass123").hexdigest()
os.environ["FLASK_SECRET_KEY"] = hashlib.sha256(b"test-secret-key").hexdigest()

import routes.api_v2 as api_v2_module
import services.skill_execution_service as skill_execution_service
from config import Config
from routes.api_v2 import api_v2_bp
from services.run_guard import (
    reserve_run_slot,
    bind_run_to_reservation,
    get_active_run_count,
    reset_run_guard_state,
)


@pytest.fixture(autouse=True)
def reset_guard_state():
    """Reset in-memory run guard state between tests."""
    reset_run_guard_state()
    yield
    reset_run_guard_state()


@pytest.fixture
def app():
    """Minimal app with only API v2 routes for guard tests."""
    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "test-secret"
    application.register_blueprint(api_v2_bp)
    return application


def _login(client, username="testadmin"):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = username


def test_per_session_guard_blocks_second_pending_run(app, monkeypatch):
    """Same session cannot exceed max pending/running runs."""
    monkeypatch.setattr(Config, "MAX_PENDING_RUNNING_RUNS_PER_SESSION", 1)
    monkeypatch.setattr(api_v2_module, "parse_skill_md", lambda _: {"inputs": []})

    counter = {"value": 0}

    def fake_execute(_skill_name, _params, **_kwargs):
        counter["value"] += 1
        return f"run-{counter['value']}"

    monkeypatch.setattr(api_v2_module, "execute_skill", fake_execute)

    client = app.test_client()
    _login(client)

    first = client.post("/api/v2/skills/demo/execute", json={"params": {}})
    assert first.status_code == 202

    second = client.post("/api/v2/skills/demo/execute", json={"params": {}})
    assert second.status_code == 429

    body = second.get_json()
    assert body["status"] == "error"
    assert body["error_code"] == "session_run_limit_exceeded"
    assert body["max_pending_running_runs"] == 1
    assert second.headers.get("Retry-After") == str(body["retry_after_seconds"])


def test_per_session_guard_isolated_between_sessions(app, monkeypatch):
    """Different sessions have independent pending/running limits."""
    monkeypatch.setattr(Config, "MAX_PENDING_RUNNING_RUNS_PER_SESSION", 1)
    monkeypatch.setattr(api_v2_module, "parse_skill_md", lambda _: {"inputs": []})
    monkeypatch.setattr(
        api_v2_module,
        "execute_skill",
        lambda _skill_name, _params, **_kwargs: "run-shared",
    )

    client_a = app.test_client()
    client_b = app.test_client()
    _login(client_a, username="user-a")
    _login(client_b, username="user-b")

    resp_a = client_a.post("/api/v2/skills/demo/execute", json={"params": {}})
    resp_b = client_b.post("/api/v2/skills/demo/execute", json={"params": {}})

    assert resp_a.status_code == 202
    assert resp_b.status_code == 202


def test_execute_failure_releases_reserved_slot(app, monkeypatch):
    """Slot reservation is released when execution fails before start."""
    monkeypatch.setattr(Config, "MAX_PENDING_RUNNING_RUNS_PER_SESSION", 1)
    monkeypatch.setattr(api_v2_module, "parse_skill_md", lambda _: {"inputs": []})

    state = {"calls": 0}

    def flaky_execute(_skill_name, _params, **_kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            raise RuntimeError("boom")
        return "run-after-retry"

    monkeypatch.setattr(api_v2_module, "execute_skill", flaky_execute)

    client = app.test_client()
    _login(client)

    first = client.post("/api/v2/skills/demo/execute", json={"params": {}})
    assert first.status_code == 500

    second = client.post("/api/v2/skills/demo/execute", json={"params": {}})
    assert second.status_code == 202


def test_subprocess_completion_releases_run_slot(monkeypatch):
    """Execution lifecycle releases session slot after subprocess completion."""
    updates = []

    def fake_update_status(_execution_id, status, **_kwargs):
        updates.append(status)

    class _DummyResult:
        returncode = 0
        stdout = "Saved to .tmp/demo.md"
        stderr = ""

    monkeypatch.setattr(
        skill_execution_service.models,
        "update_skill_execution_status",
        fake_update_status,
        raising=False,
    )
    monkeypatch.setattr(
        skill_execution_service.subprocess,
        "run",
        lambda *_args, **_kwargs: _DummyResult(),
    )

    session_key = "session:test"
    reservation_id = reserve_run_slot(session_key, 1)
    assert reservation_id is not None
    assert bind_run_to_reservation(session_key, reservation_id, "run-123")
    assert get_active_run_count(session_key) == 1

    skill_execution_service._run_skill_subprocess(
        execution_id="run-123",
        cmd=["python3", "-c", "print('ok')"],
        skill_name="demo",
    )

    assert get_active_run_count(session_key) == 0
    assert updates[0] == "running"
    assert updates[-1] == "success"
