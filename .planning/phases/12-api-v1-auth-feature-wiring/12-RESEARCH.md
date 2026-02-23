# Phase 12: API v1 Auth & Feature Wiring - Research

**Researched:** 2026-02-23
**Domain:** Flask API route wiring, session auth, SQLite CRUD, legacy migration
**Confidence:** HIGH

## Summary

This phase closes four specific gaps identified in the v1-MILESTONE-AUDIT.md: a session key mismatch in api.py, a stub favorites API, a missing Google Docs delivery endpoint, and webhook management routes that only exist in app_legacy.py. All four issues are well-scoped with clear frontend contracts (JS already written) and existing backend patterns to follow.

The codebase has a clear split: `api.py` (v1, prefix `/api/`) handles deployment/workflow operations with a broken `require_auth` decorator, while `api_v2.py` (prefix `/api/v2/`) handles skills/executions/settings with a working `login_required` decorator. The v2 patterns should be the template for all new endpoints.

**Primary recommendation:** Fix the 1-line auth mismatch first, then implement the three feature endpoints following api_v2.py's `login_required` + `models.*` + `jsonify` pattern exactly.

## Standard Stack

### Core (Already In-Use -- No New Dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | current | Web framework, Blueprint routing | Already used for all routes |
| SQLite3 | stdlib | Database via `database.py` helpers | Already used for all persistence |
| models.py | local | Database CRUD layer | Already has favorites + webhook functions |
| main.js `fetchAPI` | local | Frontend API wrapper | Already used by webhooks.js; favorites.js uses raw fetch |

### Supporting (Already In-Use)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| google-api-python-client | installed | Google Docs creation | Google Docs delivery endpoint |
| google-auth | installed | Google API auth | Google Docs delivery endpoint |
| requests | installed | HTTP forwarding for webhooks | Webhook test endpoint |

### No New Dependencies Needed

This phase is pure wiring -- connecting existing frontend JS to new/fixed backend routes using libraries and patterns already in the codebase.

## Architecture Patterns

### Recommended Approach: Add to Existing Blueprints

```
routes/
├── api.py          # Fix require_auth (1 line), add GET /api/favorites
├── api_v2.py       # Add POST /api/v2/executions/{id}/deliver/gdocs
└── views.py        # Already has webhook handler -- NO changes needed here
```

**Decision: Where do webhook management API routes go?**

The webhook management endpoints (`/api/webhook-workflows/*`) should go in `api.py` because:
1. The frontend (webhooks.js) calls `/api/webhook-workflows/*` (no `/v2/` prefix)
2. `api.py` already has the `/api/` prefix on its Blueprint
3. The webhook receiver handler is already in `views.py` (uses DB-backed workflows via models.py)
4. Only the management CRUD routes need migrating from `app_legacy.py`

### Pattern: api_v2.py Endpoint Style (Follow This)

```python
@blueprint.route('/path', methods=['POST'])
@login_required
def endpoint_name():
    """Docstring with request/response format."""
    data = request.get_json(silent=True) or {}

    # Validate
    field = data.get('field_name', '').strip()
    if not field:
        return jsonify({"status": "error", "message": "field_name required"}), 400

    try:
        # Business logic via models.*
        result = models.some_operation(field)
        return jsonify({"status": "ok", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
```

Key conventions from api_v2.py:
- Use `@login_required` (checks `session.get('logged_in')`) -- NOT `@require_auth`
- Use `request.get_json(silent=True) or {}` for safe parsing
- Return `{"status": "ok", ...}` on success, `{"status": "error", "message": "..."}` on failure
- Wrap in try/except, return 500 with error message
- Use `models.*` functions for all database operations

