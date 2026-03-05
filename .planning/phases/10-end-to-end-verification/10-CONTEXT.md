---
phase: 10-end-to-end-verification
created: 2026-02-23
source: discuss-phase (user chose "you decide everything")
---

# Phase 10: End-to-End Verification — Context

## Decisions

### Test Framework
- **pytest** for all tests — consistent with existing test_app.py
- Tests run against local Flask test client (no live server needed)
- No browser automation — test HTTP responses and JSON, not rendered UI

### API Validation Tests (TEST-02)
- Test all API v2 endpoints added during phases 2-9
- Validate structured error responses (field-level messages, correct HTTP status codes)
- Test both valid and invalid inputs per endpoint
- Key endpoints: /api/v2/skills/search, /api/v2/skills/execute, /api/v2/clients, /api/v2/preferences, /skills/recommended

### E2E Smoke Test (TEST-03)
- Single test function walking through: setup/login → configure API key → browse skills → execute skill → view output
- Uses Flask test client (app.test_client()) for HTTP-level testing
- Simulates user session with session cookies
- Tests the happy path — not every edge case

### Regression Strategy
- Run existing test_app.py tests alongside new tests
- All tests in same pytest session — any failure = phase fails
- No modifications to existing tests (they must pass as-is)

### Test File Location
- New tests in `railway_apps/aiaa_dashboard/test_hardening.py`
- Keeps new tests separate from existing test_app.py
- Both discovered by pytest automatically

### What "Passing" Means
- All pytest tests exit 0
- No skipped tests (every test must actually run)
- Coverage of all critical user workflows, not line-by-line coverage

## Deferred Ideas
None — this is the final phase.
