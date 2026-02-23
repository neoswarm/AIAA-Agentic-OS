# Phase 7: Skill Discovery - Research

**Researched:** 2026-02-23
**Domain:** Client-side search, skill metadata enrichment, role-based recommendations, Jinja2/vanilla JS UI
**Confidence:** HIGH

## Summary

Phase 7 enhances the skill discovery experience across three surfaces: the dashboard home page (`dashboard_v2.html`), the workflow catalog (`workflow_catalog.html`), and the skill execution detail page (`skill_execute.html`). The codebase already has a working search implementation on the dashboard (client-side filter over `allSkills` array fetched from `/api/v2/skills`) and a separate DOM-based filter on the catalog page. Neither supports partial matching or synonyms.

The standard approach for this phase is to enhance the existing `search_skills()` backend function with synonym mapping and improved partial matching, then consume the improved API from the frontend. Skill metadata (run time, complexity) does not currently exist in SKILL.md frontmatter or the parsed skill data but CAN be derived from the `process_steps` count (already used by the `/estimate` endpoint) and prerequisites. The user role preference is already saved during onboarding as `pref.role` in the `user_settings` table and can be read via `/api/v2/settings/preferences`.

**Primary recommendation:** Build a synonym dictionary and enhanced search scorer in `skill_execution_service.py`, enrich `list_available_skills()` return data with computed `estimated_minutes` and `complexity` fields, and wire a role-based recommendation section into the dashboard using the existing `pref.role` setting.

## Standard Stack

This phase uses ONLY the existing stack. No new libraries needed.

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.0.0 | Backend routes and API | Already in use |
| Jinja2 | (bundled with Flask) | Server-side templates | Already in use |
| SQLite | (stdlib) | Data persistence | Already in use |
| Vanilla JS | ES6+ | Client-side interactivity | Decision: no framework migration |

### Supporting (already present)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `main.js` | N/A | Shared utils (debounce, fetchAPI, showToast, escapeHtml) | All JS pages |
| `favorites.js` | N/A | Favorite toggle logic | Catalog page |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom synonym map | Fuse.js (fuzzy search library) | Adds 24KB dependency; 133 skills is small enough for a hand-rolled scorer |
| Custom complexity calc | SKILL.md frontmatter field | Would require editing 133 SKILL.md files; derived calculation is simpler |
| Server-side search API | Client-side only search | Server-side already exists at `/api/v2/skills/search`; should enhance it and use from frontend |

**Installation:** None required. No new packages.

## Architecture Patterns

### Current Architecture (what exists)

```
dashboard_v2.html
  JS: fetch('/api/v2/skills') -> allSkills[]
  JS: client-side filter via .includes() on name/desc/category
  300ms setTimeout debounce (matches project convention)

workflow_catalog.html
  Jinja2: server-renders all cards
  JS: DOM-based filterWorkflows() with .includes()
  No debounce (instant DOM filter)

skill_execute.html
  JS: fetch('/api/v2/skills/{name}') -> skill detail
  Shows: name, description, category badge, input form
  Missing: run time, complexity, output preview

Backend:
  skill_execution_service.py:
    search_skills(query) -> token-based scoring
    parse_skill_md(name) -> full skill metadata
    list_available_skills() -> all skills with light metadata
  api_v2.py:
    GET /api/v2/skills -> list all
    GET /api/v2/skills/search?q= -> search
    GET /api/v2/skills/{name} -> detail
    GET /api/v2/skills/{name}/estimate -> time/cost estimate
```

### Recommended Enhancement Pattern

```
skill_execution_service.py
  + SYNONYM_MAP dict (maps common terms to skill name tokens)
  + _compute_complexity(skill) -> "simple" | "moderate" | "advanced"
  + _estimate_minutes(skill) -> int
  + Enhanced search_skills() with synonym expansion + partial matching
  + Enhanced list_available_skills() returns estimated_minutes + complexity

api_v2.py
  + GET /api/v2/skills/recommended -> role-based recommendations
  (or add ?role= param to existing /api/v2/skills endpoint)

dashboard_v2.html
  + "Recommended for You" section (uses pref.role)
  + Enhanced search uses synonym-aware API endpoint
  + Search results show estimated time + complexity badge

workflow_catalog.html (or a new skill_catalog.html)
  + Skill cards show estimated_minutes + complexity indicator
  + Search uses the enhanced backend

skill_execute.html
  + Output preview section (from SKILL.md Outputs section or description)
  + Estimated run time + complexity shown in header
```

