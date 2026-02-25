#!/usr/bin/env python3
"""
AIAA Dashboard - Hardening Integration Tests
Tests API v2 endpoint validation, auth enforcement, and end-to-end smoke test.

Created in Phase 10 (End-to-End Verification) to validate all hardening
work from Phases 2-9.
"""

import os
import sys
import hashlib
import tempfile
from pathlib import Path

# --- Module-level env vars (MUST be set before any Flask imports) ---
os.environ["FLASK_ENV"] = "testing"
os.environ["DASHBOARD_USERNAME"] = "testadmin"
_test_pw_hash = hashlib.sha256(b"testpass123").hexdigest()
_test_flask_key = hashlib.sha256(b"test-secret-key").hexdigest()
os.environ["DASHBOARD_PASSWORD_HASH"] = _test_pw_hash
os.environ["FLASK_SECRET_KEY"] = _test_flask_key

_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DB_PATH"] = _test_db.name

# --- Import after env vars ---
from app import create_app
import database

import pytest


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def app():
    """Create application for testing."""
    # Re-assert test env in case another test module mutated process env.
    os.environ["DASHBOARD_USERNAME"] = "testadmin"
    os.environ["DASHBOARD_PASSWORD_HASH"] = _test_pw_hash
    os.environ["FLASK_SECRET_KEY"] = _test_flask_key
    os.environ["DB_PATH"] = _test_db.name

    application = create_app()
    application.config["TESTING"] = True
    application.config["SESSION_COOKIE_SECURE"] = False

    with application.app_context():
        database.init_db(application)

    yield application

    # Cleanup temp DB
    try:
        os.unlink(_test_db.name)
    except OSError:
        pass


@pytest.fixture(scope="module")
def client(app):
    """Unauthenticated test client."""
    return app.test_client()


