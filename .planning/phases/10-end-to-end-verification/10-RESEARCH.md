# Phase 10: End-to-End Verification - Research

**Researched:** 2026-02-23
**Domain:** pytest + Flask test_client integration testing
**Confidence:** HIGH

## Summary

Phase 10 requires writing integration tests in `test_hardening.py` that validate all API v2 endpoints added during phases 2-9 and run an end-to-end smoke test covering the complete user journey. The existing `test_app.py` already passes under pytest (7 tests, all green) despite using a non-standard `return True/False` pattern instead of `assert` statements.

The testing infrastructure is straightforward: Flask 3.1.2 includes `app.test_client()` which supports JSON APIs natively (via `client.post(url, json={...})` and `response.get_json()`), and session authentication can be simulated via `client.session_transaction()`. pytest 7.4.4 is already installed and working. No additional test dependencies are needed.

**Primary recommendation:** Create a single `test_hardening.py` file using pytest fixtures for app/client/authenticated-client setup, with isolated test database per session, testing all 18+ API v2 endpoints for both valid and invalid inputs, plus one sequential E2E smoke test function.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 7.4.4 | Test framework | Already installed, discovers both test files |
| Flask test_client | (bundled with Flask 3.1.2) | HTTP-level testing | Built-in, no server needed, session support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tempfile (stdlib) | N/A | Temporary test database | Isolate test DB from production data |
| hashlib (stdlib) | N/A | Generate test password hashes | Match existing SHA-256 auth pattern |
| json (stdlib) | N/A | Parse/build JSON payloads | API v2 endpoints all use JSON |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw test_client | pytest-flask | Adds dependency; test_client is sufficient for this scope |
| Manual session setup | Flask-Login test helpers | App doesn't use Flask-Login |
| Selenium/Playwright | Flask test_client | CONTEXT.md explicitly says no browser automation |

**Installation:**
```bash
# No new packages needed - everything is already available
```

## Architecture Patterns

### Recommended Test File Structure
```
railway_apps/aiaa_dashboard/
  test_app.py               # Existing 7 regression tests (DO NOT MODIFY)
  test_hardening.py          # New file: API validation + E2E smoke test
```

No conftest.py is needed. The new test file will define its own fixtures at file scope. Reason: the existing `test_app.py` sets environment variables at module level (lines 15-26) which already configure the test environment. A conftest.py would create import ordering issues.

### Pattern 1: Isolated App Fixture with Temp DB
**What:** Each test session gets a fresh Flask app with its own temporary SQLite database
**When to use:** All new tests
**Example:**
```python
# Source: Flask 3.1.x official docs + existing test_app.py pattern
import os
import hashlib
import tempfile
import pytest

@pytest.fixture(scope="module")
def app():
    """Create Flask app with isolated test database."""
    # Create temp DB
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)

    # Set env vars BEFORE importing app
    os.environ["FLASK_ENV"] = "testing"
    os.environ["DASHBOARD_USERNAME"] = "testadmin"
    os.environ["DASHBOARD_PASSWORD_HASH"] = hashlib.sha256(b"testpass123").hexdigest()
    os.environ["FLASK_SECRET_KEY"] = hashlib.sha256(b"test-secret").hexdigest()
    os.environ["DB_PATH"] = db_file.name

    # Import after env setup
    from app import create_app
    import database

    test_app = create_app()
    test_app.config["TESTING"] = True
    test_app.config["SESSION_COOKIE_SECURE"] = False  # Allow test cookies

    with test_app.app_context():
        database.init_db(test_app)

    yield test_app

    # Cleanup
    os.unlink(db_file.name)

@pytest.fixture
def client(app):
    """Unauthenticated test client."""
    return app.test_client()

@pytest.fixture
def auth_client(app):
    """Authenticated test client with active session."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testadmin"
    return client
```

### Pattern 2: Session Authentication via session_transaction()
**What:** Bypass the login form and inject session state directly
**When to use:** All tests that need an authenticated user
**Example:**
```python
# Source: Flask 3.1.x official testing docs
def test_protected_endpoint(auth_client):
    """Authenticated client can access protected routes."""
    resp = auth_client.get("/api/v2/skills")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
```