### Pattern 1: Synonym Map for Skill Search
**What:** A static dictionary mapping common user terms to skill-name tokens
**When to use:** When the user types "email" and expects to find "cold-email-campaign"
**Example:**
```python
# In skill_execution_service.py
SYNONYM_MAP = {
    # Common terms -> skill name fragments they should match
    "email": ["cold-email", "email-sequence", "email-deliverability", "email-validator",
              "email-reply", "email-autoreply", "ecommerce-email", "campaign-launcher",
              "follow-up", "webinar-followup"],
    "blog": ["blog-post", "content", "newsletter"],
    "research": ["company-research", "market-research", "niche-research",
                  "prospect-research", "competitor-monitor"],
    "video": ["vsl", "youtube", "reel", "thumbnail", "video-ad"],
    "social": ["linkedin", "twitter", "instagram", "carousel-post", "x-youtube"],
    "funnel": ["vsl-funnel", "landing-page"],
    "outreach": ["cold-email", "cold-dm", "linkedin-lead"],
    "ads": ["ad-creative", "meta-ads", "google-ads", "static-ad", "fb-ad", "video-ad"],
    "lead": ["lead-list-builder", "scraping", "gmaps", "crunchbase", "job-board",
             "linkedin-lead", "funding-tracker"],
    "seo": ["seo-audit", "blog-post", "content"],
    "proposal": ["proposal", "pricing", "sales-deck"],
    "newsletter": ["newsletter", "ai-news-digest", "rss"],
    "image": ["ai-image-generator", "thumbnail", "static-ad"],
    "automation": ["automation-builder", "n8n", "webhook", "task-assignment"],
    "client": ["client-onboarding", "client-feedback", "client-health",
               "client-report", "churn-alert"],
    "write": ["blog-post", "case-study", "press-release", "product-description",
              "newsletter", "faq", "cold-email-campaign"],
}
```

### Pattern 2: Complexity Derivation from SKILL.md
**What:** Compute complexity from existing metadata rather than adding new frontmatter
**When to use:** For DISC-02 (complexity indicator on skill cards)
**Example:**
```python
def _compute_complexity(skill_data: dict) -> str:
    """Derive complexity from process steps and prerequisites."""
    steps = len(skill_data.get("process_steps", []))
    prereqs = len(skill_data.get("prerequisites", []))
    inputs_required = sum(1 for i in (skill_data.get("inputs") or []) if i.get("required"))

    score = steps + prereqs + inputs_required
    if score <= 5:
        return "simple"
    elif score <= 10:
        return "moderate"
    else:
        return "advanced"


def _estimate_minutes(skill_data: dict) -> int:
    """Estimate run time from process steps (~30s per step, min 1 minute)."""
    steps = len(skill_data.get("process_steps", []))
    # Existing logic from /estimate endpoint: max(steps * 30, 60) seconds
    return max(steps // 2, 1)  # In minutes, rounded
```

### Pattern 3: Role-Based Recommendations
**What:** Map user roles to relevant skill categories
**When to use:** For DISC-03 (dashboard highlights popular/recommended skills)
**Example:**
```python
ROLE_SKILL_MAP = {
    "marketing": ["content", "social", "email", "ads", "video"],
    "sales": ["sales", "leads", "email", "research"],
    "operations": ["automation", "deploy", "client"],
    "executive": ["research", "client", "content"],
}

def get_recommended_skills(role: str, limit: int = 8) -> list:
    """Get skills recommended for a user role."""
    categories = ROLE_SKILL_MAP.get(role, [])
    skills = list_available_skills()
    recommended = [s for s in skills if s["category"] in categories]
    # Sort by relevance (category order priority)
    recommended.sort(key=lambda s: (
        categories.index(s["category"]) if s["category"] in categories else 99
    ))
    return recommended[:limit]
```

