#!/usr/bin/env python3
"""Tests for v1 profile upsert endpoint."""

import os
import tempfile

import pytest
from flask import Flask

import database
import models
import routes.api_v1 as api_v1_routes


@pytest.fixture
def app():
    """Create isolated app + temp DB for each test."""
    if hasattr(database._thread_local, "connection"):
        database._thread_local.connection.close()
        del database._thread_local.connection

    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "test-secret-key"
    application.register_blueprint(api_v1_routes.api_v1_bp)

    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp_db.name
    tmp_db.close()

    database.set_db_path(db_path)
    with application.app_context():
        database.init_db(application)

    yield application

    if hasattr(database._thread_local, "connection"):
        database._thread_local.connection.close()
        del database._thread_local.connection

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app):
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "tester"
    return c


def test_upsert_profile_requires_auth(client):
    resp = client.post("/v1/profiles/upsert", json={"name": "Acme Inc"})
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"] == "Authentication required"


def test_upsert_profile_creates_new_profile(auth_client):
    resp = auth_client.post(
        "/v1/profiles/upsert",
        json={
            "name": "Acme Inc",
            "website": "https://acme.example",
            "industry": "Technology",
            "rules": "Be concise",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["action"] == "created"
    assert data["slug"] == "acme-inc"
    assert data["profile"]["name"] == "Acme Inc"


def test_upsert_profile_updates_existing_profile(app, auth_client):
    with app.app_context():
        models.create_client_profile(name="Acme Inc", slug="acme-inc")

    resp = auth_client.post(
        "/v1/profiles/upsert",
        json={
            "slug": "acme-inc",
            "industry": "Software",
            "website": "https://acme.example",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["action"] == "updated"
    assert data["slug"] == "acme-inc"
    assert data["profile"]["industry"] == "Software"
    assert data["profile"]["website"] == "https://acme.example"


def test_upsert_profile_rejects_invalid_payload(auth_client):
    resp = auth_client.post("/v1/profiles/upsert", json={"website": "not-a-url"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"] == "Validation failed"
    assert "website" in data["errors"]


def test_upsert_profile_writes_encrypted_setup_token(auth_client, monkeypatch):
    monkeypatch.setenv("FLASK_SECRET_KEY", "profile-upsert-token-secret")

    token = "setup-token-abc123"
    resp = auth_client.post(
        "/v1/profiles/upsert",
        json={"profile_id": "student-a", "token": token},
    )

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["action"] == "created"
    assert data["profile_id"] == "student-a"
    assert data["profile"]["profile_id"] == "student-a"
    assert data["profile"]["status"] == "active"
    assert "token" not in data["profile"]

    raw_setting = database.query_one(
        "SELECT value FROM settings WHERE key = ?",
        ("student-a.claude_setup_token",),
    )
    assert raw_setting is not None
    assert raw_setting["value"] != token
    assert raw_setting["value"].startswith("enc:v1:")

    raw_profile = database.query_one(
        "SELECT encrypted_token FROM setup_token_profiles WHERE profile_id = ?",
        ("student-a",),
    )
    assert raw_profile is not None
    assert raw_profile["encrypted_token"] != token
    assert raw_profile["encrypted_token"].startswith("enc:v1:")


def test_upsert_profile_updates_existing_setup_token(auth_client, monkeypatch):
    monkeypatch.setenv("FLASK_SECRET_KEY", "profile-upsert-token-secret")

    first = auth_client.post(
        "/v1/profiles/upsert",
        json={"profile_id": "student-b", "token": "setup-token-one"},
    )
    assert first.status_code == 201

    first_raw = database.query_one(
        "SELECT encrypted_token FROM setup_token_profiles WHERE profile_id = ?",
        ("student-b",),
    )
    assert first_raw is not None

    second = auth_client.post(
        "/v1/profiles/upsert",
        json={"profile_id": "student-b", "token": "setup-token-two"},
    )
    assert second.status_code == 200

    data = second.get_json()
    assert data["status"] == "ok"
    assert data["action"] == "updated"
    assert data["profile_id"] == "student-b"
    assert data["profile"]["status"] == "active"

    second_raw = database.query_one(
        "SELECT encrypted_token FROM setup_token_profiles WHERE profile_id = ?",
        ("student-b",),
    )
    assert second_raw is not None
    assert second_raw["encrypted_token"] != first_raw["encrypted_token"]
    assert models.get_setting("student-b.claude_setup_token") == "setup-token-two"


def test_upsert_profile_setup_token_requires_profile_id_and_token(auth_client):
    resp = auth_client.post("/v1/profiles/upsert", json={"profile_id": "student-a"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["errors"]["token"] == "token is required"
