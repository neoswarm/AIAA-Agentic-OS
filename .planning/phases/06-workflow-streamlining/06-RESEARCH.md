# Phase 6: Workflow Streamlining - Research

**Researched:** 2026-02-23
**Domain:** Flask/Jinja2 dashboard UX -- reducing clicks and guesswork for common user paths
**Confidence:** HIGH

## Summary

This phase adds five workflow-streamlining features to an existing Flask 3.0 + Jinja2 + vanilla JS dashboard. The codebase is mature with established patterns for API endpoints, localStorage-based client state, SQLite persistence, and server-rendered templates enhanced with fetch-based JS. Every requirement maps to existing code patterns -- no new libraries, frameworks, or architecture are needed.

The dashboard already has partial infrastructure for each requirement: a "Re-run" button exists but only navigates to the skill form without pre-filling parameters; a favorites system exists using both `localStorage` (dashboard_v2.html) and a SQLite `favorites` table (workflow_catalog.html) creating a dual-storage inconsistency that must be resolved; category chips on the dashboard link to `/workflows?category=X` (the legacy workflow catalog) instead of the skill catalog at `/skills?category=X`; onboarding step 4 links to the dashboard but does not redirect automatically; and the client selector does not exist on the skill execution page.

**Primary recommendation:** Each requirement is a self-contained frontend enhancement with a small API addition. The favorites system needs consolidation to a single storage mechanism (localStorage, matching the existing dashboard pattern and the "Welcome banner dismissal stored in localStorage" decision). The "Run Again" feature requires the execution output API to return the original params, which are already stored in `skill_executions.params`.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.0.0 | Web framework | Already in use, all routes in views.py |
| Jinja2 | (bundled) | Server-side templates | All pages extend base.html |
| Vanilla JS | ES6+ | Client-side interactivity | Project decision: no React/Vue |
| SQLite | (stdlib) | Persistence | Project decision: no Postgres |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| localStorage | (browser) | Client-side favorites, banner dismissal | Favorites, welcome state |
| CSS custom properties | (browser) | Theming | All new UI elements should use var(--*) tokens |
| fetchAPI() wrapper | main.js | API calls with auto-toast | All JS-initiated API calls |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| localStorage for favorites | SQLite favorites table | SQLite already exists but dashboard reads from localStorage; localStorage is simpler, matches decision pattern, works offline |
| URL query params for pre-fill | sessionStorage | Query params are linkable/shareable; sessionStorage is tab-scoped and lost on navigate |

**Installation:**
No new dependencies required. All work uses existing stack.

## Architecture Patterns

### Recommended Project Structure
```
railway_apps/aiaa_dashboard/
├── routes/
│   ├── views.py           # Add/modify: skill_run (query param support), onboarding redirect
│   └── api_v2.py          # Add: favorites API (localStorage sync optional), client list endpoint tweaks
├── templates/
│   ├── skill_output.html   # FLOW-01: "Run Again" button with pre-fill
│   ├── dashboard_v2.html   # FLOW-02: favorites display, FLOW-03: category links fix
│   ├── skill_execute.html  # FLOW-01: read pre-fill params, FLOW-05: client selector
│   └── onboarding.html     # FLOW-04: auto-redirect after completion
├── static/js/
│   ├── main.js             # Shared utilities (unchanged)
│   └── favorites.js        # FLOW-02: consolidate favorites logic
└── migrations/
    └── (no new migration needed -- params already in skill_executions table)
```

### Pattern 1: URL Query Params for Pre-filling Forms
**What:** Pass execution parameters via URL query string from output page to execution page
**When to use:** FLOW-01 "Run Again" -- user wants to re-execute with same params
**Example:**
```javascript
// Source: existing skill_output.html pattern (line 604)
// CURRENT (broken -- just navigates to form with no params):
document.getElementById('btn-rerun').href = '/skills/' + encodeURIComponent(data.skill_name) + '/execute';

// NEW (pre-fills form via query params):
var rerunUrl = '/skills/' + encodeURIComponent(data.skill_name || skillName) + '/run';
if (data.params) {
    var params = typeof data.params === 'string' ? JSON.parse(data.params) : data.params;
    var qs = new URLSearchParams(params).toString();
    if (qs) rerunUrl += '?' + qs;
}
document.getElementById('btn-rerun').href = rerunUrl;

// On skill_execute.html -- read query params and pre-fill fields:
function prefillFromQueryParams() {
    var params = new URLSearchParams(window.location.search);
    params.forEach(function(value, key) {
        var field = document.getElementById('field-' + key);
        if (field) field.value = value;
    });
}
```