### Anti-Patterns to Avoid
- **Do NOT use `@require_auth`** for new endpoints (even after the fix) -- it has a different style. Use `@login_required` matching api_v2.py.
- **Do NOT use in-memory registries** for webhook config (app_legacy.py pattern). The modular app already uses SQLite via `models.*`.
- **Do NOT import from app_legacy.py**. The webhook handler in `views.py` already uses DB-backed models. The legacy in-memory approach is obsolete.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Favorites persistence | File-based or in-memory store | `models.add_favorite()`, `models.remove_favorite()`, `models.get_favorites()`, `models.is_favorite()` | Already exists with SQLite-backed `favorites` table |
| Webhook CRUD | In-memory registry (app_legacy.py style) | `models.upsert_workflow()`, `models.get_workflows(workflow_type='webhook')`, `models.delete_workflow()` | Already exists with proper DB persistence |
| Google Docs creation | Custom Google API code | `.claude/skills/google-doc-delivery/create_google_doc.py` | Already a full skill with markdown-to-Docs conversion |
| Session auth checking | Custom session logic | `login_required` decorator from api_v2.py or views.py | Already implemented correctly |

**Key insight:** Every piece of backend logic needed already exists in `models.py` or the skills system. This phase is purely about wiring routes to connect frontend JS calls to existing backend functions.

## Common Pitfalls

### Pitfall 1: Auth Decorator Confusion
**What goes wrong:** Using `require_auth` for new endpoints or forgetting to import `login_required`.
**Why it happens:** api.py has its own `require_auth` decorator with the bug. api_v2.py and views.py each define their own `login_required`.
**How to avoid:** For new routes in api.py, either (a) fix `require_auth` to check `session.get('logged_in')`, or (b) define/import a `login_required` matching the v2 pattern. The fix to `require_auth` is the minimum required change.
**Warning signs:** 401 responses when logged in via the dashboard.

### Pitfall 2: Webhook Config Storage Mismatch
**What goes wrong:** Migrating app_legacy.py's in-memory/env-var webhook registry pattern instead of using the existing DB models.
**Why it happens:** app_legacy.py uses `load_webhook_config()` / `save_webhook_config()` with an in-memory dict persisted to Railway env vars. The modular app uses SQLite via `models.upsert_workflow()`.
**How to avoid:** views.py already has a working webhook handler using `models.get_workflow_by_slug()`. New webhook management API routes should use `models.*` functions exclusively.
**Warning signs:** Webhooks created via API not appearing in the workflows page (different storage backends).

### Pitfall 3: Favorites Response Format Mismatch
**What goes wrong:** The toggle endpoint returns a different JSON shape than favorites.js expects.
**Why it happens:** favorites.js expects `{ favorite: true/false }` from toggle, and a plain array of workflow names from GET `/api/favorites`.
**How to avoid:** Read favorites.js carefully:
- Toggle: POST `/api/favorites/toggle` with `{workflow_name}` -- expects `{ favorite: boolean }` in response
- List: GET `/api/favorites` -- expects a JSON array of workflow name strings (not wrapped in an object)
**Warning signs:** Stars don't update visually; console errors about undefined properties.

### Pitfall 4: Google Docs Delivery Endpoint Path
**What goes wrong:** Creating the endpoint at the wrong path or in the wrong blueprint.
**Why it happens:** skill_output.html calls `POST /api/v2/executions/{id}/deliver/gdocs`. This must be in api_v2.py.
**How to avoid:** The endpoint MUST be at `/api/v2/executions/<execution_id>/deliver/gdocs` in api_v2_bp.
**Warning signs:** 404 when clicking "Send to Google Docs" button.

### Pitfall 5: Webhook JS Using fetchAPI vs Raw Fetch
**What goes wrong:** Not considering that webhooks.js uses `fetchAPI()` (from main.js) which auto-sets Content-Type and handles errors.
**Why it happens:** Different JS files use different fetch approaches.
**How to avoid:** webhooks.js uses `fetchAPI()` which parses JSON and throws on non-OK. favorites.js uses raw `fetch()`. Ensure API responses are valid JSON in all cases.
**Warning signs:** Uncaught promise rejections in console.

## Code Examples

### Fix 1: api.py require_auth Session Key (1 Line)

```python
# File: routes/api.py, line 38
# BEFORE (broken):
if session.get('authenticated'):

# AFTER (fixed):
if session.get('logged_in'):
```

Source: Verified by reading views.py:168 which sets `session['logged_in'] = True` and api_v2.py:64 which checks `session.get('logged_in')`.

### Fix 2: Favorites Toggle (Replace Stub)

