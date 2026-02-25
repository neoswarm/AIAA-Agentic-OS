# UX Idiot-Proof Plan: AIAA Agentic OS

> **Created:** February 18, 2026
> **Goal:** Make setup and deployment absolutely foolproof for non-tech users who are used to SaaS onboarding (click a button, enter email, done).

---

## Current State vs SaaS Expectations

**What a SaaS user expects:**
1. Go to a URL
2. Sign up with email/Google
3. See a dashboard immediately
4. Click buttons to configure things
5. Never touch a terminal
6. Never see code
7. Never debug anything

**What this system currently requires:**
1. Know what Claude Code is
2. Install Claude Code (terminal)
3. Open a terminal
4. Paste a giant 600-line prompt
5. Answer questions one by one
6. Get API keys from 6+ different services
7. Set up Google Cloud OAuth (25 steps)
8. Deploy to Railway (interactive CLI)
9. Log into a dashboard that shows nothing

The gap is enormous. This plan bridges it.

---

## Phase 1: Pre-Entry Fixes (5 files, ~30 min)

*User hasn't even started yet. These are "I can't find the front door" problems.*

| # | Problem | Fix | File(s) |
|---|---------|-----|---------|
| 1 | **No idea what Claude Code is or how to install it** | Add a "Step 0: Install Claude Code" section at the very top of QUICKSTART with: what it is (one sentence), install command, how to open Terminal on Mac (Cmd+Space, type "Terminal"), screenshot-quality text description | `QUICKSTART_PROMPT.md` |
| 2 | **Version numbers say 4.1, 3.0, and 5.0 across different files -- looks broken** | Normalize everything to `v5.0` in all 14 locations: QUICKSTART (5x), README (1x), app.py (2x), login.html (1x), views.py health endpoint (1x), CLAUDE.md (already correct), AGENTS.md (already correct) | 5 files |
| 3 | **Two different GitHub URLs** (`stopmoclay/` vs `lucassynnott/`) | Standardize to `lucassynnott/AIAA-Agentic-OS` everywhere | `QUICKSTART_PROMPT.md` |
| 4 | **`.env.example` exists but is stale** -- lists keys the QUICKSTART doesn't mention (Apollo, PandaDoc, GHL, Smartlead, Pinecone) and misses `OPENROUTER_API_KEY` which is the only required one | Rewrite `.env.example` to match the actual required/recommended/optional tiers from QUICKSTART | `.env.example` |

---

## Phase 2: QUICKSTART Rewrite (1 file, ~45 min)

*The core onboarding. Currently ~800 lines of nested prompts. Needs to become a SaaS-style guided flow.*

| # | Problem | Fix |
|---|---------|-----|
| 5 | **Wall of text before the prompt starts** -- 50 lines of "Prerequisites" before they even get to copy-paste | Collapse to 3 bullet points: (1) Install Claude Code, (2) Have a GitHub account, (3) Have a Railway account. Everything else is auto-detected. |
| 6 | **The prompt inside the prompt is 600+ lines** -- a non-tech user sees this in their clipboard and panics | Add a clear visual separator: "COPY EVERYTHING BELOW THIS LINE" with a row of equals signs. Add "STOP COPYING HERE" at the end. |
| 7 | **Google OAuth is step 3 of 7 and takes 25 sub-steps** -- this is where people quit | Move Google OAuth to the END (Step 7, fully optional). Reorder to: Install -> API Keys (just OpenRouter) -> Agency Profile -> Deploy Dashboard -> Test -> Show Skills -> OPTIONAL: Google Docs. The user gets a working system before hitting the hard part. |
| 8 | **6 API keys presented as a wall** -- only OpenRouter is required but it feels like all 6 are | Restructure into 3 tiers with clear labels: (a) REQUIRED (just OpenRouter -- 1 key, 5 min), (b) RECOMMENDED (Perplexity + Slack -- do these if you have 10 min), (c) SKIP FOR NOW (Anthropic, FAL, Apify -- add later from the dashboard). If user says "skip" to recommended, just move on. |
| 9 | **Interactive Railway prompts break the automated flow** | Add explicit callout boxes: "PAUSE -- YOU NEED TO DO SOMETHING. A browser window will open. Sign in and come back. Type 'done' when finished." Make these visually distinct from the automated parts. |
| 10 | **Password hash generation is shell-fragile** | Replace the heredoc approach with a simple `python3 -c "import hashlib; print(hashlib.sha256(input('Password: ').encode()).hexdigest())"` using `input()` to avoid shell escaping entirely. Or better: have Claude ask for the password in conversation and generate the hash in-context. |
| 11 | **"Publishing Workflows" section at the bottom is developer-facing** | Move to a separate `PUBLISHING.md` file or into AGENTS.md. A first-time user does not need deployment instructions during setup. |

