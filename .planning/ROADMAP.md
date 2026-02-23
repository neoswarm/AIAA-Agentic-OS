# Roadmap: Agentic OS Hardening

## Overview

This roadmap hardens the existing Agentic OS dashboard for non-technical users. All pages and core functionality already exist -- this is a polish, validation, and stability pass across 43 requirements in 10 phases. The first phase establishes a regression baseline, phases 2-9 harden specific dimensions (many parallelizable), and phase 10 verifies everything works end-to-end.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Regression Baseline** - Verify all existing functionality works before making changes ✓
- [x] **Phase 2: Input Validation** - All forms validate input with clear inline feedback ✓
- [x] **Phase 3: Error Handling** - Every failure shows a user-friendly message with recovery actions ✓
- [x] **Phase 4: Loading & Empty States** - Visual feedback for all async operations and empty data views ✓
- [x] **Phase 5: Help & Guidance** - Contextual help, tooltips, and onboarding improvements ✓
- [x] **Phase 6: Workflow Streamlining** - Reduce clicks and friction in common user paths ✓
- [x] **Phase 7: Skill Discovery** - Better search, browsing, and skill metadata for 133 skills ✓
- [x] **Phase 8: Accessibility** - ARIA labels, keyboard navigation, focus management, color contrast ✓
- [x] **Phase 9: Mobile Polish** - Responsive layout fixes, touch targets, mobile-specific UX ✓
- [ ] **Phase 10: End-to-End Verification** - Integration tests confirming the hardened system works as a whole

## Phase Details

### Phase 1: Regression Baseline
**Goal**: Confirm all existing pages render and function correctly before any hardening begins
**Depends on**: Nothing (first phase)
**Requirements**: TEST-01, TEST-04
**Success Criteria** (what must be TRUE):
  1. All existing test suites pass without modification
  2. Every dashboard page loads without JavaScript console errors
  3. A baseline test report exists documenting current state
**Plans**: 1 plan

Plans:
- [ ] 01-01-PLAN.md -- Run existing test suite, audit all routes and API endpoints, compile baseline report

### Phase 2: Input Validation
**Goal**: Users receive immediate, clear feedback when they enter invalid data in any form
**Depends on**: Phase 1
**Requirements**: VAL-01, VAL-02, VAL-03, VAL-04, VAL-05
**Success Criteria** (what must be TRUE):
  1. User sees inline error messages on skill execution forms when required fields are empty or invalid
  2. User sees real-time validation feedback on client forms (name required, URL format)
  3. User sees format validation on API key fields before save is attempted
  4. API endpoints return structured JSON errors with field-level messages on bad input
  5. Search input is debounced and sanitized (no excessive API calls on rapid typing)
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md -- Client-side inline validation for skill execution, client, and settings forms (VAL-01, VAL-02, VAL-03)
- [ ] 02-02-PLAN.md -- Server-side API validation with structured field-level error responses (VAL-04)
- [ ] 02-03-PLAN.md -- Search debounce standardization and XSS sanitization (VAL-05)

### Phase 3: Error Handling
**Goal**: When something fails, users understand what happened and know exactly how to fix it
**Depends on**: Phase 1
**Requirements**: ERR-01, ERR-02, ERR-03, ERR-04, ERR-05, ERR-06
**Success Criteria** (what must be TRUE):
  1. Every failed API call in the dashboard shows a user-friendly toast notification (not a silent failure)
  2. Network timeouts display a "Check your connection" message with a retry button
  3. Skill execution failures show the specific error reason and suggested recovery steps
  4. Missing API key errors link directly to Settings with the relevant key section highlighted
  5. 404 and 500 pages use the v2 error template with contextual recovery actions
  6. Failed form submissions preserve all user input (form is never cleared on error)
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md -- Consolidate toast system, enhance fetchAPI with timeout/retry and auto-toast on failure (ERR-01, ERR-02)
- [ ] 03-02-PLAN.md -- Skill execution error display with classified errors, recovery steps, and missing key detection (ERR-03, ERR-04)
- [ ] 03-03-PLAN.md -- Error pages using v2 template, Settings API key deep-linking, form preservation audit (ERR-05, ERR-06)