```python
# File: routes/api.py -- replace existing stub at line 416-450
@api_bp.route('/favorites/toggle', methods=['POST'])
@require_auth('write')  # Works after Fix 1
def api_toggle_favorite():
    data = request.get_json(silent=True) or {}
    workflow_name = data.get('workflow_name', '').strip()

    if not workflow_name:
        return jsonify({"status": "error", "message": "workflow_name required"}), 400

    try:
        if models.is_favorite(workflow_name):
            models.remove_favorite(workflow_name)
            return jsonify({"status": "ok", "favorite": False})
        else:
            models.add_favorite(workflow_name)
            return jsonify({"status": "ok", "favorite": True})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
```

Note: `import models` must be added to api.py (currently not imported).

### Fix 3: Favorites List Endpoint (New)

```python
# File: routes/api.py -- add new route
@api_bp.route('/favorites', methods=['GET'])
@require_auth('read')
def api_get_favorites():
    try:
        favorites = models.get_favorites()  # Returns List[str]
        return jsonify(favorites)  # Plain array, not wrapped
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
```

Source: favorites.js:52-53 calls `GET /api/favorites` and expects a plain JSON array of workflow name strings. It iterates with `favorites.forEach(workflowName => ...)`.

### Fix 4: Google Docs Delivery Endpoint (New)

```python
# File: routes/api_v2.py -- add new route
@api_v2_bp.route('/executions/<execution_id>/deliver/gdocs', methods=['POST'])
@login_required
def api_deliver_gdocs(execution_id):
    """Deliver execution output to Google Docs."""
    try:
        execution = get_execution_status(execution_id)
        if execution is None:
            return jsonify({"status": "error", "message": "Execution not found"}), 404

        # Get output content
        output_path = execution.get("output_path")
        if not output_path:
            return jsonify({"status": "error", "message": "No output file for this execution"}), 400

        full_path = Path(output_path)
        if not full_path.is_absolute():
            full_path = SKILLS_DIR.parent.parent / output_path

        if not full_path.exists():
            return jsonify({"status": "error", "message": "Output file not found"}), 404

        # Call the Google Docs delivery skill
        import subprocess
        skill_name = execution.get("skill_name", "output")
        result = subprocess.run(
            [
                sys.executable,
                str(SKILLS_DIR / "google-doc-delivery" / "create_google_doc.py"),
                "--file", str(full_path),
                "--title", f"{skill_name} - {execution_id[:8]}"
            ],
            capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            return jsonify({
                "status": "error",
                "message": "Google Docs delivery failed",
                "detail": result.stderr[:500]
            }), 500

        # Parse URL from output (skill prints URL)
        url = None
        for line in result.stdout.split('\n'):
            if 'docs.google.com' in line:
                url = line.strip()
                break

        return jsonify({
            "status": "ok",
            "message": "Delivered to Google Docs",
            "url": url
        })
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "Google Docs delivery timed out"}), 504
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
```

Source: skill_output.html:672-686 calls `POST /api/v2/executions/{id}/deliver/gdocs`, expects `{ url: "..." }` in response, opens the URL in a new tab.

### Fix 5: Webhook Management Routes (New, in api.py)

The frontend (webhooks.js) calls these endpoints:
- `GET /api/webhook-workflows` -- list all webhooks
- `POST /api/webhook-workflows/register` -- create/update
- `POST /api/webhook-workflows/unregister` -- delete
- `POST /api/webhook-workflows/toggle` -- enable/disable
- `POST /api/webhook-workflows/test` -- send test payload

