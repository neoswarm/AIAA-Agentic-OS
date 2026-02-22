# Requirements — Agentic OS Hardening

## v1 Requirements

### Input Validation (VAL)
- [ ] **VAL-01**: All skill execution form fields validate required inputs before submission with inline error messages
- [ ] **VAL-02**: Client form validates required fields (name) and formats (website URL) with real-time feedback
- [ ] **VAL-03**: Settings page validates API key format before save attempt (length, prefix patterns)
- [ ] **VAL-04**: Server-side validation on all API v2 endpoints returns structured error JSON with field-level messages
- [ ] **VAL-05**: Search inputs sanitize and debounce to prevent excessive API calls

### Error Handling (ERR)
- [ ] **ERR-01**: All API calls in JS have try/catch with user-friendly toast messages on failure
- [ ] **ERR-02**: Network timeout errors show "Check your connection" with retry button
- [ ] **ERR-03**: Skill execution failures display the error reason and suggest specific recovery steps
- [ ] **ERR-04**: Missing API key errors link directly to the Settings page with the relevant key highlighted
- [ ] **ERR-05**: 404 and 500 pages use error_v2.html with contextual recovery actions
- [ ] **ERR-06**: Form submission errors preserve user input (don't clear the form)

### Loading & Empty States (UX)
- [ ] **UX-01**: Skill catalog shows skeleton cards while loading
- [ ] **UX-02**: Execution history shows empty state with "Run your first skill" CTA when no history exists
- [ ] **UX-03**: Client list shows empty state with "Add your first client" CTA when no clients exist
- [ ] **UX-04**: All buttons show loading spinner during async operations and disable to prevent double-clicks
- [ ] **UX-05**: Dashboard recent activity shows "No activity yet" with helpful guidance when empty
- [ ] **UX-06**: Search results show "No skills match — try different keywords" when empty

### Help & Guidance (HELP)
- [ ] **HELP-01**: Each skill execution form field has a tooltip explaining what it does and example values
- [ ] **HELP-02**: Settings API key section has "What is this?" and "Where do I get this?" expandable help per key
- [ ] **HELP-03**: Onboarding wizard has progress indicator showing current step and total steps clearly
- [ ] **HELP-04**: Help page has searchable FAQ covering the top 10 user questions
- [ ] **HELP-05**: First-time dashboard visit shows welcome banner with quick orientation

### Accessibility (A11Y)
- [ ] **A11Y-01**: All interactive elements have proper ARIA labels and roles
- [ ] **A11Y-02**: Focus management works correctly through form flows and modals
- [ ] **A11Y-03**: Color contrast meets WCAG AA standard in both dark and light themes
- [ ] **A11Y-04**: All forms are keyboard-navigable (tab order, enter to submit, escape to cancel)

### Mobile Polish (MOB)
- [ ] **MOB-01**: Dashboard cards stack properly on mobile (single column below 768px)
- [ ] **MOB-02**: Sidebar collapses to hamburger menu on mobile
- [ ] **MOB-03**: Skill execution forms are fully usable on mobile (no horizontal scroll)
- [ ] **MOB-04**: Touch targets are minimum 44x44px for all buttons and links

### Workflow Streamlining (FLOW)
- [ ] **FLOW-01**: "Run Again" button on output page pre-fills the form with previous parameters
- [ ] **FLOW-02**: Favorite skills persist and appear on dashboard home for quick access
- [ ] **FLOW-03**: Skill categories on dashboard link directly to filtered catalog view
- [ ] **FLOW-04**: After onboarding completion, user lands on dashboard with first-run guidance
- [ ] **FLOW-05**: Client selector dropdown available on skill execution page for client-specific runs

### Skill Discovery (DISC)
- [ ] **DISC-01**: Search supports partial matches and common synonyms (e.g., "email" matches "cold-email-campaign")
- [ ] **DISC-02**: Each skill card shows estimated run time and complexity indicator
- [ ] **DISC-03**: Popular/recommended skills highlighted on dashboard based on user's role
- [ ] **DISC-04**: Skill detail page shows example output preview or description of what gets generated

### Testing & Stability (TEST)
- [ ] **TEST-01**: All existing tests continue to pass (regression)
- [ ] **TEST-02**: New API endpoints have basic validation tests
- [ ] **TEST-03**: End-to-end smoke test for: onboarding → API key → run skill → view output
- [ ] **TEST-04**: All pages render without JS errors in browser console

## v2 Requirements (Deferred)

- Batch skill execution (run multiple skills at once)
- Skill scheduling (run skills on a cron)
- Output sharing (public links to outputs)
- User analytics (usage stats, popular skills)
- Multi-language support
- Dark/light theme auto-detection from OS preference
- Keyboard shortcuts for power users

## Out of Scope

- React/Vue migration — vanilla JS stack is sufficient and simpler to maintain
- PostgreSQL migration — SQLite handles the load for single-user/small-team
- New skill creation — 133 skills cover the use cases
- CI/CD pipeline — manual Railway deploys are fine for now
- Multi-tenant auth — current single-user login is appropriate

## Traceability

| Requirement | Phase |
|-------------|-------|
| VAL-01..05 | TBD |
| ERR-01..06 | TBD |
| UX-01..06 | TBD |
| HELP-01..05 | TBD |
| A11Y-01..04 | TBD |
| MOB-01..04 | TBD |
| FLOW-01..05 | TBD |
| DISC-01..04 | TBD |
| TEST-01..04 | TBD |
