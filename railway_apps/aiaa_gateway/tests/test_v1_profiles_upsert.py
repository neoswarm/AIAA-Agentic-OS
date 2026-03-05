"""Tests for POST /v1/profiles/upsert."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pytest


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aiaa_gateway import create_app
from aiaa_gateway import routes
from aiaa_gateway.services.profile_service import ENCRYPTED_TOKEN_PREFIX
from aiaa_gateway.services.profile_service import decrypt_token_from_storage


@pytest.fixture(autouse=True)
def _set_required_encryption_key(monkeypatch, tmp_path):
    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "gateway-startup-test-key")
    monkeypatch.setenv("GATEWAY_PROFILE_DB_PATH", str(tmp_path / "gateway_profiles.db"))


def _auth_headers(token: str = "gateway-internal-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _make_client(
    *,
    gateway_token: str = "gateway-internal-token",
    profile_store: dict[str, dict[str, Any]] | None = None,
    profile_token_store: dict[str, dict[str, Any]] | None = None,
):
    app = create_app(
        {
            "TESTING": True,
            "GATEWAY_INTERNAL_TOKEN": gateway_token,
            "PROFILE_STORE": {} if profile_store is None else profile_store,
            "PROFILE_TOKEN_STORE": (
                {} if profile_token_store is None else profile_token_store
            ),
            "GATEWAY_RUNTIME_CANARY_TIMEOUT_SECONDS": 4,
        }
    )
    return app.test_client()


def test_post_v1_profiles_upsert_requires_gateway_bearer_auth():
    client = _make_client()

    response = client.post(
        "/v1/profiles/upsert",
        json={"profile_id": "default", "token": "token-123"},
    )

    assert response.status_code == 401
    body = response.get_json()
    assert body["error"]["type"] == "authentication_error"


def test_post_v1_profiles_upsert_requires_profile_id_and_token():
    client = _make_client()

    response = client.post(
        "/v1/profiles/upsert",
        json={},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["type"] == "invalid_request_error"
    assert body["error"]["details"]["profile_id"] == "profile_id is required"


def test_post_v1_profiles_upsert_creates_profile_and_encrypts_token(monkeypatch):
    client = _make_client()
    monkeypatch.setattr(
        routes,
        "run_gateway_runtime_canary",
        lambda token, *, timeout_seconds=None: {
            "status": "valid",
            "message": "ok",
            "used_token": token,
            "timeout": timeout_seconds,
        },
    )

    response = client.post(
        "/v1/profiles/upsert",
        json={"profile_id": "Default", "token": "stored-token", "status": "active"},
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["action"] == "created"
    assert body["profile_id"] == "default"
    assert body["profile"]["profile_id"] == "default"
    assert body["profile"]["status"] == "active"
    assert body["validation"] == "valid"
    assert body["token_status"] == "valid"

    app_store = client.application.config["PROFILE_TOKEN_STORE"]["default"]
    assert app_store["encrypted_token"].startswith(ENCRYPTED_TOKEN_PREFIX)
    assert app_store.get("token") is None
    assert decrypt_token_from_storage(app_store["encrypted_token"]) == "stored-token"


def test_post_v1_profiles_upsert_returns_updated_when_token_exists(monkeypatch):
    client = _make_client(
        profile_token_store={"default": {"token": "existing-token", "status": "active"}}
    )
    monkeypatch.setattr(
        routes,
        "run_gateway_runtime_canary",
        lambda token, *, timeout_seconds=None: {"status": "valid", "message": "ok"},
    )

    response = client.post(
        "/v1/profiles/upsert",
        json={"profile_id": "default", "token": "new-token"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["action"] == "updated"
    assert body["profile_id"] == "default"


def test_post_v1_profiles_upsert_maps_runtime_failure_to_unreachable(monkeypatch):
    client = _make_client()
    monkeypatch.setattr(
        routes,
        "run_gateway_runtime_canary",
        lambda token, *, timeout_seconds=None: {
            "status": "runtime_unavailable",
            "message": "Claude runtime missing",
        },
    )

    response = client.post(
        "/v1/profiles/upsert",
        json={"profile_id": "default", "token": "new-token"},
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["validation"] == "unreachable"
    assert body["token_status"] == "unreachable"