```python
# File: routes/api.py -- add new webhook management routes

@api_bp.route('/webhook-workflows', methods=['GET'])
@require_auth('read')
def api_webhook_workflows():
    """List all webhook workflows."""
    try:
        webhooks = models.get_workflows(workflow_type='webhook')
        base_url = request.host_url.rstrip('/')
        result = []
        for wf in webhooks:
            result.append({
                "name": wf['name'],
                "description": wf.get('description', ''),
                "slug": wf.get('webhook_slug'),
                "enabled": wf['status'] == 'active',
                "webhook_url": f"{base_url}/webhook/{wf.get('webhook_slug')}",
                "forward_url": wf.get('forward_url'),
                "slack_notify": bool(wf.get('slack_notify')),
                "source": "Database",
            })
        return jsonify({"webhook_workflows": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route('/webhook-workflows/register', methods=['POST'])
@require_auth('write')
def api_webhook_register():
    """Register or update a webhook workflow."""
    data = request.get_json(silent=True) or {}
    slug = data.get('slug', '').strip().lower().replace(' ', '-')
    name = data.get('name', '').strip()

    if not slug or not name:
        return jsonify({"status": "error", "message": "slug and name required"}), 400

    try:
        # Check if exists
        existing = models.get_workflow_by_slug(slug)

        models.upsert_workflow(
            workflow_id=slug,
            name=name,
            description=data.get('description', f'Webhook: {slug}'),
            workflow_type='webhook',
            status='active' if data.get('enabled', True) else 'paused',
            webhook_slug=slug,
            forward_url=data.get('forward_url'),
            slack_notify=data.get('slack_notify', False),
        )

        base_url = request.host_url.rstrip('/')
        action = "updated" if existing else "registered"
        return jsonify({
            "status": action,
            "slug": slug,
            "name": name,
            "webhook_url": f"{base_url}/webhook/{slug}"
        }), 200 if existing else 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
```

Source: Directly translated from app_legacy.py:5092-5240, adapted to use models.py instead of in-memory registry.

## State of the Art

| Old Approach (app_legacy.py) | Current Approach (modular app) | When Changed | Impact |
|-----|------|------|------|
| In-memory webhook registry with Railway env var persistence | SQLite via `models.upsert_workflow()` | Phase 2+ modular migration | Webhook management must use DB, not memory |
| `session['authenticated']` in api.py | `session['logged_in']` everywhere else | Pre-existing mismatch | 1-line fix in api.py |
| Monolithic `app_legacy.py` (5000+ lines) | Blueprint-based routes (`api.py`, `api_v2.py`, `views.py`) | Modular migration | New routes go in blueprints |
| Favorites as TODO stub | `favorites` table with full CRUD in models.py | Migration 001 created table | Just wire routes to models |

**Key insight:** The database models and schema already support all four features. The modular app's views.py already has a working webhook handler using the DB. Only the API management routes are missing.

## Detailed File Analysis

### What favorites.js Expects

| Endpoint | Method | Request Body | Expected Response |
|----------|--------|-------------|-------------------|
| `/api/favorites/toggle` | POST | `{ workflow_name: string }` | `{ favorite: boolean }` |
| `/api/favorites` | GET | none | `string[]` (plain array of workflow names) |

The toggle response key is `favorite` (not `is_favorite` or `status`). The GET response is a bare array, not `{ favorites: [...] }`.

### What webhooks.js Expects

| Endpoint | Method | Request Body | Expected Response |
|----------|--------|-------------|-------------------|
| `/api/webhook-workflows` | GET | none | `{ webhook_workflows: [{name, description, slug, enabled, webhook_url, forward_url, slack_notify, source}] }` |
| `/api/webhook-workflows/register` | POST | `{ slug, name, description, source, slack_notify, forward_url, enabled }` | `{ status: "registered"/"updated", slug, name, webhook_url }` |
| `/api/webhook-workflows/unregister` | POST | `{ slug }` | `{ status: "unregistered", slug, name }` |
| `/api/webhook-workflows/toggle` | POST | `{ slug }` | `{ slug, enabled: boolean, name }` |
| `/api/webhook-workflows/test` | POST | `{ slug }` | `{ slug, test_status: "success"/"failed"/"error", response_code, response }` |

### What skill_output.html Expects

| Endpoint | Method | Request Body | Expected Response |
|----------|--------|-------------|-------------------|
| `/api/v2/executions/{id}/deliver/gdocs` | POST | none | `{ url: string }` |

On success, opens `data.url` in new tab. On failure, shows "Could not send to Google Docs" toast.

### models.py Functions Already Available