### Pattern 2: localStorage Favorites with Dashboard Rendering
**What:** Store favorites as a JSON array in localStorage, render on dashboard load
**When to use:** FLOW-02 -- favorites persist client-side and display on home page
**Example:**
```javascript
// Source: existing dashboard_v2.html pattern (lines 706-725)
// CURRENT: reads from localStorage('skill_favorites'), renders favorite links
// This is already working -- just needs:
// 1. A way to toggle favorites from skill cards (star icon)
// 2. Consistent key name across all pages
// 3. Empty state CTA when no favorites exist

var FAVORITES_KEY = 'skill_favorites';

function getFavorites() {
    try {
        return JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]');
    } catch (e) { return []; }
}

function toggleFavorite(skillName) {
    var favs = getFavorites();
    var idx = favs.indexOf(skillName);
    if (idx === -1) {
        favs.push(skillName);
    } else {
        favs.splice(idx, 1);
    }
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(favs));
    return idx === -1; // true if added
}
```

### Pattern 3: Category Filter via URL Query Param
**What:** Dashboard category chips link to `/skills?category=X` and the skill catalog reads the query param
**When to use:** FLOW-03 -- clicking a category on home navigates to filtered skill catalog
**Example:**
```javascript
// Source: existing dashboard_v2.html renderCategories (line 739)
// CURRENT: links to /workflows?category=X (legacy page)
// FIX: change href to /skills?category=X

chip.href = '/skills?category=' + encodeURIComponent(cat);

// On skill catalog -- already handled server-side in views.py line 521:
// category_filter = request.args.get('category')
// skills = [s for s in skills if s.get('category') == category_filter]
```

### Pattern 4: Post-Onboarding Redirect with First-Run Flag
**What:** After onboarding step 4, redirect to dashboard and show welcome banner
**When to use:** FLOW-04 -- new user completes onboarding
**Example:**
```javascript
// Source: existing onboarding.html (line 653)
// CURRENT: button manually navigates: onclick="window.location.href='/'"
// ENHANCED: set first-run flag and redirect to dashboard

function completeOnboarding() {
    localStorage.setItem('onboarding_completed', '1');
    // Don't dismiss welcome banner -- let it show on first dashboard visit
    localStorage.removeItem('welcome_banner_dismissed');
    window.location.href = '/home';
}
```

### Pattern 5: Client Selector Dropdown via API
**What:** Fetch clients from `/api/v2/clients` and render a `<select>` on the skill execution page
**When to use:** FLOW-05 -- user selects a client before running a skill
**Example:**
```javascript
// Source: existing API pattern from api_v2.py (line 537-553)
// Fetch clients and render dropdown above the skill form

async function loadClientSelector() {
    try {
        var data = await fetchAPI('/api/v2/clients');
        var clients = data.clients || [];
        if (clients.length === 0) return; // Hide selector if no clients

        var select = document.getElementById('client-selector');
        clients.forEach(function(client) {
            var opt = document.createElement('option');
            opt.value = client.slug;
            opt.textContent = client.name;
            select.appendChild(opt);
        });
        document.getElementById('client-selector-group').style.display = 'block';
    } catch (e) {
        // Silently fail -- client selector is optional
    }
}
```

### Anti-Patterns to Avoid
- **Dual storage for favorites:** The codebase has BOTH localStorage (`dashboard_v2.html`) and SQLite table (`favorites` in 001_initial.sql + `favorites.js`). Pick one. Per decisions: use localStorage (consistent with welcome banner pattern).
- **Inline fetch calls without fetchAPI:** All new API calls MUST use the `fetchAPI()` wrapper from main.js which handles timeouts, error toasts, and retries.
- **Hard-coding skill routes:** Use `encodeURIComponent()` for skill names in URLs -- names contain hyphens and special chars.
- **Breaking the Re-run link pattern:** The current Re-run button links to `/skills/{name}/execute` which is the wrong route. The correct route is `/skills/{name}/run` (see views.py line 536).

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API fetch with error handling | Raw `fetch()` calls | `fetchAPI()` from main.js | Auto-toast, timeout, retry built in |
| Button loading states | Manual disabled/text toggle | `setButtonLoading()` from main.js | Handles spinner SVG, stores/restores original state |
| Confirmation dialogs | Custom modal HTML | `confirmAction()` from main.js | Promise-based, consistent styling |
| URL query param parsing | Manual string splitting | `getQueryParams()` from main.js | Already exists and handles edge cases |
| URL param updating | Manual history.pushState | `updateQueryParams()` from main.js | Handles null removal, proper URL construction |
| Client-side form data collection | Manual DOM traversal | `getFormData()` / `setFormData()` from main.js | Handles checkboxes, all input types |
| Debouncing search/filter | setTimeout/clearTimeout | `debounce()` from main.js | Already used in clients.js |
| Date formatting | Manual date math | `formatDate()` from main.js | Relative time display (Xm ago, Xh ago) |
| Clipboard operations | Manual textarea fallback | `copyToClipboard()` from main.js | Has fallback for older browsers |

