"""Tests for POST /v1/profiles/validate."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aiaa_gateway import create_app
from aiaa_gateway import routes
from aiaa_gateway.services.profile_service import encrypt_token_for_storage


@pytest.fixture(autouse=True)
def _set_required_encryption_key(monkeypatch, tmp_path):
    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "gateway-startup-test-key")
    monkeypatch.setenv("GATEWAY_PROFILE_DB_PATH", str(tmp_path / "gateway_profiles.db"))


def _auth_headers(token: str = "gateway-internal-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _make_client(profile_store=None, *, gateway_token: str = "gateway-internal-token"):
    app = create_app(
        {
            "TESTING": True,
            "GATEWAY_INTERNAL_TOKEN": gateway_token,
            "PROFILE_TOKEN_STORE": profile_store or {},
            "GATEWAY_RUNTIME_CANARY_TIMEOUT_SECONDS": 4,
        }
    )
    return app.test_client()


def test_post_v1_profiles_validate_requires_profile_id():
    client = _make_client()

    response = client.post("/v1/profiles/validate", json={}, headers=_auth_headers())

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["type"] == "invalid_request_error"
    assert body["error"]["details"]["profile_id"] == "profile_id is required"


def test_post_v1_profiles_validate_uses_stored_profile_token(monkeypatch):
    client = _make_client(profile_store={"default": {"token": "stored-token"}})
    captured = {}

    def fake_canary(token: str, *, timeout_seconds=None):
        captured["token"] = token
        captured["timeout_seconds"] = timeout_seconds
        return {
            "status": "valid",
            "message": "Gateway runtime canary succeeded",
            "output": "OK",
        }

    monkeypatch.setattr(routes, "run_gateway_runtime_canary", fake_canary)

    response = client.post(
        "/v1/profiles/validate",
        json={"profile_id": "default", "token": "request-token-should-be-ignored"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["profile_id"] == "default"
    assert body["validation"] == "valid"
    assert captured["token"] == "stored-token"
    assert captured["timeout_seconds"] == 4


def test_post_v1_profiles_validate_supports_encrypted_stored_token(monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "gateway-profile-token-secret")
    encrypted = encrypt_token_for_storage("stored-token")
    client = _make_client(profile_store={"default": {"encrypted_token": encrypted}})
    captured = {}

    def fake_canary(token: str, *, timeout_seconds=None):
        captured["token"] = token
        return {"status": "valid", "message": "ok"}

    monkeypatch.setattr(routes, "run_gateway_runtime_canary", fake_canary)

    response = client.post(
        "/v1/profiles/validate",
        json={"profile_id": "default"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert captured["token"] == "stored-token"


def test_post_v1_profiles_validate_returns_error_when_token_missing():
    client = _make_client(profile_store={})

    response = client.post(
        "/v1/profiles/validate",
        json={"profile_id": "default"},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["type"] == "invalid_request_error"
    assert body["error"]["details"]["token"] == "No token configured for profile: default"


def test_post_v1_profiles_validate_maps_runtime_failures_to_unreachable(monkeypatch):
    client = _make_client(profile_store={"default": "stored-token"})

    monkeypatch.setattr(
        routes,
        "run_gateway_runtime_canary",
        lambda token, *, timeout_seconds=None: {
            "status": "runtime_unavailable",
            "message": "Claude runtime is not installed on this host",
        },
    )

    response = client.post(
        "/v1/profiles/validate",
        json={"profile_id": "default"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["validation"] == "unreachable"
    assert body["detail"]["status"] == "runtime_unavailable"
