#!/usr/bin/env python3
"""Tests for gateway profile lifecycle metric counters."""

import database
import pytest
from flask import Flask

import routes.api_v1 as api_v1_routes
import routes.api_v2 as api_v2_routes


@pytest.fixture()
def app(tmp_path):
    """Create a minimal app with isolated database."""
    db_path = tmp_path / "gateway-profile-lifecycle-metrics.db"

    existing_conn = getattr(database._thread_local, "connection", None)
    if existing_conn is not None:
        existing_conn.close()
        delattr(database._thread_local, "connection")

    database.set_db_path(str(db_path))

    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "gateway-profile-lifecycle-metrics-test"
    application.register_blueprint(api_v1_routes.api_v1_bp)
    application.register_blueprint(api_v2_routes.api_v2_bp)

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


def test_profile_lifecycle_metrics_count_success_outcomes(auth_client, monkeypatch):
    monkeypatch.setattr(
        api_v1_routes,
        "run_gateway_runtime_canary",
        lambda _token: {
            "status": "valid",
            "message": "Gateway runtime canary succeeded",
            "output": "OK",
        },
    )

    upsert_resp = auth_client.post(
        "/v1/profiles/upsert",
        json={
            "name": "Acme Inc",
            "website": "https://acme.example",
        },
    )
    assert upsert_resp.status_code == 201

    validate_resp = auth_client.post(
        "/v1/profiles/validate",
        json={"profile_id": "default", "token": "token-123"},
    )
    assert validate_resp.status_code == 200

    revoke_resp = auth_client.post(
        "/v1/profiles/revoke",
        json={"profile_slug": "acme-inc"},
    )
    assert revoke_resp.status_code == 200

    status_resp = auth_client.get("/api/v2/settings/api-keys/status")
    assert status_resp.status_code == 200
    payload = status_resp.get_json()

    lifecycle = payload["gateway_profile_lifecycle_metrics"]
    assert lifecycle["upsert"]["created"] == 1
    assert lifecycle["validate"]["valid"] == 1
    assert lifecycle["revoke"]["deleted"] + lifecycle["revoke"]["invalidated"] == 1
    assert payload["metrics"]["gateway_profile_lifecycle"] == lifecycle


def test_profile_lifecycle_metrics_count_validation_failures(auth_client):
    upsert_resp = auth_client.post("/v1/profiles/upsert", json={"website": "not-a-url"})
    assert upsert_resp.status_code == 400

    validate_resp = auth_client.post("/v1/profiles/validate", json={"token": "token-123"})
    assert validate_resp.status_code == 400

    revoke_resp = auth_client.post(
        "/v1/profiles/revoke",
        json={"profile_slug": "../escape"},
    )
    assert revoke_resp.status_code == 400

    status_resp = auth_client.get("/api/v2/settings/api-keys/status")
    assert status_resp.status_code == 200
    lifecycle = status_resp.get_json()["gateway_profile_lifecycle_metrics"]

    assert lifecycle["upsert"]["validation_failed"] == 1
    assert lifecycle["validate"]["validation_failed"] == 1
    assert lifecycle["revoke"]["validation_failed"] == 1