### Phase 4: Loading & Empty States
**Goal**: Users always see visual feedback during loading and helpful guidance when views have no data
**Depends on**: Phase 1
**Requirements**: UX-01, UX-02, UX-03, UX-04, UX-05, UX-06
**Success Criteria** (what must be TRUE):
  1. Skill catalog shows animated skeleton cards while data loads
  2. Execution history page shows "Run your first skill" CTA when empty
  3. Client list page shows "Add your first client" CTA when empty
  4. All buttons show a loading spinner and disable during async operations (no double-clicks)
  5. Dashboard recent activity shows "No activity yet" guidance when empty
  6. Search results display "No skills match -- try different keywords" when empty
**Plans**: 3 plans

Plans:
- [ ] 04-01-PLAN.md -- Skeleton loading states with CSS pulse animation for dashboard and catalog views (UX-01)
- [ ] 04-02-PLAN.md -- Empty states with CTAs for execution history, dashboard activity, and search results (UX-02, UX-03, UX-05, UX-06)
- [ ] 04-03-PLAN.md -- Button loading spinners with double-click prevention across all async operations (UX-04)

### Phase 5: Help & Guidance
**Goal**: New users can understand every field, feature, and workflow without external help
**Depends on**: Phase 1
**Requirements**: HELP-01, HELP-02, HELP-03, HELP-04, HELP-05
**Success Criteria** (what must be TRUE):
  1. Every skill execution form field has a tooltip with description and example values
  2. Settings API key section has expandable "What is this?" and "Where do I get this?" help per key
  3. Onboarding wizard clearly shows progress (current step X of Y)
  4. Help page has a searchable FAQ covering the top 10 user questions
  5. First-time dashboard visit shows a welcome banner with quick orientation
**Plans**: 2 plans

Plans:
- [ ] 05-01-PLAN.md -- Enhance skill form tooltips with example values, add Step X of Y to onboarding (HELP-01, HELP-03)
- [ ] 05-02-PLAN.md -- Searchable FAQ with 10 questions, first-time dashboard welcome banner (HELP-04, HELP-05)

Note: HELP-02 (API key expandable help) is already satisfied by existing settings.html implementation.

### Phase 6: Workflow Streamlining
**Goal**: Common user paths require fewer clicks and less guesswork
**Depends on**: Phase 1
**Requirements**: FLOW-01, FLOW-02, FLOW-03, FLOW-04, FLOW-05
**Success Criteria** (what must be TRUE):
  1. Output page has a "Run Again" button that pre-fills the form with previous parameters
  2. Users can favorite skills and see them on the dashboard home for quick access
  3. Dashboard category links go directly to a filtered catalog view
  4. After onboarding, user lands on the dashboard with first-run guidance
  5. Skill execution page has a client selector dropdown for client-specific runs
**Plans**: 2 plans

Plans:
- [ ] 06-01-PLAN.md -- Run Again pre-fill via query params and client selector dropdown on execution page (FLOW-01, FLOW-05)
- [ ] 06-02-PLAN.md -- Favorite skill toggling on dashboard, category link fix to /skills, post-onboarding redirect (FLOW-02, FLOW-03, FLOW-04)

### Phase 7: Skill Discovery
**Goal**: Users can quickly find the right skill among 133 options through better search and browsing
**Depends on**: Phase 1
**Requirements**: DISC-01, DISC-02, DISC-03, DISC-04
**Success Criteria** (what must be TRUE):
  1. Search supports partial matches and common synonyms (e.g., "email" finds "cold-email-campaign")
  2. Skill cards display estimated run time and complexity indicator
  3. Dashboard highlights popular/recommended skills based on user role
  4. Skill detail page shows example output preview or description of generated output
**Plans**: 2 plans

Plans:
- [ ] 07-01-PLAN.md -- Backend: synonym search, metadata enrichment (time/complexity), output example parsing, role-based recommendations endpoint (DISC-01, DISC-02, DISC-03, DISC-04 backend)
- [ ] 07-02-PLAN.md -- Frontend: API-backed search with synonyms, time/complexity badges, recommended section, output preview on detail page (DISC-01, DISC-02, DISC-03, DISC-04 frontend)