### Pattern 3: Validation Error Response Assertion
**What:** Assert the structured error format from validation_error() helper
**When to use:** All invalid-input tests for API v2 endpoints
**Example:**
```python
# Source: api_v2.py validation_error() helper
def test_create_client_missing_name(auth_client):
    resp = auth_client.post("/api/v2/clients", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert data["message"] == "Validation failed"
    assert "name" in data["errors"]
```

### Pattern 4: E2E Smoke Test as Sequential Steps
**What:** Single test function that walks through the full user journey using a single client instance
**When to use:** The E2E smoke test (TEST-03)
**Example:**
```python
def test_e2e_smoke(app):
    """End-to-end: setup -> login -> API key -> browse -> execute -> output."""
    client = app.test_client()

    # Step 1: Login
    resp = client.post("/login", data={
        "username": "testadmin",
        "password": "testpass123"
    }, follow_redirects=False)
    assert resp.status_code == 302  # Redirect on success

    # Step 2: Configure API key (session persists)
    resp = client.post("/api/v2/settings/api-keys", json={
        "key_name": "openrouter",
        "key_value": "sk-or-test-1234567890"
    })
    assert resp.status_code == 200

    # Step 3: Browse skills
    resp = client.get("/api/v2/skills")
    data = resp.get_json()
    assert data["total"] > 0

    # Step 4: Execute a skill (creates DB record, launches subprocess)
    # Step 5: Check execution status
```

### Anti-Patterns to Avoid
- **Sharing database state between test_app.py and test_hardening.py:** Each file must use its own temp DB to avoid interference. The existing test_app.py already creates its own temp DB at module level.
- **Modifying test_app.py:** CONTEXT.md explicitly states "No modifications to existing tests."
- **Using `return True` in new tests:** Use `assert` statements. The existing test_app.py pattern causes PytestReturnNotNoneWarning.
- **Testing rendered HTML content:** CONTEXT.md says "test HTTP responses and JSON, not rendered UI." Check status codes, not page content.
- **Starting a live server:** Use `app.test_client()` only. No `app.run()` in tests.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session auth in tests | Manual cookie manipulation | `client.session_transaction()` | Flask built-in, handles serialization |
| JSON request/response | Manual Content-Type headers | `client.post(url, json=data)` and `resp.get_json()` | Flask test client handles encoding |
| Temp database isolation | Manual file management | `tempfile.NamedTemporaryFile` + fixture teardown | Stdlib, auto-cleanup |
| Password hashing for test user | Hard-coded hash string | `hashlib.sha256(b"testpass123").hexdigest()` | Matches existing auth pattern exactly |
| Structured error assertions | Ad-hoc field checking | Assert against `validation_error()` output shape | All v2 endpoints use same format |

**Key insight:** The Flask test client already handles everything needed. There are zero external dependencies required.

## Common Pitfalls

### Pitfall 1: Module-Level Environment Variables in test_app.py
**What goes wrong:** test_app.py sets `os.environ` at import time (lines 15-26). If test_hardening.py imports `app` before setting its own env vars, the wrong DB path or password hash gets baked in.
**Why it happens:** Python module imports are cached. First import wins.
**How to avoid:** test_hardening.py must set its own env vars BEFORE any `from app import ...` statements. Use `scope="module"` fixture with env var setup at the top.
**Warning signs:** Tests pass individually but fail when run together.

### Pitfall 2: Session Cookie Security Blocking Test Auth
**What goes wrong:** The production config sets `SESSION_COOKIE_SECURE = True`, which means cookies are only sent over HTTPS. The test client uses HTTP.
**Why it happens:** Config class inherits secure defaults.
**How to avoid:** Set `app.config["SESSION_COOKIE_SECURE"] = False` in the test fixture, or set `FLASK_ENV=testing`/development. The existing test_app.py works because it sets `FLASK_ENV=testing` which doesn't trigger secure cookies (but actually it uses ProductionConfig since "testing" != "development"). Safest approach: explicitly set `SESSION_COOKIE_SECURE = False` in the test app fixture.
**Warning signs:** `session_transaction()` sets values but subsequent requests don't see them.

### Pitfall 3: Database Thread-Local Connections
**What goes wrong:** The database module uses `threading.local()` for connections. If tests create connections in setup and then make requests through the test client, the test client runs in the same thread but the connection state might differ.
**Why it happens:** `database.py` uses `_thread_local = threading.local()` for connection pooling.
**How to avoid:** Initialize the database within `app.app_context()` in the fixture. The test client shares the same thread, so this works correctly. Just ensure `database.init_db(app)` is called in the fixture.
**Warning signs:** "no such table" errors despite migrations running.

