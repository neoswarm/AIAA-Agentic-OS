# Agentic OS Hardening for Non-Technical Users

## What This Is

A hardening, polish, and streamlining pass on the Agentic OS dashboard and skill execution system to make it bulletproof for non-technical users (marketers, agency owners, sales professionals) who have zero CLI knowledge, no terminal experience, and no coding background.

## Context

The Agentic OS is a production-grade AI agency operating system with 133 skills, a Flask dashboard (Railway-deployed), and a DOE (Directive-Orchestration-Execution) architecture. A major UX overhaul was just completed that added:

- New dashboard home with search, quick start cards, categories
- Skill execution forms auto-generated from SKILL.md metadata
- Execution progress page with live output streaming
- Output viewer with copy/download/delivery actions
- Settings page (API keys, preferences, profile)
- Client management with CRUD operations
- Onboarding wizard (4-step flow)
- Improved error pages with plain-English messages
- New navigation structure (Home, Run Skill, My Outputs, Clients, Settings, Help)
- 10 hook files rewritten with user-friendly error messages

## The Problem

The UX overhaul created the foundation, but it was built quickly by an agent team. It needs hardening:

1. **Input validation is minimal** — forms accept bad data, no client-side validation
2. **Error recovery is weak** — when things fail, users don't know what happened or how to fix it
3. **Help/tooltips are sparse** — new users don't understand what fields mean
4. **Loading states are basic** — no skeleton screens, no graceful degradation
5. **Edge cases aren't handled** — empty states, network errors, timeout scenarios
6. **Accessibility is poor** — no ARIA labels, keyboard nav incomplete
7. **Mobile experience is untested** — responsive CSS exists but may have gaps
8. **Workflow friction** — too many clicks for common tasks, unclear next steps
9. **API key setup is confusing** — users don't know where to get keys or why they need them
10. **Skill discovery is weak** — 133 skills but hard to find the right one

## Core Value

Non-technical users can discover, configure, execute, and receive output from any of 133 AI skills through the web dashboard without ever touching a terminal, and when something goes wrong, they understand exactly what happened and how to fix it.

## Target Users

- **Primary:** Marketing agency owners running campaigns for clients
- **Secondary:** Sales professionals who need content/research on demand
- **Tertiary:** Operations managers automating workflows

## Constraints

- Must preserve all existing functionality (133 skills, hooks, DOE architecture)
- Must stay within Flask + Jinja2 + vanilla JS + CSS stack (no React, no build tools)
- Must remain deployable to Railway with current Procfile/Gunicorn setup
- SQLite database (no Postgres migration)
- Must work in both dark and light themes
- Must keep all 35 hooks functional

## What Success Looks Like

A non-technical user can:
1. Complete onboarding and configure their first API key in under 3 minutes
2. Find and execute any skill in under 60 seconds
3. Understand and recover from any error without external help
4. Manage clients and run client-specific skills without confusion
5. Navigate the entire dashboard without encountering broken states or dead ends

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep vanilla JS (no framework) | Simplicity, no build step, fast deploys | Confirmed |
| SQLite (no migration) | Sufficient for single-user/small-team dashboard | Confirmed |
| Harden existing code, not rewrite | UX overhaul foundation is solid, needs polish not replacement | Confirmed |
| Focus on common paths first | 80/20 rule — make the top 10 workflows flawless | Confirmed |

## Requirements

### Validated

- ✓ Dashboard home with search and categories — existing
- ✓ Skill execution forms from SKILL.md — existing
- ✓ Execution progress with live output — existing
- ✓ Output viewer with actions — existing
- ✓ Settings page (API keys, preferences, profile) — existing
- ✓ Client management CRUD — existing
- ✓ Onboarding wizard — existing
- ✓ Improved error pages — existing
- ✓ New navigation structure — existing
- ✓ Hook messages in plain English — existing

### Active

- [ ] Input validation on all forms (client-side + server-side)
- [ ] Loading states and skeleton screens
- [ ] Empty states for all list views
- [ ] Error recovery with actionable guidance
- [ ] Tooltips and contextual help
- [ ] Keyboard accessibility (ARIA, focus management)
- [ ] Mobile responsiveness polish
- [ ] Workflow streamlining (reduce clicks)
- [ ] Skill search improvements (better fuzzy matching, suggestions)
- [ ] API key setup guidance (inline help, validation feedback)
- [ ] Toast notifications for all async operations
- [ ] Graceful degradation (offline, API down, missing keys)
- [ ] End-to-end testing of all user flows

### Out of Scope

- Framework migration (React, Vue, etc.) — too much complexity for current needs
- Database migration (Postgres) — SQLite sufficient
- Multi-user/auth system overhaul — current single-user login is fine
- New skill creation — existing 133 skills are sufficient
- CI/CD pipeline — manual Railway deploys work

---
*Last updated: 2026-02-22 after initialization*
