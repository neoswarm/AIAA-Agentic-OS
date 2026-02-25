#!/usr/bin/env python3
"""Tests for POST /v1/profiles/revoke."""

from flask import Flask
import pytest

from routes.api_v2 import api_v1_bp
import routes.api_v2 as api_v2


@pytest.fixture
def app(monkeypatch):
    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "test-secret"

    revoke_markers = []

    def fake_set_setting(setting_key, setting_value, *args, **kwargs):
        revoke_markers.append((setting_key, setting_value))
        return 1

    monkeypatch.setattr(api_v2.models, "set_setting", fake_set_setting, raising=False)
    monkeypatch.setattr(
        api_v2.models,
        "delete_client_profile",
        lambda _slug: 0,
        raising=False,
    )

    application.register_blueprint(api_v1_bp)
    application.config["REVOKE_MARKERS"] = revoke_markers
    return application


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


def test_revoke_profile_requires_auth(client):
    resp = client.post("/v1/profiles/revoke", json={"profile_slug": "acme"})
    assert resp.status_code == 401


def test_revoke_profile_secure_deletes_when_available(auth_client, app, monkeypatch):
    deleted = []

    def fake_delete_client_profile(profile_slug):
        deleted.append(profile_slug)
        return 1

    monkeypatch.setattr(
        api_v2.models,
        "delete_client_profile",
        fake_delete_client_profile,
        raising=False,
    )

    resp = auth_client.post("/v1/profiles/revoke", json={"profile_slug": "acme"})
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["profile_slug"] == "acme"
    assert data["action"] == "deleted"
    assert deleted == ["acme"]
    assert app.config["REVOKE_MARKERS"][-1][0] == "profile_revoked.acme"


def test_revoke_profile_invalidates_when_delete_does_not_remove(auth_client, app):
    resp = auth_client.post("/v1/profiles/revoke", json={"profile_slug": "missing"})
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["profile_slug"] == "missing"
    assert data["action"] == "invalidated"
    assert app.config["REVOKE_MARKERS"][-1][0] == "profile_revoked.missing"


def test_revoke_profile_rejects_invalid_slug(auth_client):
    resp = auth_client.post("/v1/profiles/revoke", json={"profile_slug": "../escape"})
    assert resp.status_code == 400

    data = resp.get_json()
    assert data["status"] == "error"
    assert data["errors"]["profile"] == "Invalid profile slug"


def test_revoked_profiles_are_not_resolvable(monkeypatch):
    monkeypatch.setattr(
        api_v2.models,
        "get_setting",
        lambda key: "2026-02-25T00:00:00Z" if key == "profile_revoked.acme" else None,
        raising=False,
    )
    monkeypatch.setattr(
        api_v2.models,
        "get_client_profile",
        lambda slug: {"slug": slug},
        raising=False,
    )

    assert api_v2._is_known_client_profile("acme") is False
