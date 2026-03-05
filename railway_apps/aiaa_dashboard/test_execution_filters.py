#!/usr/bin/env python3
"""Execution listing filter tests (status/date/search)."""

import json
import os
from pathlib import Path

import pytest
from flask import Flask

import database
from routes.api_v2 import api_v2_bp


def _reset_db_connection():
    """Close thread-local connection so tests can use an isolated DB file."""
    conn = getattr(database._thread_local, "connection", None)
    if conn is not None:
        conn.close()
        delattr(database._thread_local, "connection")


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    db_dir = tmp_path_factory.mktemp("db")
    db_path = db_dir / "filters.db"

    _reset_db_connection()
    database.set_db_path(str(db_path))

    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "test-secret"
    application.register_blueprint(api_v2_bp)

    with application.app_context():
        database.init_db(application)
        database.execute(
            """
            INSERT INTO executions (
                workflow_id, workflow_name, trigger_type, status,
                started_at, completed_at, duration_ms,
                error_message, output_summary, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                None,
                "blog-post",
                "manual",
                "success",
                "2026-02-10 09:00:00",
                "2026-02-10 09:00:45",
                45000,
                None,
                "Generated blog draft",
                json.dumps({"source": "test"}),
            ),
        )
        database.execute(
            """
            INSERT INTO executions (
                workflow_id, workflow_name, trigger_type, status,
                started_at, completed_at, duration_ms,
                error_message, output_summary, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                None,
                "email-sequence",
                "api",
                "error",
                "2026-02-12 11:15:00",
                "2026-02-12 11:15:20",
                20000,
                "OpenRouter timeout",
                None,
                json.dumps({"source": "test"}),
            ),
        )
        database.execute(
            """
            INSERT INTO executions (
                workflow_id, workflow_name, trigger_type, status,
                started_at, completed_at, duration_ms,
                error_message, output_summary, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                None,
                "market-research",
                "manual",
                "success",
                "2026-02-15 14:30:00",
                "2026-02-15 14:31:00",
                60000,
                None,
                "AI market report generated",
                json.dumps({"source": "test"}),
            ),
        )

    yield application

    _reset_db_connection()
    if Path(db_path).exists():
        os.unlink(db_path)


@pytest.fixture(scope="module")
def auth_client(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session["logged_in"] = True
        session["username"] = "tester"
    return client


def test_execution_filter_by_status(auth_client):
    resp = auth_client.get("/api/v2/executions?status=error")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["total"] == 1
    assert data["executions"][0]["skill_name"] == "email-sequence"
    assert data["executions"][0]["status"] == "error"


def test_execution_filter_by_date_range(auth_client):
    resp = auth_client.get("/api/v2/executions?date_from=2026-02-11&date_to=2026-02-13")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["total"] == 1
    assert data["executions"][0]["skill_name"] == "email-sequence"


def test_execution_filter_by_search(auth_client):
    resp = auth_client.get("/api/v2/executions?search=report")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["total"] == 1
    assert data["executions"][0]["skill_name"] == "market-research"


def test_execution_filter_by_q_alias(auth_client):
    resp = auth_client.get("/api/v2/executions?q=timeout")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["total"] == 1
    assert data["executions"][0]["skill_name"] == "email-sequence"


def test_execution_filter_combined(auth_client):
    resp = auth_client.get("/api/v2/executions?status=success&search=blog&date_to=2026-02-10")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["total"] == 1
    assert data["executions"][0]["skill_name"] == "blog-post"