@pytest.fixture(scope="module")
def auth_client(app):
    """Authenticated test client with session injected."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testadmin"
    return c


# =============================================================================
# Public Skills Endpoints
# =============================================================================

def test_list_skills(client):
    """GET /api/v2/skills returns 200 with skills list."""
    resp = client.get("/api/v2/skills")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["total"] > 0
    assert isinstance(data["skills"], list)


def test_search_skills(client):
    """GET /api/v2/skills/search?q=email returns results."""
    resp = client.get("/api/v2/skills/search?q=email")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert isinstance(data["skills"], list)


def test_search_skills_empty(client):
    """GET /api/v2/skills/search with nonsense query returns empty results."""
    resp = client.get("/api/v2/skills/search?q=zzzznotaskill")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert len(data["skills"]) == 0


def test_skill_categories(client):
    """GET /api/v2/skills/categories returns category list."""
    resp = client.get("/api/v2/skills/categories")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert isinstance(data["categories"], (list, dict))


def test_recommended_skills(client):
    """GET /api/v2/skills/recommended returns 200."""
    resp = client.get("/api/v2/skills/recommended")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_skill_detail(client):
    """GET /api/v2/skills/{name} returns skill object."""
    # First get a real skill name
    resp = client.get("/api/v2/skills")
    skills = resp.get_json()["skills"]
    assert len(skills) > 0
    skill_name = skills[0]["name"]

    resp = client.get(f"/api/v2/skills/{skill_name}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "skill" in data
    assert data["skill"]["name"] == skill_name


def test_skill_detail_not_found(client):
    """GET /api/v2/skills/nonexistent returns 404."""
    resp = client.get("/api/v2/skills/nonexistent-skill-xyz")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["status"] == "error"


# =============================================================================
# Auth Enforcement
# =============================================================================

def test_execute_requires_auth(client):
    """POST /api/v2/skills/blog-post/execute without session returns 401."""
    resp = client.post("/api/v2/skills/blog-post/execute", json={"params": {}})
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["status"] == "error"


def test_settings_requires_auth(client):
    """POST /api/v2/settings/api-keys without session returns 401."""
    resp = client.post("/api/v2/settings/api-keys", json={"key_name": "openrouter", "key_value": "sk-or-test"})
    assert resp.status_code == 401


def test_clients_create_requires_auth(client):
    """POST /api/v2/clients without session returns 401."""
    resp = client.post("/api/v2/clients", json={"name": "Test Client"})
    assert resp.status_code == 401


def test_executions_requires_auth(client):
    """GET /api/v2/executions without session returns 401."""
    resp = client.get("/api/v2/executions")
    assert resp.status_code == 401


# =============================================================================
# Authenticated: API Key Management
# =============================================================================

def test_save_api_key_valid(auth_client):
    """POST /api/v2/settings/api-keys with valid data returns 200."""
    resp = auth_client.post("/api/v2/settings/api-keys", json={
        "key_name": "openrouter",
        "key_value": "sk-or-test-1234567890abcdef",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_save_api_key_missing_fields(auth_client):
    """POST /api/v2/settings/api-keys with empty body returns 400 with field errors."""
    resp = auth_client.post("/api/v2/settings/api-keys", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"]
    assert isinstance(data["errors"], dict)
    assert "key_name" in data["errors"] or "key_value" in data["errors"]


def test_save_api_key_invalid_prefix(auth_client):
    """POST /api/v2/settings/api-keys with wrong prefix returns 400."""
    resp = auth_client.post("/api/v2/settings/api-keys", json={
        "key_name": "openrouter",
        "key_value": "invalid-no-prefix",
    })
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "errors" in data
    assert "key_value" in data["errors"]


def test_api_key_status(auth_client):
    """GET /api/v2/settings/api-keys/status returns 200 with keys info."""
    resp = auth_client.get("/api/v2/settings/api-keys/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "keys" in data


def test_rotate_api_key_valid(auth_client):
    """POST /api/v2/settings/api-keys/<key>/rotate rotates token successfully."""
    resp = auth_client.post("/api/v2/settings/api-keys/openrouter/rotate", json={
        "key_value": "sk-or-rotated-1234567890abcdef",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["action"] == "rotate"
    assert os.getenv("OPENROUTER_API_KEY", "").startswith("sk-or-rotated-")


def test_rotate_api_key_missing_value(auth_client):
    """POST /api/v2/settings/api-keys/<key>/rotate with empty body returns 400."""
    resp = auth_client.post("/api/v2/settings/api-keys/openrouter/rotate", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "errors" in data
    assert "key_value" in data["errors"]


def test_revoke_api_key_valid(auth_client):
    """POST /api/v2/settings/api-keys/<key>/revoke removes configured token."""
    seed = auth_client.post("/api/v2/settings/api-keys/openrouter/rotate", json={
        "key_value": "sk-or-revoke-1234567890abcdef",
    })
    assert seed.status_code == 200

    resp = auth_client.post("/api/v2/settings/api-keys/openrouter/revoke")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["action"] == "revoke"

    status_resp = auth_client.get("/api/v2/settings/api-keys/status")
    assert status_resp.status_code == 200
    status_data = status_resp.get_json()
    assert status_data["keys"]["openrouter"]["configured"] is False


def test_settings_page_has_rotate_and_revoke_controls(auth_client):
    """GET /settings includes rotate/revoke controls for API key rows."""
    resp = auth_client.get("/settings")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "rotateApiKey('openrouter')" in html
    assert "revokeApiKey('openrouter')" in html


# =============================================================================
# Authenticated: Client Management
# =============================================================================

def test_create_client_valid(auth_client):
    """POST /api/v2/clients with valid data returns 201."""
    resp = auth_client.post("/api/v2/clients", json={
        "name": "Test Client Inc",
        "website": "https://example.com",
        "industry": "Technology",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "client_id" in data or "slug" in data


def test_create_client_missing_name(auth_client):
    """POST /api/v2/clients with no name returns 400 with 'name' error."""
    resp = auth_client.post("/api/v2/clients", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert isinstance(data["errors"], dict)
    assert "name" in data["errors"]


def test_create_client_short_name(auth_client):
    """POST /api/v2/clients with 1-char name returns 400."""
    resp = auth_client.post("/api/v2/clients", json={"name": "A"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "name" in data["errors"]


def test_create_client_invalid_website(auth_client):
    """POST /api/v2/clients with bad URL returns 400 with 'website' error."""
    resp = auth_client.post("/api/v2/clients", json={
        "name": "Valid Name Corp",
        "website": "not-a-url",
    })
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "website" in data["errors"]


def test_list_clients(auth_client):
    """GET /api/v2/clients returns 200 with clients list."""
    resp = auth_client.get("/api/v2/clients")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "clients" in data


# =============================================================================
# Authenticated: Preferences and Profile
# =============================================================================

def test_get_preferences(auth_client):
    """GET /api/v2/settings/preferences returns 200."""
    resp = auth_client.get("/api/v2/settings/preferences")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "preferences" in data


def test_save_preferences_valid(auth_client):
    """POST /api/v2/settings/preferences with valid JSON returns 200."""
    resp = auth_client.post("/api/v2/settings/preferences", json={"role": "marketer"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_save_preferences_invalid_body(auth_client):
    """POST /api/v2/settings/preferences with non-object body returns 400."""
    resp = auth_client.post(
        "/api/v2/settings/preferences",
        data='"just a string"',
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert isinstance(data["errors"], dict)


def test_get_profile(auth_client):
    """GET /api/v2/settings/profile returns 200."""
    resp = auth_client.get("/api/v2/settings/profile")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "profile" in data


def test_save_profile_valid(auth_client):
    """POST /api/v2/settings/profile with valid JSON returns 200."""
    resp = auth_client.post("/api/v2/settings/profile", json={"display_name": "Test Admin"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


# =============================================================================
# Authenticated: Executions
# =============================================================================

def test_list_executions(auth_client):
    """GET /api/v2/executions returns 200 with executions list."""
    resp = auth_client.get("/api/v2/executions")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "executions" in data


def test_execution_stats(auth_client):
    """GET /api/v2/executions/stats returns 200 with stats."""
    resp = auth_client.get("/api/v2/executions/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "stats" in data


# =============================================================================
# Chat Endpoints
# =============================================================================

def test_chat_page_requires_auth(client):
    """GET /chat without auth redirects to login."""
    resp = client.get("/chat", follow_redirects=False)
    assert resp.status_code == 302


def test_chat_token_status_missing(auth_client, monkeypatch):
    """GET /api/chat/token/status returns missing when token is not configured."""
    import routes.chat as chat_routes

    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "")
    resp = auth_client.get("/api/chat/token/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["configured"] is False
    assert data["validation"] == "missing"


def test_chat_save_token_invalid(auth_client, monkeypatch):
    """POST /api/chat/token returns 400 for invalid token."""
    import routes.chat as chat_routes

    monkeypatch.setattr(
        chat_routes,
        "validate_claude_token",
        lambda token: {"status": "invalid", "http_status": 401, "message": "bad token"},
    )
    resp = auth_client.post("/api/chat/token", json={"token": "bad-token"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["validation"]["status"] == "invalid"


def test_chat_save_token_success(auth_client, monkeypatch):
    """POST /api/chat/token saves and returns validation metadata."""
    import routes.chat as chat_routes

    monkeypatch.setattr(
        chat_routes,
        "validate_claude_token",
        lambda token: {"status": "valid", "http_status": 200, "message": "ok"},
    )
    monkeypatch.setattr(chat_routes, "_persist_to_railway_async", lambda payload: False)

    resp = auth_client.post("/api/chat/token", json={"token": "eyJ.test.token"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["validation"] == "valid"
    assert data["persisted_to_railway"] is False


def test_chat_session_message_and_stream(auth_client, monkeypatch):
    """Session create -> message send -> stream path works with mocked runner."""
    import routes.chat as chat_routes

    class FakeRunner:
        def __init__(self):
            self._sessions = {}

        def list_sessions(self):
            return [{"id": sid, "title": v["title"], "status": "idle"} for sid, v in self._sessions.items()]

        def create_session(self, title=None):
            sid = "abc123"
            self._sessions[sid] = {"id": sid, "title": title or "New chat", "messages": []}
            return {"id": sid, "title": title or "New chat", "messages": []}

        def get_session(self, session_id):
            return self._sessions.get(session_id)

        def has_session(self, session_id):
            return session_id in self._sessions

        def send_message(self, session_id, user_message):
            self._sessions[session_id]["messages"].append({"role": "user", "content": user_message})

        def get_stream(self, session_id):
            yield 'data: {"type":"text","content":"hello"}\n\n'
            yield 'data: {"type":"done"}\n\n'

    fake_runner = FakeRunner()
    monkeypatch.setattr(chat_routes, "_get_runner", lambda: fake_runner)
    monkeypatch.setattr(chat_routes, "get_claude_token", lambda: "eyJ.test.token")

    create_resp = auth_client.post("/api/chat/sessions", json={})
    assert create_resp.status_code == 201
    create_data = create_resp.get_json()
    session_id = create_data["session_id"]
    assert session_id == "abc123"

    get_resp = auth_client.get(f"/api/chat/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["session"]["id"] == session_id

    bad_resp = auth_client.post("/api/chat/message", json={"session_id": session_id})
    assert bad_resp.status_code == 400

    send_resp = auth_client.post(
        "/api/chat/message",
        json={"session_id": session_id, "message": "hello"},
    )
    assert send_resp.status_code == 202
    assert send_resp.get_json()["status"] == "ok"

    stream_resp = auth_client.get(f"/api/chat/stream/{session_id}")
    assert stream_resp.status_code == 200
    assert stream_resp.mimetype == "text/event-stream"
    assert b'"type":"done"' in stream_resp.data


# =============================================================================
# E2E Smoke Test
# =============================================================================

def test_e2e_smoke(app):
    """End-to-end smoke test: login -> API key -> browse -> execute -> check status.

    Uses a fresh test_client (not the shared fixtures) to simulate a real
    user session from login through skill execution.
    """
    client = app.test_client()

    # Step 1 - Login with form credentials
    resp = client.post("/login", data={
        "username": "testadmin",
        "password": "testpass123",
    }, follow_redirects=False)
    assert resp.status_code == 302, f"Login should redirect, got {resp.status_code}"

    # Step 2 - Save an API key
    resp = client.post("/api/v2/settings/api-keys", json={
        "key_name": "openrouter",
        "key_value": "sk-or-test-1234567890abcdef",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"

    # Step 3 - Browse skills
    resp = client.get("/api/v2/skills")
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["total"] > 0
    skill_name = data["skills"][0]["name"]

    # Step 4 - View skill detail
    resp = client.get(f"/api/v2/skills/{skill_name}")
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "skill" in data

    # Step 5 - Execute a skill (or validate required params)
    # Build dummy params from required inputs if any
    skill_meta = data["skill"]
    required_inputs = [i for i in (skill_meta.get("inputs") or []) if i.get("required")]
    params = {}
    for inp in required_inputs:
        field = inp.get("name", "")
        if field:
            params[field] = "test-value"

    resp = client.post(f"/api/v2/skills/{skill_name}/execute", json={"params": params})
    # Accept 202 (execution started) or 400 (validation error -- still proves the layer works)
    assert resp.status_code in (202, 400), f"Execute returned unexpected {resp.status_code}"
    data = resp.get_json()
    if resp.status_code == 202:
        assert data["status"] == "ok"
        assert "execution_id" in data
    else:
        # 400 means validation caught missing/invalid params -- structured error shape
        assert data["status"] == "error"
        assert "errors" in data or "message" in data

    # Step 6 - Check executions list
    resp = client.get("/api/v2/executions")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "executions" in data

    # Step 7 - Check API key status
    resp = client.get("/api/v2/settings/api-keys/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "keys" in data