### Phase 8: Accessibility
**Goal**: The dashboard is fully usable via keyboard and meets WCAG AA contrast standards
**Depends on**: Phase 1
**Requirements**: A11Y-01, A11Y-02, A11Y-03, A11Y-04
**Success Criteria** (what must be TRUE):
  1. All interactive elements (buttons, links, inputs, modals) have proper ARIA labels and roles
  2. Focus moves correctly through form flows and modals (no focus traps, logical tab order)
  3. Color contrast meets WCAG AA in both dark and light themes
  4. All forms are fully keyboard-navigable (tab order, enter to submit, escape to cancel)
**Plans**: 2 plans

Plans:
- [ ] 08-01-PLAN.md -- ARIA labels, roles, live regions, and focus management across all templates and main.js (A11Y-01, A11Y-02)
- [ ] 08-02-PLAN.md -- WCAG AA color contrast fixes and full keyboard navigation implementation (A11Y-03, A11Y-04)

### Phase 9: Mobile Polish
**Goal**: The dashboard is fully usable on mobile devices without layout issues or unusable touch targets
**Depends on**: Phase 1
**Requirements**: MOB-01, MOB-02, MOB-03, MOB-04
**Success Criteria** (what must be TRUE):
  1. Dashboard cards stack in a single column below 768px
  2. Sidebar collapses to a hamburger menu on mobile
  3. Skill execution forms are fully usable on mobile (no horizontal scrolling)
  4. All buttons and links have minimum 44x44px touch targets
**Plans**: 2 plans

Plans:
- [ ] 09-01-PLAN.md -- Hamburger menu, sidebar overlay, card stacking, form adaptation, mobile layout (MOB-01, MOB-02, MOB-03)
- [ ] 09-02-PLAN.md -- Touch target enforcement (44px minimum) and iOS zoom prevention (MOB-04)

### Phase 10: End-to-End Verification
**Goal**: The fully hardened dashboard passes integration tests covering all critical user workflows
**Depends on**: Phases 2-9
**Requirements**: TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. New API endpoints have validation tests that pass
  2. End-to-end smoke test passes: onboarding -> API key setup -> run skill -> view output
  3. All regression tests from Phase 1 still pass after all hardening changes
**Plans**: 1 plan

Plans:
- [ ] 10-01-PLAN.md -- API v2 validation tests for all endpoints + E2E smoke test covering full user journey (TEST-02, TEST-03)

## Parallelization Notes

Phases 2-9 all depend only on Phase 1 (regression baseline), not on each other. This means they can be worked in parallel or any order after Phase 1 completes. Suggested parallel groupings:

- **Group A (Form Hardening)**: Phase 2 (Validation) + Phase 3 (Error Handling) -- related but independent layers
- **Group B (Visual Polish)**: Phase 4 (Loading/Empty) + Phase 5 (Help/Guidance) -- both add visual elements
- **Group C (Feature Enhancement)**: Phase 6 (Workflow) + Phase 7 (Discovery) -- both add capabilities
- **Group D (Device/Access)**: Phase 8 (Accessibility) + Phase 9 (Mobile) -- both about device/access compatibility

Phase 10 must come last as it verifies everything together.

## Progress

**Execution Order:**
Phase 1 first, then Phases 2-9 in any order (parallelizable), then Phase 10 last.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Regression Baseline | 1/1 | Complete ✓ | 2026-02-22 |
| 2. Input Validation | 3/3 | Complete ✓ | 2026-02-22 |
| 3. Error Handling | 3/3 | Complete ✓ | 2026-02-22 |
| 4. Loading & Empty States | 3/3 | Complete ✓ | 2026-02-23 |
| 5. Help & Guidance | 2/2 | Complete ✓ | 2026-02-23 |
| 6. Workflow Streamlining | 2/2 | Complete ✓ | 2026-02-23 |
| 7. Skill Discovery | 2/2 | Complete ✓ | 2026-02-23 |
| 8. Accessibility | 2/2 | Complete ✓ | 2026-02-23 |
| 9. Mobile Polish | 2/2 | Complete ✓ | 2026-02-23 |
| 10. End-to-End Verification | 0/1 | Not started | - |