### Anti-Patterns to Avoid
- **Building a search index for 133 items:** Overkill. A simple scorer with synonym expansion handles this scale trivially.
- **Adding Fuse.js or Lunr.js:** Adds external dependency for a problem solvable with ~50 lines of vanilla JS/Python.
- **Editing 133 SKILL.md files to add metadata:** Fragile and high effort. Derive from existing data.
- **Moving search entirely client-side:** The backend already has `search_skills()`. Enhance it server-side and call from frontend. Server-side search is more maintainable and keeps synonym logic centralized.
- **Using raw innerHTML without escapeHtml():** Project convention requires `escapeHtml()` for all user-derived content. Existing code already follows this pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Debounce | Custom timer logic | `debounce()` from `main.js` | Already exists globally, 300ms default |
| Toast notifications | Custom notification UI | `showToast()` from `main.js` | Single source of truth per project convention |
| HTML escaping | Template literals with raw text | `escapeHtml()` local function (already in dashboard_v2.html and skill_execute.html) | XSS prevention is a project requirement |
| API calls | Raw `fetch()` | `fetchAPI()` from `main.js` for new fetch calls; existing code in dashboard_v2 uses raw fetch (keep consistent) | Auto-toast on error, timeout handling |
| Skill name formatting | Custom formatter | `formatSkillName()` already in dashboard_v2.html and skill_execute.html | Converts kebab-case to Title Case |
| Cost estimation | New calculation | Existing `/api/v2/skills/{name}/estimate` endpoint | Already uses step count to estimate |
| User role reading | New endpoint | `GET /api/v2/settings/preferences` returns `pref.role` | Onboarding already saves role here |

## Common Pitfalls

### Pitfall 1: Two Divergent Search Implementations
**What goes wrong:** Dashboard and catalog each have their own search logic. Adding synonym support to one but not the other creates inconsistency.
**Why it happens:** Dashboard uses client-side JS filter; catalog uses DOM-based filter. Both use `.includes()` and neither calls the backend `search_skills()` endpoint.
**How to avoid:** Centralize enhanced search on the backend (`/api/v2/skills/search?q=`). Have dashboard JS call the API (with debounce) instead of filtering `allSkills` locally. Keep catalog's DOM filter for instant category toggling but enhance with the same synonym logic client-side if needed.
**Warning signs:** "email" finds results on dashboard but not catalog, or vice versa.

### Pitfall 2: Synonym Map Gets Stale
**What goes wrong:** New skills are added but synonym map is not updated.
**Why it happens:** Synonym map is a static dict; skill dirs are dynamic.
**How to avoid:** Build synonym map from CATEGORY_KEYWORDS (already exists) as the primary source. Only add explicit synonyms for terms that cross categories (e.g., "write" -> content skills + email skills). Keep the map small and intentional.
**Warning signs:** Newly added skills never appear in synonym-based searches.

### Pitfall 3: N+1 Reads When Computing Metadata
**What goes wrong:** Computing complexity/run time for each of 133 skills individually causes slow page loads.
**Why it happens:** `list_available_skills()` already reads every SKILL.md file. Adding full `parse_skill_md()` calls for each would double the I/O.
**How to avoid:** Compute `estimated_minutes` and `complexity` inside `list_available_skills()` using the data already being parsed (the function already reads frontmatter and input specs). Add step counting to the existing quick parse, don't call `parse_skill_md()` separately.
**Warning signs:** Dashboard load time exceeds 2 seconds; `/api/v2/skills` response time spikes.

### Pitfall 4: Role Not Set (New Users Who Skip Onboarding)
**What goes wrong:** Recommended skills section shows nothing or crashes because `pref.role` is null.
**Why it happens:** Users can skip onboarding or access the dashboard directly.
**How to avoid:** Fall back to showing "Popular Skills" (by execution count or a curated default list) when no role is set. Show a gentle prompt: "Set your role in Settings for personalized recommendations."
**Warning signs:** Blank "Recommended" section for any user.

### Pitfall 5: Search Dropdown Renders Unsanitized Content
**What goes wrong:** XSS vulnerability in search results.
**Why it happens:** Accidentally using innerHTML with unescaped skill names or descriptions.
**How to avoid:** Existing code in `dashboard_v2.html` already uses `escapeHtml()` for all rendered text. Maintain this pattern. Every string from the API that gets inserted into HTML MUST go through `escapeHtml()` or `escapeAttr()`.
**Warning signs:** Code review shows `innerHTML = '<div>' + s.name` without escaping.