**Key insight:** main.js is loaded globally via base.html script tag and exports 13 utility functions to `window.*`. Every common UI operation has a helper. Check main.js before writing any utility code.

## Common Pitfalls

### Pitfall 1: Favorites System Dual Storage
**What goes wrong:** The `favorites.js` file uses `/api/favorites/toggle` (server-side SQLite), while `dashboard_v2.html` reads from `localStorage('skill_favorites')`. These can desync.
**Why it happens:** Two different implementations were built at different times for different pages.
**How to avoid:** Consolidate on localStorage. The dashboard home already reads from localStorage, and the "Welcome banner dismissal stored in localStorage" decision confirms this as the pattern. Remove or ignore the SQLite favorites table for skill favorites (keep it for legacy workflow favorites on `/workflows` page if needed).
**Warning signs:** User favorites appear on one page but not another.

### Pitfall 2: Re-run URL Points to Wrong Route
**What goes wrong:** The current `btn-rerun` in skill_output.html builds a URL to `/skills/{name}/execute` but the actual route is `/skills/{name}/run`.
**Why it happens:** Typo or route rename that wasn't propagated.
**How to avoid:** Verify route against views.py. The route is `@views_bp.route('/skills/<skill_name>/run')` at line 536.
**Warning signs:** "Run Again" button gives a 404.

### Pitfall 3: Execution Output API Missing Params
**What goes wrong:** The "Run Again" feature needs the original execution params, but the `/api/v2/executions/<id>/output` endpoint (api_v2.py line 219) returns `output_content`, `output_path`, `output_preview` -- NOT the original `params`.
**Why it happens:** The output endpoint was designed for viewing output, not for re-execution.
**How to avoid:** Either modify the output endpoint to also return `params` from the `skill_executions` table (which stores them as JSON in the `params` column), or fetch them from a separate call to the status endpoint.
**Warning signs:** "Run Again" navigates to form but all fields are empty.

### Pitfall 4: Onboarding Page Doesn't Use base.html
**What goes wrong:** `onboarding.html` is a standalone page (not extending base.html). It has its own theme system, fonts, and no sidebar. Changes to base.html won't affect it.
**Why it happens:** Onboarding was designed as a full-screen wizard separate from the authenticated dashboard.
**How to avoid:** Keep onboarding standalone but ensure the redirect goes to `/home` (the authenticated dashboard) not `/` (which also redirects to `/home` but adds an unnecessary hop).
**Warning signs:** None -- this is intentional design, just document it.

### Pitfall 5: Category Links Pointing to Legacy Page
**What goes wrong:** Dashboard category chips link to `/workflows?category=X` (the legacy workflow catalog page) instead of `/skills?category=X` (the v2 skill catalog).
**Why it happens:** The dashboard_v2.html `renderCategories()` function at line 739 uses `/workflows?category=` as the href target.
**How to avoid:** Change the href to `/skills?category=`. The `/skills` route in views.py (line 512-533) already supports `?category=` filtering server-side.
**Warning signs:** User clicks a category on dashboard, lands on legacy workflow page instead of skill catalog.

### Pitfall 6: Client Selector Auth Requirements
**What goes wrong:** The `/api/v2/clients` endpoint requires authentication (`@login_required`). If the user's session expires mid-page, the client selector will fail silently.
**Why it happens:** API auth is strict by design.
**How to avoid:** Use `fetchAPI()` which auto-toasts on errors. The client selector should degrade gracefully -- if the API call fails, the skill form still works without it.
**Warning signs:** Client dropdown shows nothing, no error visible.

## Code Examples

Verified patterns from the existing codebase:

### Reading Execution Params for Re-run (Backend Change Needed)
```python
# Source: api_v2.py - execution output endpoint
# Current response does NOT include params. Add this:
@api_v2_bp.route('/executions/<execution_id>/output', methods=['GET'])
@login_required
def api_execution_output(execution_id):
    execution = get_execution_status(execution_id)
    # ... existing code ...
    return jsonify({
        "status": "ok",
        "execution_id": execution_id,
        "skill_name": execution.get("skill_name"),
        "params": execution.get("params"),  # ADD THIS LINE
        "output_content": output_content,
        # ... rest unchanged ...
    })
```