---

## Phase 3: Dashboard UX Fixes (6 files, ~30 min)

*User just deployed. They log in and see... nothing.*

| # | Problem | Fix | File(s) |
|---|---------|-----|---------|
| 12 | **Empty dashboard after first deploy** -- 0 workflows, 0 executions, blank events table | Add a "Welcome" empty-state on the dashboard: "Your dashboard is live! Go to Claude Code and run a skill to see results here. Try: 'Write a cold email for TestCo targeting small businesses'" | `templates/dashboard.html` |
| 13 | **`error.html` template doesn't exist** -- 404 and 500 errors will crash the app | Create `templates/error.html` extending base.html with error code and message display | New file |
| 14 | **Login footer says "v3.0"** | Change to "v5.0" | `templates/login.html` |
| 15 | **Health endpoint returns "version": "3.0"** | Change to "5.0" | `routes/views.py` |
| 16 | **app.py header and startup banner say "v3.0"** | Change to "v5.0" | `app.py` |
| 17 | **No "what is this?" context on login page** -- user arrives at a URL with just a username/password box | Add a one-liner under the title: "Your AI agency command center. 133 skills at your fingertips." | `templates/login.html` |

---

## Phase 4: Safety Nets (3 files, ~20 min)

*Things that go wrong and the user has no way to recover.*

| # | Problem | Fix | File(s) |
|---|---------|-----|---------|
| 18 | **Locked out of dashboard, no recovery path** | Add a `/setup` route that activates when `DASHBOARD_PASSWORD_HASH` is empty -- shows a "Set your password" form. Document in troubleshooting: "To reset, run `railway variables set DASHBOARD_PASSWORD_HASH=` (blank) and visit /setup" | `routes/views.py`, `templates/` (new setup.html) |
| 19 | **No Windows support mentioned** | Add one line to QUICKSTART prerequisites: "Works on macOS and Linux. Windows users: install WSL first (link)" | `QUICKSTART_PROMPT.md` |
| 20 | **`workflow_catalog.html` references `total_workflows`, `categories`, `favorites`, `recent_workflows` but `views.py` doesn't pass all of them** | Audit the template variables vs what the route actually passes and fix the mismatches so the workflow page renders without Jinja errors | `routes/views.py` |

---

## Phase 5: README Alignment (1 file, ~15 min)

| # | Problem | Fix |
|---|---------|-----|
| 21 | **README duplicates the full 600-line prompt from QUICKSTART** -- confusing which to use, doubles maintenance surface | Replace the inline prompt in README with a 3-line quick start: "1. Install Claude Code, 2. Open terminal, 3. Paste the contents of QUICKSTART_PROMPT.md" and link to QUICKSTART. Keep the system overview, skill list, and dashboard docs. |
| 22 | **README says "v4.1" in the embedded prompt** | Remove the duplicate prompt (see #21) to eliminate the version mismatch entirely |

---

## Execution Order

### Wave 1: Trust + Unblocking (do first, ~30 min)

Prevents the "this looks broken" reaction.

- [ ] Items 1-4 (version + URL + .env fixes)
- [ ] Items 14-16 (dashboard version strings)
- [ ] Item 13 (error.html -- prevents crashes)

### Wave 2: Onboarding Quality (~45 min)

Makes the setup flow feel like a SaaS product.

- [ ] Items 5-11 (QUICKSTART rewrite/reorder)
- [ ] Item 12 (dashboard empty state)
- [ ] Item 17 (login context)

### Wave 3: Safety + Polish (~30 min)

Catches edge cases and prevents lock-outs.

- [ ] Items 18-20 (recovery, Windows, template audit)
- [ ] Items 21-22 (README cleanup)

---

## Total Estimate

~2.5 hours of implementation across ~15 files.

---

## Key Principle

Every decision a user has to make is a chance for them to quit. The goal is to reduce decisions to zero where possible, show progress constantly, and make the first "win" (a working dashboard with visible output) happen in under 10 minutes.
