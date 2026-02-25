#!/usr/bin/env python3
"""Tests for API v2 client profile validation in skill execution."""

from flask import Flask
import pytest

from routes.api_v2 import api_v2_bp
import routes.api_v2 as api_v2_routes


@pytest.fixture
def auth_client():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(api_v2_bp)

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "tester"
    return client


def test_execute_skill_rejects_unknown_client_profile(auth_client, monkeypatch):
    monkeypatch.setattr(api_v2_routes, "parse_skill_md", lambda _: {"inputs": []})
    monkeypatch.setattr(api_v2_routes.models, "get_client_profile", lambda _: None, raising=False)

    def _should_not_execute(*_args, **_kwargs):
        raise AssertionError("execute_skill should not run for unknown profiles")

    monkeypatch.setattr(api_v2_routes, "execute_skill", _should_not_execute)

    resp = auth_client.post(
        "/api/v2/skills/blog-post/execute",
        json={"client": "missing-profile"},
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"] == "Invalid client profile"
    assert data["errors"]["client"] == "Unknown profile: missing-profile"


def test_execute_skill_allows_known_client_profile(auth_client, monkeypatch):
    monkeypatch.setattr(api_v2_routes, "parse_skill_md", lambda _: {"inputs": []})
    monkeypatch.setattr(
        api_v2_routes.models,
        "get_client_profile",
        lambda slug: {"slug": slug} if slug == "acme" else None,
        raising=False,
    )
    monkeypatch.setattr(api_v2_routes, "execute_skill", lambda _skill, _params: "exec-123")

    resp = auth_client.post(
        "/api/v2/skills/blog-post/execute",
        json={"client": "acme"},
    )

    assert resp.status_code == 202
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["execution_id"] == "exec-123"