| Function | Signature | Returns | Used For |
|----------|-----------|---------|----------|
| `add_favorite(workflow_name)` | str -> int | row count | Add to favorites |
| `remove_favorite(workflow_name)` | str -> int | row count | Remove from favorites |
| `get_favorites()` | () -> List[str] | workflow name list | List favorites |
| `is_favorite(workflow_name)` | str -> bool | True/False | Check before toggle |
| `get_workflows(workflow_type='webhook')` | -> List[Dict] | workflow dicts | List webhooks |
| `get_workflow_by_slug(slug)` | str -> Optional[Dict] | workflow or None | Lookup webhook |
| `upsert_workflow(...)` | many params -> int | row count | Create/update webhook |
| `delete_workflow(workflow_id)` | str -> int | row count | Soft-delete webhook |
| `update_workflow_status(id, status)` | str, str -> int | row count | Toggle webhook |
| `get_skill_execution(execution_id)` | str -> Optional[Dict] | execution data | Google Docs delivery |

### Import Requirements for api.py

api.py currently does NOT import `models`. It needs:
```python
import models
```
added near the top (after the `sys.path.insert` line), matching the pattern in api_v2.py.

## Open Questions

1. **Google Docs credentials in Railway**
   - What we know: The `create_google_doc.py` skill requires `credentials.json` or `GOOGLE_APPLICATION_CREDENTIALS`. The endpoint can gracefully fail if not configured.
   - What's unclear: Whether the Railway deployment has Google credentials configured.
   - Recommendation: Implement the endpoint, return a clear error message if credentials are missing. This matches the "degrade gracefully" error handling pattern.

2. **Webhook test endpoint -- self-POST safety**
   - What we know: app_legacy.py's test endpoint POSTs to itself (`{base_url}/webhook/{slug}`). This could cause issues if the webhook handler forwards to an external URL during testing.
   - What's unclear: Whether test payloads should be marked differently to prevent external forwarding.
   - Recommendation: Include `"test": true` in the test payload (matching app_legacy.py pattern) and optionally skip forwarding for test requests in the webhook handler.

3. **Favorites frontend uses raw fetch() not fetchAPI()**
   - What we know: favorites.js uses raw `fetch()` while webhooks.js uses `fetchAPI()`. After the auth fix, raw fetch will work but won't have timeout/retry.
   - What's unclear: Whether favorites.js should be migrated to use fetchAPI() as part of this phase.
   - Recommendation: Keep scope minimal -- just fix the backend. Frontend JS migration to fetchAPI() is P3 code quality tech debt.

## Sources

### Primary (HIGH confidence)
- `routes/api.py` lines 26-52 -- `require_auth` decorator with `session.get('authenticated')` bug
- `routes/api_v2.py` lines 59-71 -- `login_required` decorator with correct `session.get('logged_in')`
- `routes/views.py` lines 159-196 -- login handler setting `session['logged_in'] = True`
- `models.py` lines 422-448 -- favorites CRUD functions (add, remove, get, is_favorite)
- `models.py` lines 16-111 -- workflow CRUD functions (get, upsert, delete, update)
- `static/js/favorites.js` lines 1-72 -- full frontend favorites contract
- `static/js/webhooks.js` lines 1-200 -- full frontend webhook management contract
- `templates/skill_output.html` lines 672-686 -- Google Docs delivery frontend call
- `app_legacy.py` lines 5092-5240 -- webhook management routes to migrate
- `app_legacy.py` lines 235-341 -- legacy in-memory webhook registry (NOT to use)
- `migrations/001_initial.sql` line 113 -- favorites table schema
- `.planning/v1-MILESTONE-AUDIT.md` -- authoritative list of issues

### Secondary (MEDIUM confidence)
- `.claude/skills/google-doc-delivery/SKILL.md` -- Google Docs delivery skill interface
- `.claude/skills/google-doc-delivery/create_google_doc.py` -- implementation details

## Metadata

**Confidence breakdown:**
- Auth fix: HIGH -- verified by reading all three files (api.py, api_v2.py, views.py)
- Favorites wiring: HIGH -- models exist, JS contract is clear, table exists
- Google Docs delivery: MEDIUM -- endpoint pattern is clear, but subprocess invocation of skill may need adjustment based on create_google_doc.py output format
- Webhook migration: HIGH -- legacy routes are straightforward, models.py already has all needed functions, views.py webhook handler already uses DB

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable -- internal codebase, no external dependency changes)
