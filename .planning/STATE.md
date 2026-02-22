# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-22)

**Core value:** Non-technical users can discover, configure, execute, and receive output from any of 133 AI skills through the web dashboard without ever touching a terminal, and when something goes wrong, they understand exactly what happened and how to fix it.
**Current focus:** Phases 2-9 (parallelizable after Phase 1 baseline verified)

## Current Position

Phase: 3 of 10 (Error Handling)
Plan: 3 of 3 in current phase
Status: Phase complete -- all 3 plans (03-01, 03-02, 03-03) done
Last activity: 2026-02-22 -- Completed 03-03-PLAN.md (error pages + settings deep-link + form preservation)

Progress: [███░░░░░░░] 33%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 2.4 min
- Total execution time: 0.28 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-regression-baseline | 1 | 3 min | 3 min |
| 02-input-validation | 3 | 9 min | 3 min |
| 03-error-handling | 3 | 6 min | 2 min |

**Recent Trend:**
- Last 5 plans: 3min, 4min, 2min, 2min, 2min
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

### Pending Todos

None.

### Blockers/Concerns

- API v1 protected endpoints return 401 for session-authenticated users due to session key mismatch (api.py checks `session['authenticated']`, login sets `session['logged_in']`). Should be addressed in a future hardening phase.

## Session Continuity

Last session: 2026-02-22T23:39:02Z
Stopped at: Completed 03-03-PLAN.md (error pages + settings deep-link + form preservation)
Resume file: None
