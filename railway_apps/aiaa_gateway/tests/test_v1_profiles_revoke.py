"""Tests for POST /v1/profiles/revoke."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aiaa_gateway import create_app


def _make_client(
    *,
    gateway_token: str = "gateway-internal-token",
    profile_store: dict[str, dict[str, Any]] | None = None,
):
    app = create_app(
        {
            "TESTING": True,
            "GATEWAY_INTERNAL_TOKEN": gateway_token,
            "PROFILE_STORE": {} if profile_store is None else profile_store,
        }
    )
    return app.test_client()


def test_post_v1_profiles_revoke_requires_gateway_bearer_auth():
    client = _make_client()

    response = client.post("/v1/profiles/revoke", json={"profile_id": "default"})

    assert response.status_code == 401
    body = response.get_json()
    assert body["error"]["type"] == "authentication_error"


def test_post_v1_profiles_revoke_requires_profile_id():
    client = _make_client()

    response = client.post(
        "/v1/profiles/revoke",
        json={},
        headers={"Authorization": "Bearer gateway-internal-token"},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["message"] == "profile_id is required."


def test_post_v1_profiles_revoke_rejects_invalid_profile_id():
    client = _make_client()

    response = client.post(
        "/v1/profiles/revoke",
        json={"profile_id": "../escape"},
        headers={"Authorization": "Bearer gateway-internal-token"},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["message"] == "profile_id is invalid."


def test_post_v1_profiles_revoke_clears_tokens_and_marks_profile_revoked():
    store = {
        "student-a": {
            "profile_id": "student-a",
            "status": "active",
            "token": "raw-token-should-not-survive",
            "encrypted_token": "enc:v1:should-not-survive",
        }
    }
    client = _make_client(profile_store=store)

    response = client.post(
        "/v1/profiles/revoke",
        json={"profile_id": "student-a"},
        headers={"Authorization": "Bearer gateway-internal-token"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"status": "ok", "revoked": True}

    profile = store["student-a"]
    assert profile["status"] == "revoked"
    assert "token" not in profile
    assert "encrypted_token" not in profile
    assert profile["revoked_at"]
    assert profile["updated_at"]


def test_post_v1_profiles_revoke_invalidates_missing_profile():
    store: dict[str, dict[str, Any]] = {}
    client = _make_client(profile_store=store)

    response = client.post(
        "/v1/profiles/revoke",
        json={"profile_id": "new-profile"},
        headers={"Authorization": "Bearer gateway-internal-token"},
    )

    assert response.status_code == 200
    profile = store["new-profile"]
    assert profile["status"] == "revoked"
    assert "token" not in profile
    assert "encrypted_token" not in profile