### Pitfall 4: Skill Execution Actually Launching Subprocesses
**What goes wrong:** Calling `POST /api/v2/skills/<name>/execute` triggers `execute_skill()` which spawns a real subprocess running a Python script.
**Why it happens:** The execute endpoint calls `execute_skill()` which uses `threading.Thread` + `subprocess.Popen` to run the actual skill script.
**How to avoid:** For the E2E smoke test, either: (a) accept that a subprocess is launched and just verify the execution record is created with status "queued" (don't wait for completion), or (b) mock `subprocess.Popen` if you need to avoid side effects. Option (a) is simpler and sufficient for a smoke test.
**Warning signs:** Tests hanging, random failures due to missing API keys in subprocess.

### Pitfall 5: SKILLS_DIR Path Resolution
**What goes wrong:** `skill_execution_service.py` resolves `SKILLS_DIR` relative to the file location (`_PROJECT_ROOT / ".claude" / "skills"`). If tests are run from a different working directory, skills might not be found.
**Why it happens:** Path resolution uses `Path(__file__).parent.parent.parent.parent`.
**How to avoid:** The path is absolute (resolved from `__file__`), so it works from any cwd. However, verify skills are found by checking `list_available_skills()` returns non-empty in the test. Can also set `SKILLS_DIR` env var as override.
**Warning signs:** `search_skills` and `list_available_skills` return empty lists.

### Pitfall 6: API v2 login_required Returns 401 JSON (Not Redirect)
**What goes wrong:** Confusing the behavior of `views.login_required` (redirects to `/login`) vs `api_v2.login_required` (returns 401 JSON). Tests must assert the correct behavior for each.
**Why it happens:** There are two separate `login_required` decorators -- one in `views.py` (redirect-based) and one in `api_v2.py` (JSON 401).
**How to avoid:** For API v2 tests, assert 401 status code. For view tests, assert 302 redirect.
**Warning signs:** Expecting 401 from a view route or 302 from an API route.

## Code Examples

Verified patterns from the actual codebase:

### Complete API v2 Endpoint Inventory (from api_v2.py)
```
PUBLIC (no auth):
  GET  /api/v2/skills                    - List all skills
  GET  /api/v2/skills/search?q=...       - Search skills
  GET  /api/v2/skills/categories         - Skills by category
  GET  /api/v2/skills/recommended?role=  - Role-based recommendations
  GET  /api/v2/skills/<name>             - Skill detail

AUTHENTICATED (@login_required):
  POST /api/v2/skills/<name>/execute     - Execute a skill (returns 202)
  GET  /api/v2/skills/<name>/estimate    - Time/cost estimate
  GET  /api/v2/executions/<id>/status    - Execution status
  GET  /api/v2/executions/<id>/output    - Execution output
  POST /api/v2/executions/<id>/cancel    - Cancel execution
  GET  /api/v2/executions               - List executions
  GET  /api/v2/executions/stats          - Execution statistics
  POST /api/v2/settings/api-keys         - Save API key
  GET  /api/v2/settings/api-keys/status  - Check API key status
  GET  /api/v2/settings/preferences      - Get preferences
  POST /api/v2/settings/preferences      - Save preferences
  GET  /api/v2/settings/profile          - Get profile
  POST /api/v2/settings/profile          - Save profile
  POST /api/v2/clients                   - Create client
  GET  /api/v2/clients                   - List clients
  GET  /api/v2/clients/<slug>            - Get client
  PUT  /api/v2/clients/<slug>            - Update client
```

### Validation Error Response Shape
```python
# All v2 endpoints use validation_error() which returns:
{
    "status": "error",
    "message": "Validation failed",  # or custom message
    "errors": {
        "field_name": "Error description"
    }
}
# HTTP status: 400
```

### Standard Success Response Shape
```python
# List endpoints:
{"status": "ok", "total": N, "skills|clients|executions": [...]}

# Single item:
{"status": "ok", "skill|client|execution": {...}}

# Action endpoints:
{"status": "ok", "message": "...", ...}

# Execute returns 202:
{"status": "ok", "execution_id": "uuid", "message": "Skill '...' execution started"}
```

### Key Validation Rules from api_v2.py
```python
# Client creation:
# - name: required, 2-100 chars
# - website: optional, must match r'^https?://.+\..+'
# - industry: optional, max 100 chars
# - Duplicate slug check (returns 409)

# API key save:
# - key_name: required
# - key_value: required
# - Prefix validation per provider (e.g., sk-or- for OpenRouter, pplx- for Perplexity)

# Skill execute:
# - Validates required params from parsed SKILL.md inputs dynamically
# - Returns 404 for unknown skill
# - Returns 400 with field-level errors for missing required params

# Preferences/Profile save:
# - Body must be a JSON object (dict), not list or string
```

### Login Flow for E2E Test
```python
# 1. POST /login with form data (NOT json)
resp = client.post("/login", data={
    "username": "testadmin",
    "password": "testpass123"
}, follow_redirects=False)
# Returns 302 redirect to home_v2 on success
# Returns 200 with error template on failure

# 2. After login, session has:
#    session["logged_in"] = True
#    session["username"] = "testadmin"
```

### Setup Route Behavior
```python
# GET /setup:
#   - If DASHBOARD_PASSWORD_HASH is set: redirects to /login
#   - If not set: renders setup.html form

# POST /setup:
#   - If DASHBOARD_PASSWORD_HASH is set: redirects to /login
#   - Validates: password required, passwords match, min 8 chars
#   - Sets os.environ["DASHBOARD_USERNAME"] and DASHBOARD_PASSWORD_HASH
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom test runner (`if __name__`) | pytest discovery | Already working | Both approaches coexist; pytest discovers functions named `test_*` |
| `return True/False` from tests | `assert` statements | pytest convention | Old pattern causes warnings but still works |
| Single test file | Separate test_app.py + test_hardening.py | Phase 10 | Clean separation of baseline vs hardening tests |

**Deprecated/outdated:**
- `app.test_request_context()` for session testing: replaced by `client.session_transaction()` in modern Flask
- `response.data` for JSON: use `response.get_json()` instead (available since Flask 1.0)

## Open Questions

Things that couldn't be fully resolved:

1. **Subprocess side effects in E2E execute test**
   - What we know: `execute_skill()` launches a real subprocess that runs a Python script with potentially missing API keys
   - What's unclear: Whether the subprocess will error silently or cause test failures/hangs
   - Recommendation: Test only that execution record is created (status "queued") and the 202 response is correct. Do NOT wait for subprocess completion. The test verifies the HTTP layer, not the skill execution itself.

2. **Database isolation between test_app.py and test_hardening.py**
   - What we know: test_app.py creates its own temp DB at module level, which means when pytest collects both files, they each get separate databases
   - What's unclear: Whether the `database` module's global `DB_PATH` state could leak between test files during collection
   - Recommendation: Use `scope="module"` fixtures with explicit `database.set_db_path()` calls, and ensure env vars are set before any app imports in test_hardening.py. Tested: existing tests pass under pytest, so the pattern works.

3. **Existing test warnings**
   - What we know: 7 existing tests produce PytestReturnNotNoneWarning (return True instead of assert)
   - What's unclear: Whether a future pytest version will turn these warnings into errors
   - Recommendation: Ignore. CONTEXT.md says "No modifications to existing tests." New tests must use `assert`.

## Sources

### Primary (HIGH confidence)
- Flask 3.1.x official testing docs (https://flask.palletsprojects.com/en/stable/testing/) -- session_transaction(), test_client(), JSON API testing
- Direct codebase reading: `api_v2.py` (650 lines), `views.py` (862+ lines), `models.py` (763 lines), `skill_execution_service.py`, `database.py`, `test_app.py`
- Local verification: `pytest --collect-only` confirms 7 tests discovered from test_app.py; `pytest test_app.py -v` confirms all 7 pass

### Secondary (MEDIUM confidence)
- pytest 7.4.4 behavior verified locally (collection, warnings, fixture scope)
- Flask test_client JSON support verified via official docs

### Tertiary (LOW confidence)
- None. All findings verified against actual codebase and official documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified locally (pytest 7.4.4, Flask 3.1.2, test_client works)
- Architecture: HIGH - based on actual codebase reading of all 18+ endpoints and existing test patterns
- Pitfalls: HIGH - identified from reading actual source code (thread-local DB, module-level env vars, dual login_required decorators, subprocess execution)
- Code examples: HIGH - extracted directly from api_v2.py, views.py, models.py source code

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable -- no moving targets, just testing existing code)
