---
phase: 06-workflow-streamlining
plan: 01
subsystem: skill-execution-workflow
tags: [run-again, pre-fill, client-selector, query-params, ux]
dependencies:
  requires:
    - 01-regression-baseline (stable API and template foundation)
    - 02-input-validation (field validation for pre-filled forms)
    - 03-error-handling (fetchAPI wrapper, error panels)
  provides:
    - Run Again pre-fill from execution output to skill form via URL query params
    - Client selector dropdown on skill execution page
    - Execution output API returns params and skill_name
  affects:
    - 06-02 (remaining workflow streamlining features)
tech-stack:
  added: []
  patterns:
    - URL query params for cross-page form pre-fill
    - Graceful degradation for optional client selector
key-files:
  created: []
  modified:
    - railway_apps/aiaa_dashboard/routes/api_v2.py
    - railway_apps/aiaa_dashboard/templates/skill_output.html
    - railway_apps/aiaa_dashboard/templates/skill_execute.html
decisions:
  - Use getQueryParams() from main.js for URL parsing (no hand-rolled alternative)
  - Client selector degrades silently (hidden when no clients, console.warn on API failure)
  - Re-run URL uses /skills/{name}/run route (not the broken /execute route)
  - params returned as-is from SQLite (JSON string parsed on frontend)
  - loadClientSelector() runs in parallel with loadSkill() for faster page load
metrics:
  duration: 2min
  completed: 2026-02-23
---

# Phase 6 Plan 1: Run Again Pre-fill and Client Selector Summary

**One-liner:** Run Again button pre-fills skill form via URL query params from execution output; client selector dropdown fetches from /api/v2/clients with graceful degradation.

## What Was Done

### Task 1: Run Again pre-fill (API + output page + execution page)
Three coordinated changes to enable "Run Again" with pre-filled parameters:

1. **api_v2.py**: Added `skill_name` and `params` fields to the `/api/v2/executions/<id>/output` JSON response. The execution dict from `get_execution_status()` already contains these from the `skill_executions` table.

2. **skill_output.html**: Replaced the broken Re-run link (which pointed to `/skills/{name}/execute`) with a new URL builder that uses the correct `/skills/{name}/run` route and appends query params parsed from `data.params`.

3. **skill_execute.html**: Added `prefillFromQueryParams()` function that reads URL query params via `getQueryParams()` (from main.js) and sets matching form field values. Called immediately after `buildForm()` completes so fields exist in the DOM.

### Task 2: Client selector dropdown on skill execution page
Four additions to enable client-specific skill runs:

1. **HTML**: Added a client selector `<div>` with `<select>` between the skill header and mode tabs. Uses existing `.field-group`, `.field-label`, `.field-select` CSS classes.

2. **JavaScript**: Added `loadClientSelector()` async function that fetches from `/api/v2/clients` using `fetchAPI()` wrapper, populates the dropdown, and shows the selector group. Pre-fills from query params if `?client=slug` is present.

3. **Form submission**: Modified `collectFormData()` to include the selected client value in the execution POST body as `data.client`.

4. **Initialization**: `loadClientSelector()` called alongside `loadSkill()` at page init for parallel loading.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Use getQueryParams() from main.js | Already exported to window, handles edge cases, avoids hand-rolling |
| Client selector hides when no clients | Graceful degradation -- form works normally without it |
| Run parallel loadSkill() + loadClientSelector() | Both are independent API calls, faster page load |
| Re-run URL includes all params (including defaults) | User can edit pre-filled values; better to show previous values than empty form |
| params returned as raw JSON string from API | Frontend parses with JSON.parse; avoids double-encoding issues |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

1. API endpoint returns `skill_name` and `params` fields in execution output response
2. Re-run button href builds `/run` URL with query params (no `/execute` references remain)
3. `prefillFromQueryParams()` function exists and is called after `buildForm()`
4. Client selector HTML, JS, and form integration all present and using fetchAPI
5. No references to `/skills/{name}/execute` remain in skill_output.html

## Next Phase Readiness

**Blockers:** None
**Concerns:** None
**Ready for:** 06-02 (favorites, category links, onboarding redirect)
