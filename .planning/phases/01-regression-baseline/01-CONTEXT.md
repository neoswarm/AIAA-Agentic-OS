# Phase 1: Regression Baseline - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Confirm all existing pages render and function correctly before any hardening begins. Run existing tests, audit every dashboard page for JS errors, and produce a baseline report documenting current state. No code changes in this phase — observation only.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
- Test scope: Run existing test suite (test_app.py), plus manual verification of all page routes returning 200
- Pass/fail criteria: Existing tests must pass as-is. Console JS errors are noted but don't block. Deprecation warnings documented but acceptable.
- Audit depth: Hit every route defined in views.py, verify HTTP status codes, check for obvious template rendering errors
- API endpoint verification: Hit all API v2 endpoints with basic GET requests, verify they return valid JSON
- Baseline report: Markdown document listing all routes, their status, any issues found, and test results
- Report location: `.planning/phases/01-regression-baseline/BASELINE-REPORT.md`

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants this done quickly so we can move to the hardening phases.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-regression-baseline*
*Context gathered: 2026-02-22*