### Pre-filling Form from URL Query Params
```javascript
// Source: skill_execute.html - add after buildForm() completes
// Uses existing getQueryParams() from main.js
function prefillFromQueryParams() {
    var params = getQueryParams();
    Object.keys(params).forEach(function(key) {
        var field = document.getElementById('field-' + key);
        if (field) {
            field.value = decodeURIComponent(params[key]);
        }
    });
}
// Call after form fields are rendered:
// buildForm(skillMeta.inputs || []);
// prefillFromQueryParams();
```

### Dashboard Favorites with Empty State CTA
```javascript
// Source: dashboard_v2.html loadFavorites pattern (line 705-725)
// Enhanced with actionable empty state
async function loadFavorites() {
    var stored = localStorage.getItem('skill_favorites');
    var favs = [];
    try { favs = JSON.parse(stored || '[]'); } catch (e) {}

    if (!Array.isArray(favs) || favs.length === 0) {
        favoritesList.innerHTML = '<div class="empty-hint">'
            + '<div style="margin-bottom: 0.5rem;">'
            + '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color: var(--text-muted);">'
            + '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>'
            + '</svg></div>'
            + '<div style="font-weight: 500; color: var(--text-primary); margin-bottom: 0.25rem;">No favorites yet</div>'
            + '<div>Star your most-used skills for quick access.</div>'
            + '<a href="/skills" class="btn" style="margin-top: 0.75rem; font-size: 0.75rem; padding: 0.5rem 1rem;">Browse Skills</a>'
            + '</div>';
        return;
    }
    // ... render favorites list as already implemented
}
```

### Client Selector HTML Structure
```html
<!-- Source: skill_execute.html - add before mode-tabs -->
<div class="field-group" id="client-selector-group" style="display: none; margin-bottom: 1.5rem;">
    <label class="field-label">
        Client
        <span class="field-tooltip" data-tip="Select a client to apply their profile settings to this skill run">?</span>
    </label>
    <select class="field-select" id="client-selector" name="client">
        <option value="">No client (general)</option>
        <!-- Populated by JS -->
    </select>
    <span class="field-hint">Optional: select a client to customize the output for their brand.</span>
</div>
```

