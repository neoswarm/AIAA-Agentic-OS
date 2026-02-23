# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-22)

**Core value:** Non-technical users can discover, configure, execute, and receive output from any of 133 AI skills through the web dashboard without ever touching a terminal, and when something goes wrong, they understand exactly what happened and how to fix it.
**Current focus:** Phases 2-9 (parallelizable after Phase 1 baseline verified)

## Current Position

Phase: 5 of 10 (Help & Guidance)
Plan: 1 of 2 in current phase
Status: In progress
Last activity: 2026-02-23 -- Completed 05-01-PLAN.md

Progress: [████████░░] 83%

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: 2.3 min
- Total execution time: 0.38 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-regression-baseline | 1 | 3 min | 3 min |
| 02-input-validation | 3 | 9 min | 3 min |
| 03-error-handling | 3 | 6 min | 2 min |
| 04-loading-empty-states | 3 | 6 min | 2 min |
| 05-help-guidance | 1 | 1 min | 1 min |

**Recent Trend:**
- Last 5 plans: 2min, 2min, 2min, 3min, 1min
- Trend: consistent fast execution

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Brownfield hardening (not rewrite) -- existing UX overhaul is the foundation
- Vanilla JS stack (no React/Vue migration)
- SQLite (no Postgres migration)
- Phases 2-9 are parallelizable after Phase 1 baseline
- API v1 session key mismatch (authenticated vs logged_in) documented as pre-existing issue, not fixed in baseline phase
- /setup redirect when password configured is expected behavior, not a bug
- validation_error() helper centralizes structured error format for all API v2 endpoints
- Collect all field errors before returning (user sees all problems at once)
- Skill execute validates required params from parsed SKILL.md metadata dynamically
- Layered inline validation on top of browser-native checkValidity (not replacing it)
- Error messages derived from field labels dynamically for skill form
- Client-side KEY_PREFIXES mirrors server-side _KEY_PREFIXES for consistent validation
- 300ms debounce for API-backed searches, 200ms for local DOM filtering
- IIFE debounce pattern for pages without main.js loaded
- All search output rendering uses escapeHtml() -- no raw innerHTML with user input
- main.js loaded globally via base.html script tag (single toast source of truth)
- fetchAPI showError defaults to true -- all callers auto-toast on failure
- 15s default timeout via AbortController in fetchAPI
- Retry button uses callback pattern for network/timeout errors
- Error panel below form (not modal) so users see input and error together
- API key provider detection via keyword matching in error messages
- classifyError() pattern for structured error display with recovery guidance
- error_v2.html used for all 404/500 handlers (app-level and blueprint-level)
- 500 handler shows error detail only in debug mode (str(e) if app.debug)
- Deep-link highlight animation auto-removes after 4 seconds
- All catch blocks use showToast guard (typeof check) for safe invocation
- Skeleton uses CSS custom properties for automatic light/dark theme compatibility
- Skeletons hidden in catch block too to prevent eternal loading state
- Catalog skeleton uses DOMContentLoaded since content is server-rendered via Jinja2
- SVG spinner uses stroke-dasharray for proper rotating arc (not clock icon)
- Spinner keyframes injected globally from main.js (not duplicated per template)
- setButtonLoading stores/restores innerHTML to preserve button icons
- withButtonLoading() wraps async ops with auto-restore in finally block
- Empty states include actionable CTAs guiding users to next logical step
- Verified clients.html already satisfies UX-03 (no changes needed)
- Dashboard activity empty state uses inline styles matching existing empty-hint pattern
- Search empty state includes 'browse all skills' link to /workflows for discoverability
- Tooltip text assembled from description + example/placeholder with pre-line whitespace
- Placeholders under 60 chars used as example fallback when no explicit example exists
- Progress text placed below dots (not inside onboarding-card) for visual hierarchy

### Pending Todos

None.

### Blockers/Concerns

- API v1 protected endpoints return 401 for session-authenticated users due to session key mismatch (api.py checks `session['authenticated']`, login sets `session['logged_in']`). Should be addressed in a future hardening phase.

## Session Continuity

Last session: 2026-02-23T00:29:51Z
Stopped at: Completed 05-01-PLAN.md (tooltips + onboarding progress)
Resume file: None