### Pitfall 6: Debounce Timing Mismatch
**What goes wrong:** Search feels laggy (too much debounce) or hammers API (too little).
**Why it happens:** Different debounce values on different pages.
**How to avoid:** Project convention: 300ms for API-backed searches, 200ms for local DOM filtering. Dashboard search hits API -> 300ms. Catalog search filters DOM -> 200ms (or keep at 0ms since it's instant DOM filtering).
**Warning signs:** User types fast and sees no results for >500ms, or API gets hit on every keystroke.

## Code Examples

### Enhanced search_skills with synonyms
```python
# In skill_execution_service.py
# Source: Derived from existing search_skills() function

SYNONYM_MAP = {
    "email": ["cold-email", "email-sequence", "email-deliverability",
              "campaign-launcher", "follow-up", "ecommerce-email"],
    "blog": ["blog-post", "content", "newsletter", "press-release"],
    "research": ["company-research", "market-research", "niche-research",
                  "prospect-research", "competitor-monitor", "brand-monitor"],
    "video": ["vsl", "youtube", "reel", "thumbnail", "video-ad"],
    "social": ["linkedin", "twitter", "instagram", "carousel-post"],
    "funnel": ["vsl-funnel", "landing-page"],
    "outreach": ["cold-email", "cold-dm", "linkedin-lead"],
    "ads": ["ad-creative", "meta-ads", "google-ads", "static-ad", "fb-ad"],
    "lead": ["lead-list-builder", "scraping", "gmaps", "crunchbase",
             "linkedin-lead", "funding-tracker"],
    "seo": ["seo-audit", "blog-post"],
    "write": ["blog-post", "case-study", "press-release", "newsletter",
              "product-description", "cold-email-campaign"],
    "automate": ["automation-builder", "n8n", "webhook"],
    "image": ["ai-image-generator", "thumbnail", "static-ad"],
}


def search_skills(query: str) -> list:
    """Search skills with partial matching and synonym support."""
    if not query or not query.strip():
        return list_available_skills()

    tokens = query.lower().split()
    skills = list_available_skills()
    scored = []

    # Expand tokens with synonyms
    expanded_tokens = set(tokens)
    for token in tokens:
        if token in SYNONYM_MAP:
            expanded_tokens.update(SYNONYM_MAP[token])
        # Also check partial synonym keys (e.g., "auto" matches "automate")
        for syn_key, syn_values in SYNONYM_MAP.items():
            if syn_key.startswith(token) or token.startswith(syn_key):
                expanded_tokens.update(syn_values)

    for skill in skills:
        searchable = (
            f"{skill['name']} {skill['display_name']} "
            f"{skill['description']} {skill['category']}"
        ).lower()
        score = 0

        for token in expanded_tokens:
            if token in searchable:
                score += 1
                if token in skill["name"].lower():
                    score += 2  # Boost exact name match
                if token == skill["category"]:
                    score += 1  # Boost category match

        # Also check original tokens for partial name matching
        for token in tokens:
            # Partial match: "email" in "cold-email-campaign"
            if token in skill["name"].lower():
                score += 3  # Strong boost for direct partial name match

        if score > 0:
            skill_copy = dict(skill)
            skill_copy["relevance_score"] = score
            scored.append(skill_copy)

    scored.sort(key=lambda x: -x["relevance_score"])
    return scored
```

### Enriched skill listing with complexity and time
```python
# Enhancement to list_available_skills() in skill_execution_service.py
# Add these computed fields to each skill dict before returning:

# Inside the for loop in list_available_skills():
    # Parse process steps for estimation
    steps_match = re.search(
        r'## Process Steps\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL
    )
    step_count = 0
    if steps_match:
        step_count = len(re.findall(r'^\d+\.', steps_match.group(1), re.MULTILINE))

    # Compute complexity
    prereq_count = 0
    prereq_match = re.search(
        r'## Prerequisites\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL
    )
    if prereq_match:
        prereq_count = len([
            l for l in prereq_match.group(1).strip().split('\n')
            if l.strip().startswith('-')
        ])

    required_inputs = sum(1 for i in inputs if i.get("required"))
    complexity_score = step_count + prereq_count + required_inputs
    if complexity_score <= 5:
        complexity = "simple"
    elif complexity_score <= 10:
        complexity = "moderate"
    else:
        complexity = "advanced"

    estimated_minutes = max(step_count // 2, 1)

    skills.append({
        "name": entry.name,
        "display_name": name,
        "description": description,
        "category": category,
        "has_script": has_script,
        "script_path": script_path,
        "inputs": inputs,
        "estimated_minutes": estimated_minutes,
        "complexity": complexity,
        "step_count": step_count,
    })
```

### Dashboard recommended skills section (Jinja2 + JS)
```html
<!-- In dashboard_v2.html, after Quick Start section -->
<div id="recommended-section" style="display: none;">
    <div class="section-label">Recommended for You</div>
    <div class="quick-start-grid" id="recommended-grid"></div>
</div>

<script>
// In the IIFE, after loadSkills()
async function loadRecommended() {
    try {
        var prefs = await fetchAPI('/api/v2/settings/preferences');
        var role = (prefs.preferences || {})['pref.role'];
        if (!role) return; // No role set, skip

        var res = await fetch('/api/v2/skills/search?role=' + encodeURIComponent(role));
        if (!res.ok) return;
        var data = await res.json();
        var skills = (data.skills || []).slice(0, 8);
        if (skills.length === 0) return;

        var grid = document.getElementById('recommended-grid');
        grid.innerHTML = '';
        skills.forEach(function(s) {
            var card = document.createElement('a');
            card.className = 'quick-start-card';
            card.href = '/skills/' + encodeURIComponent(s.name) + '/run';
            card.innerHTML = '<div class="quick-start-icon" style="background: var(--accent);">'
                + '<svg viewBox="0 0 24 24" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
                + '</div>'
                + '<span class="qs-label">' + escapeHtml(formatSkillName(s.name)) + '</span>';
            grid.appendChild(card);
        });

        document.getElementById('recommended-section').style.display = 'block';
    } catch (e) {
        // Non-critical, silently fail
    }
}
</script>
```

### Skill card complexity + time indicator (CSS)
```css
/* Complexity badges */
.complexity-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.125rem 0.5rem;
    border-radius: 9999px;
    font-size: 0.6875rem;
    font-weight: 500;
}

.complexity-simple {
    background: var(--success-muted, #dcfce7);
    color: var(--success, #16a34a);
}

.complexity-moderate {
    background: var(--warning-muted, #fef3c7);
    color: var(--warning, #d97706);
}

.complexity-advanced {
    background: var(--error-muted, #fef2f2);
    color: var(--error, #dc2626);
}

.time-estimate {
    font-size: 0.75rem;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 0.25rem;
}
```

### Output preview for skill detail page
```python
# In parse_skill_md(), add extraction of Outputs section:
outputs_match = re.search(
    r'## Outputs?\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL
)
if outputs_match:
    output_lines = []
    for line in outputs_match.group(1).strip().split('\n'):
        line = line.strip().lstrip('- ')
        if line:
            output_lines.append(line)
    result["output_examples"] = output_lines
else:
    # Fallback: generate from goal/description
    result["output_examples"] = []
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Client-side `.includes()` | Keep client-side for instant feel, add API synonym search | This phase | Partial matches and synonyms work |
| No complexity indicator | Derived from SKILL.md metadata | This phase | Users can estimate effort before running |
| Hardcoded Quick Start | Role-based recommendations | This phase | Personalized dashboard experience |
| No output preview on detail page | Extracted from SKILL.md Outputs section | This phase | Users understand what they'll get |

**Nothing deprecated** -- this phase enhances existing patterns without replacing them.

## Key Data Points

### Existing Skill Metadata Available (from SKILL.md parsing)
- `name` (kebab-case identifier)
- `display_name` (from frontmatter)
- `description` (from frontmatter)
- `category` (derived from CATEGORY_KEYWORDS in service)
- `inputs` (parsed from Input Specifications table, includes required flag)
- `process_steps` (parsed from Process Steps section)
- `prerequisites` (parsed from Prerequisites section)
- `quality_checklist` (parsed from Quality Checklist section)
- `execution_command` (parsed from Execution Command section)
- `related_directives` and `related_skill_bibles`

### What's NOT in SKILL.md but needed
- `estimated_minutes` -> DERIVE from `len(process_steps)` (already done by `/estimate` endpoint)
- `complexity` -> DERIVE from steps + prereqs + required inputs count
- `output_examples` -> PARSE from `## Outputs` section (some skills have it, like vsl-funnel)
- `synonyms` -> BUILD as a static map in service module
- `popularity` -> QUERY from `skill_executions` table (COUNT by skill_name)

### User Role Data
- Stored: `pref.role` in `user_settings` table
- Values: `"marketing"`, `"sales"`, `"operations"`, `"executive"`
- Set during: Onboarding flow (`onboarding.js` -> `POST /api/v2/settings/preferences`)
- Read via: `GET /api/v2/settings/preferences` (returns all `pref.*` keys)
- Fallback when not set: Show popular skills by execution count

### Category Mapping (already exists)
11 categories defined in `CATEGORY_KEYWORDS`:
`content`, `email`, `research`, `social`, `video`, `ads`, `leads`, `sales`, `client`, `automation`, `deploy`, + `other` fallback

## Open Questions

1. **Output preview content for skills without ## Outputs section**
   - What we know: Only some SKILL.md files (like vsl-funnel) have an explicit `## Outputs` section
   - What's unclear: What to show for the ~100+ skills that lack this section
   - Recommendation: Fall back to the `description` field or `goal` field. Show "This skill generates..." + description text. Don't try to parse or guess output format.

2. **Popularity data for "Popular Skills" fallback**
   - What we know: `skill_executions` table tracks every run with `skill_name`
   - What's unclear: Whether there's enough execution history to derive meaningful popularity
   - Recommendation: Query `SELECT skill_name, COUNT(*) as runs FROM skill_executions GROUP BY skill_name ORDER BY runs DESC LIMIT 8`. If fewer than 3 results, fall back to a curated default list (blog-post, cold-email-campaign, company-research, market-research, vsl-funnel, lead-list-builder).

3. **Should the catalog page (workflow_catalog.html) also get skill discovery features?**
   - What we know: `workflow_catalog.html` shows deployed workflow cards (cron/webhook). The skill catalog is served at `/skills` but currently uses `skill_execute.html`. These are different things.
   - What's unclear: Whether DISC requirements apply to the workflow catalog or just the skills UI
   - Recommendation: Focus DISC requirements on dashboard (`/home`) and skill pages (`/skills`, `/skills/{name}/run`). The workflow catalog is for deployed automations, not skill discovery.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of all relevant files (listed below)
- Database schema from `migrations/001_initial.sql` and `migrations/002_skill_execution.sql`

### Files Analyzed
- `/railway_apps/aiaa_dashboard/templates/dashboard_v2.html` - Dashboard with search hero and quick start
- `/railway_apps/aiaa_dashboard/templates/workflow_catalog.html` - Workflow catalog with card grid
- `/railway_apps/aiaa_dashboard/templates/skill_execute.html` - Skill detail/execution page
- `/railway_apps/aiaa_dashboard/static/js/main.js` - Shared utilities (debounce, fetchAPI, escapeHtml, showToast)
- `/railway_apps/aiaa_dashboard/static/js/onboarding.js` - Role selection and preference saving
- `/railway_apps/aiaa_dashboard/routes/views.py` - All page routes
- `/railway_apps/aiaa_dashboard/routes/api_v2.py` - Skill API endpoints
- `/railway_apps/aiaa_dashboard/services/skill_execution_service.py` - Skill parsing, search, execution
- `/railway_apps/aiaa_dashboard/models.py` - DB operations
- `/railway_apps/aiaa_dashboard/database.py` - SQLite connection and migrations
- `/railway_apps/aiaa_dashboard/migrations/002_skill_execution.sql` - Schema for skill_executions, client_profiles, user_settings
- `/.claude/skills/cold-email-campaign/SKILL.md` - Sample skill metadata
- `/.claude/skills/blog-post/SKILL.md` - Sample skill metadata
- `/.claude/skills/vsl-funnel/SKILL.md` - Sample skill with Outputs section

### Tertiary (LOW confidence)
- None. All findings are based on direct codebase analysis.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Direct codebase analysis, no new libraries
- Architecture: HIGH - All patterns derived from existing code structure
- Pitfalls: HIGH - Identified from actual code review of search implementations
- Code examples: HIGH - Based on existing function signatures and patterns in the codebase

**Research date:** 2026-02-23
**Valid until:** Indefinite (brownfield enhancement of stable codebase)