### Onboarding Completion Redirect
```javascript
// Source: onboarding.html - replace the "Go to Dashboard" button onclick
// Current (line 653): onclick="window.location.href='/'"
// New:
function completeOnboarding() {
    localStorage.setItem('onboarding_completed', '1');
    window.location.href = '/home';
}
// Button: onclick="completeOnboarding()"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `/workflows?category=X` for categories | `/skills?category=X` for skill catalog | Phase 6 | Category links target correct v2 page |
| Re-run navigates to blank form | Re-run pre-fills with previous params | Phase 6 | Saves user from re-entering all fields |
| Favorites in SQLite (`favorites.js`) | Favorites in localStorage (dashboard_v2) | Phase 6 | Single source of truth, works offline |
| Manual onboarding-to-dashboard | Auto-redirect with first-run guidance | Phase 6 | Smoother first-time experience |
| No client context on skill run | Client selector dropdown | Phase 6 | Client-specific runs without manual input |

**Deprecated/outdated:**
- `favorites.js` server-side toggle pattern (`/api/favorites/toggle`): This uses a server API that talks to the SQLite favorites table. The dashboard_v2.html already uses localStorage. The `favorites.js` file should be refactored to use localStorage instead, OR kept only for the legacy `/workflows` page.
- `/skills/{name}/execute` URL: This appears in the output page Re-run button but is NOT a valid route. The correct route is `/skills/{name}/run`.

## Requirement-by-Requirement Analysis

### FLOW-01: "Run Again" Button Pre-fills Form
**Current state:** `skill_output.html` line 604 builds a Re-run link to `/skills/{name}/execute` (wrong route, no params).
**Data availability:** `skill_executions` table stores `params` as JSON. The output API needs to return this field.
**Implementation approach:**
1. Modify `api_execution_output()` in api_v2.py to include `params` and `skill_name` in response
2. In `skill_output.html`, build Re-run URL with query params: `/skills/{name}/run?param1=val1&param2=val2`
3. In `skill_execute.html`, after form is built, read query params and pre-fill matching fields
**Confidence:** HIGH -- data exists, patterns exist, straightforward

### FLOW-02: Favorites on Dashboard Home
**Current state:** `dashboard_v2.html` lines 705-725 already loads favorites from localStorage and renders them. `favorites.js` uses a different server-side mechanism.
**Implementation approach:**
1. Consolidate on localStorage key `skill_favorites` (array of skill name strings)
2. Add star toggle icon to quick-start cards and search results on dashboard
3. Add actionable empty state CTA in favorites section
4. Ensure favorites links use `/skills/{name}/run` (correct route)
**Confidence:** HIGH -- mostly already implemented, needs polish

### FLOW-03: Category Links to Filtered Catalog
**Current state:** `dashboard_v2.html` line 739 renders category chips with `href="/workflows?category=..."`. The `/skills` route in views.py already supports `?category=` filtering.
**Implementation approach:**
1. Change one line in `renderCategories()`: `chip.href = '/skills?category=' + encodeURIComponent(cat);`
2. Verify the skill catalog page properly reads and displays the active filter
**Confidence:** HIGH -- one-line fix, server-side support already exists

### FLOW-04: Post-Onboarding Dashboard Landing
**Current state:** `onboarding.html` step 4 has a "Go to Dashboard" button that navigates to `/`. The welcome banner on `dashboard_v2.html` shows for first visitors (via localStorage check).
**Implementation approach:**
1. Change the onboarding completion button to call `completeOnboarding()` which sets localStorage flags and redirects to `/home`
2. Enhance the welcome banner with first-run guidance steps (already has step cards)
3. Optionally: make the "Skip -- I'll explore on my own" links on steps 1-3 also redirect to `/home` with welcome banner
**Confidence:** HIGH -- standalone page, minimal changes

### FLOW-05: Client Selector on Skill Execution Page
**Current state:** No client selector exists on `skill_execute.html`. The `/api/v2/clients` endpoint exists and returns client list. Client data includes name, slug, industry, website.
**Implementation approach:**
1. Add a `<select>` dropdown above the skill form in `skill_execute.html`
2. Load clients from API on page init
3. When a client is selected, optionally populate relevant form fields (e.g., company name, website)
4. Include `client` param in the execution POST body
5. Hide the selector if no clients exist (graceful degradation)
**Confidence:** HIGH -- API exists, form patterns exist

## Open Questions

Things that couldn't be fully resolved:

1. **Should client selection auto-fill form fields?**
   - What we know: Client profiles have fields like `name`, `website`, `industry`, `target_audience`, `brand_voice` that could map to skill input fields
   - What's unclear: The mapping between client profile fields and skill input field names is not standardized -- each skill defines its own inputs
   - Recommendation: Start with just passing `client` as a parameter. Auto-fill can be added later if skill input schemas stabilize around common field names (e.g., `company`, `website`).

2. **Should favorites sync across devices?**
   - What we know: localStorage is device-local. The SQLite favorites table exists but is used for legacy workflows.
   - What's unclear: Whether multi-device sync is expected
   - Recommendation: Keep localStorage per the prior decision. Multi-device sync is a deferred enhancement if needed.

3. **Should the Re-run URL include ALL params or just user-provided ones?**
   - What we know: The `params` column in skill_executions stores the full params JSON (including defaults)
   - What's unclear: Whether including default values in the URL could cause issues if defaults change between runs
   - Recommendation: Include all params. If a default changes, the user can still edit the pre-filled value before running.

## Sources

### Primary (HIGH confidence)
- **Codebase direct inspection:** All findings verified by reading source files
  - `skill_output.html` -- Re-run button implementation (line 604)
  - `dashboard_v2.html` -- Favorites, category chips, welcome banner (lines 706-739)
  - `skill_execute.html` -- Form building, field rendering (lines 619-747)
  - `onboarding.html` -- Step navigation, completion flow (lines 658-741)
  - `views.py` -- Route definitions (lines 512-563, 726-732)
  - `api_v2.py` -- API endpoints (lines 219-251, 537-553)
  - `models.py` -- Favorites and skill execution models (lines 426-580)
  - `main.js` -- Shared utilities (13 functions exported to window.*)
  - `favorites.js` -- Legacy server-side favorites toggle
  - `migrations/002_skill_execution.sql` -- skill_executions schema with params column

### Secondary (MEDIUM confidence)
- None -- all findings are from direct codebase inspection

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- codebase is well-understood, no new dependencies
- Architecture: HIGH -- all patterns already exist in codebase, extending not creating
- Pitfalls: HIGH -- identified from direct code reading, specific line numbers cited
- Code examples: HIGH -- based on actual existing code patterns with minimal modification

**Research date:** 2026-02-23
**Valid until:** Indefinite (codebase-specific research, not library-dependent)
