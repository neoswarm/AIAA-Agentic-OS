# AIAA Agentic OS

An AI-powered agency operating system that runs inside Claude Code. Just ask for what you need — from VSL funnels to cold emails to market research — and Claude finds the right skill from 133 available and handles everything. Includes a modular web dashboard with SQLite persistence, 35 automated enforcement hooks, and a skills-first DOE architecture.

**Version:** 5.0 | **133 Native Skills** | **35 Active Hooks** | **Last Updated:** February 18, 2026

---

## System Architecture (Skills-First DOE)

This system uses a **Skills-First Directive-Orchestration-Execution (DOE)** architecture. Skills are the primary entry point — each one is a self-contained folder with a workflow definition (`SKILL.md`) and a Python execution script bundled together.

```
                         USER REQUEST
                "Create a VSL funnel for Acme Corp"
                              |
                              v
              +-------------------------------+
              |  1. SKILLS (Primary)          |
              |  .claude/skills/ — 133 skills |
              |  Self-contained packages:     |
              |  SKILL.md + Python script     |
              |  Context loading, execution,  |
              |  and quality gates built in.  |
              +-------------------------------+
                              |
                     (no matching skill?)
                              |
                              v
              +-------------------------------+
              |  2. DIRECTIVES (Fallback)     |
              |  directives/*.md — 150+ SOPs  |
              |  Legacy reference material.   |
              |  Load directive, then run     |
              |  the matching script.         |
              +-------------------------------+
                              |
                              v
              +-------------------------------+
              |  3. SUBAGENTS (Delegation)    |
              |  .claude/agents/ — 5 agents   |
              |  Research, Review, QA,        |
              |  Content Writing, Deploy      |
              +-------------------------------+
                              |
                              v
              +-------------------------------+
              |  4. HOOKS (Guardrails)        |
              |  .claude/hooks/ — 35 active   |
              |  Safety, quality, deployment, |
              |  and analytics enforcement    |
              +-------------------------------+
                              |
                              v
                           OUTPUT
              Local files, Google Docs, Slack
```

**Why Skills-First:** LLMs are probabilistic (90% accuracy = 59% over 5 steps). Skills bundle deterministic Python scripts with contextual intelligence into self-contained packages. The orchestrator focuses on decisions. Hooks enforce the pattern automatically.

---

## Directory Structure

```
Agentic OS/
|
|-- .claude/                        # Claude Code configuration
|   |-- skills/                     # 133 native skills (PRIMARY)
|   |   |-- cold-email-campaign/    #   Each skill is a self-contained folder:
|   |   |   |-- SKILL.md            #     Workflow definition, args, quality gates
|   |   |   `-- write_cold_emails.py #    Execution script
|   |   |-- vsl-funnel/
|   |   |-- blog-post/
|   |   `-- ... (133 total)
|   |-- agents/                     # 5 subagent definitions
|   |   |-- research.md
|   |   |-- reviewer.md
|   |   |-- qa.md
|   |   |-- content-writer.md
|   |   `-- deployer.md
|   |-- rules/                      # 9 rule files (loaded at session start)
|   |-- hooks/                      # 35 active enforcement hooks
|   |   |-- _archived/              # 93 archived hooks (restorable)
|   |   `-- HOOK_MANIFEST.md        # Full hook documentation
|   `-- settings.local.json         # Hook registrations
|
|-- .env                            # API keys (never committed)
|-- .tmp/                           # Intermediate outputs (gitignored)
|-- credentials.json                # Google OAuth credentials
|-- token.pickle                    # Google OAuth token
|
|-- context/                        # AGENCY CONTEXT - Who you are
|   |-- agency.md                   # Agency info, services, positioning
|   |-- owner.md                    # Owner profile, background, expertise
|   |-- brand_voice.md              # Tone, style, communication preferences
|   `-- services.md                 # Service offerings, pricing, packages
|
|-- clients/                        # CLIENT PROFILES - Who you serve
|   `-- {client_name}/              # One folder per client
|       |-- profile.md              # Client info, business, goals
|       |-- rules.md                # Specific rules for this client
|       |-- preferences.md          # Style, tone, do's and don'ts
|       `-- history.md              # Past work, context, outcomes
|
|-- directives/                     # 150+ SOPs (REFERENCE material)
|   |-- vsl_funnel_orchestrator.md
|   `-- ...
|
|-- execution/                      # Utility scripts + originals (reference)
|   |-- deploy_to_railway.py
|   `-- ...
|
|-- skills/                         # 286 skill bibles (domain expertise)
|   |-- SKILL_BIBLE_*.md
|   `-- ...
|
|-- railway_apps/                   # Dashboard deployment
|   `-- aiaa_dashboard/             # Flask dashboard app
|       |-- app.py
|       |-- Procfile
|       `-- requirements.txt
|
|-- AGENTS.md                       # Full agent reference + skill catalog
|-- CLAUDE.md                       # System brain (slim version)
|-- QUICKSTART_PROMPT.md            # Setup prompt for new users
`-- requirements.txt                # Python dependencies
```

---

## Quick Start

1. **Install Claude Code** (if you don't have it):
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```
2. **Open your terminal** and type `claude` to launch Claude Code
3. **Copy the full contents of [`QUICKSTART_PROMPT.md`](QUICKSTART_PROMPT.md)** and paste it into Claude Code

Claude walks you through everything interactively: cloning the repo, configuring API keys, setting up your agency profile, deploying the dashboard to Railway, and testing the system. The only required API key is OpenRouter -- everything else is optional.

**Time to complete:** 15-30 minutes

---

## System Overview

| Resource | Count | Location |
|----------|-------|----------|
| **Native Skills** | 133 | `.claude/skills/` (each with SKILL.md + script) |
| **Shared Utilities** | 4 | `.claude/skills/_shared/` |
| Subagents | 5 | `.claude/agents/` |
| Rules | 9 | `.claude/rules/` |
| Active Hooks | 35 | `.claude/hooks/` |
| Archived Hooks | 93 | `.claude/hooks/_archived/` |
| Directives (reference) | 150+ | `directives/` |
| Skill Bibles | 286 | `skills/` |
| Agency Context | 4 files | `context/` |

---

## How Skills Work

Each skill is a self-contained folder in `.claude/skills/{name}/`:

```
.claude/skills/cold-email-campaign/
├── SKILL.md                  # Workflow definition, args, quality gates
└── write_cold_emails.py      # The execution script
```

Just ask for what you need. "Write cold emails for Acme Corp" → triggers the `cold-email-campaign` skill. The SKILL.md tells Claude the exact command, required inputs, and quality checklist. The Python script handles all deterministic work (API calls, data processing, formatting).

Browse all 133 skills: `ls .claude/skills/`

---

## What You Can Do

Once set up, just tell Claude what you need. It will find the right skill from 133 available and handle everything:

### Sales Copy
```
Create a complete VSL funnel for [COMPANY NAME]. Their website is [WEBSITE] and they sell [PRODUCT/SERVICE] to [TARGET AUDIENCE].
```
```
Write a cold email sequence for my [SERVICE] targeting [INDUSTRY]. I'm [YOUR NAME] from [YOUR COMPANY]. Focus on [PAIN POINT].
```
```
Write a long-form sales page for [PRODUCT]. Price point is [PRICE]. Target audience is [AUDIENCE]. Focus on [MAIN BENEFIT].
```

### Content Creation
```
Write a 1500-word blog post about [TOPIC] for [TARGET AUDIENCE]. Tone should be [PROFESSIONAL/CASUAL/etc].
```
```
Write a LinkedIn post about [TOPIC]. Style: [STORY/EDUCATIONAL/LISTICLE]. Make it engaging and end with a call to action.
```
```
Write a YouTube script about [TOPIC]. Target length: [X] minutes. Style: [EDUCATIONAL/TUTORIAL/STORY].
```

### Research
```
Research [COMPANY NAME]. Their website is [WEBSITE]. I need to understand their business model, target audience, competitors, and positioning.
```
```
Research the [INDUSTRY] market. I need to understand key players, trends, opportunities, and challenges.
```

### Ad Creatives
```
Generate a Meta ads campaign for [PRODUCT] targeting [AUDIENCE]. Generate images for the ads.
```

### Lead Generation
```
Find [BUSINESS TYPE] in [LOCATION]. I need their name, address, phone, website, and reviews.
```
```
Find [JOB TITLES] at companies in [INDUSTRY] located in [LOCATION].
```

### Landing Pages
```
Generate a landing page for [PRODUCT] targeting [AUDIENCE]. Style: [modern-gradient/neo-noir/editorial-luxury]. Deploy to Cloudflare.
```

### Client Work
```
Help me add a new client: [CLIENT NAME]. Their website is [WEBSITE]. They're in the [INDUSTRY] industry and sell [PRODUCTS/SERVICES] to [AUDIENCE].
```
```
Create a monthly report for [CLIENT NAME]. Key metrics: [LIST METRICS]. Highlights: [ACHIEVEMENTS].
```

---

## Execution Flow (8 Phases)

Every task follows the same 8-phase flow:

| Phase | What Happens |
|-------|-------------|
| 1. **Parse** | Extract intent from your request |
| 2. **Plan** | For complex tasks: plan first, build second |
| 3. **Skill Check** | Find matching skill from 133 in `.claude/skills/` |
| 4. **Capability Check** | Fallback: check directives + execution scripts |
| 5. **Context Load** | Load agency context, client profiles, skill bibles |
| 6. **Execute** | Run the skill's Python script |
| 7. **Quality** | Validate output against quality gates |
| 8. **Deliver** | Save locally → Google Docs → Slack notification |

---

## Subagents (5)

Specialized workers Claude can delegate to for focused tasks:

| Agent | Purpose |
|-------|---------|
| `research` | Market research, company analysis, competitive intelligence |
| `reviewer` | Fresh-eyes quality check on code and content |
| `qa` | Test generation and validation for execution scripts |
| `content-writer` | Marketing content following brand voice |
| `deployer` | Railway and Modal deployment operations |

---

## Claude Code Hooks (35 Active)

Hooks fire automatically on every tool call to enforce compliance, prevent mistakes, and track system health. Organized into 4 tiers:

| Tier | Name | Hooks | Purpose |
|------|------|-------|---------|
| 1 | **Safety Critical** | 15 | Hard blockers: secrets guard, PII detection, path traversal, command injection, file size limits, context budget |
| 2 | **Quality & Workflow** | 10 | Warnings: DOE enforcement, output quality, content length, brand voice, client context |
| 3 | **Deployment Safety** | 5 | Deploy guards: Railway pre-deploy checklist, Modal deploy safety, production warnings |
| 4 | **Analytics** | 5 | Silent tracking: API costs, session activity, workflow patterns, system health |

93 additional hooks are archived in `.claude/hooks/_archived/` and can be restored as needed. Full documentation in `.claude/hooks/HOOK_MANIFEST.md`.

### Hook Debugging

```bash
python3 .claude/hooks/<hook_name>.py --status   # Check status
python3 .claude/hooks/<hook_name>.py --reset     # Reset state
rm -rf .tmp/hooks/*.json                         # Reset ALL hook state
```

---

## AIAA Dashboard

**v5.0 Modular Architecture** — A production-grade Flask application with SQLite persistence, refactored from a 5,362-line monolith into clean, maintainable components.

### Architecture Highlights

**Modular Structure:**
- `app.py` — Flask entry point
- `routes/` — API endpoints (`api.py`) and UI views (`views.py`)
- `services/` — Business logic (deployment, Railway API, webhooks)
- `models.py` — Data models for events, executions, deployments, webhook logs
- `database.py` — SQLite persistence (replaces in-memory storage)
- `templates/` — Jinja2 templates with component architecture
- `static/` — Design system with dark/light theme

**SQLite Persistence:**
All data persists across restarts:
- Execution history with timeline view
- Deployment records with status tracking
- Webhook logs with retry attempts
- Event stream for real-time monitoring

### Key Features

- **133 Native Skills** — Full catalog with descriptions, args, and examples
- **One-Click Deploy** — Deploy any skill to Railway from the UI
- **Visual Cron Builder** — Interactive cron schedule editor
- **Webhook Management** — Register, test, retry, and monitor webhooks with full logs
- **API Authentication** — Secure API access with key-based auth
- **Execution Timeline** — Visual history with filtering and search
- **Dark/Light Theme** — Design system with localStorage persistence
- **Mobile Responsive** — Works on all devices
- **Password Protected** — SHA-256 hashed authentication

### Deploy to Railway

**Prerequisites:**
- Railway account (https://railway.app)
- Railway CLI: `npm install -g @railway/cli`

```bash
railway login
cd railway_apps/aiaa_dashboard
railway init       # Select "Empty Project"
railway up         # Deploy
railway domain     # Generate public URL
```

**Run Locally:**
```bash
cd railway_apps/aiaa_dashboard
python3 app.py     # Runs on http://localhost:5000
```

**Required Environment Variables (Dashboard Service):**

| Variable | Description |
|----------|-------------|
| `DASHBOARD_USERNAME` | Login username |
| `DASHBOARD_PASSWORD_HASH` | SHA-256 hash of your password |
| `FLASK_SECRET_KEY` | Random secret for sessions |
| `RAILWAY_API_TOKEN` | Railway API token (manages cron, shared variables) |

**Project-Wide Shared Variables (set once, all services inherit):**

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | All AI generation workflows |
| `PERPLEXITY_API_KEY` | Research workflows |
| `SLACK_WEBHOOK_URL` | Notifications |
| `ANTHROPIC_API_KEY` | Direct Claude access |
| `FAL_KEY` | Image generation |
| `APIFY_API_TOKEN` | Lead scraping |
| `CALENDLY_API_KEY` | Calendly integration |
| `INSTANTLY_API_KEY` | Email outreach |

**Generate password hash:**
```bash
python3 << 'PYHASH'
import hashlib
password = "YOUR_PASSWORD_HERE"
print(hashlib.sha256(password.encode()).hexdigest())
PYHASH
```

**Database Initialization:**
SQLite database is automatically created on first run at `railway_apps/aiaa_dashboard/aiaa.db`. No manual setup required.

---

## Context System

### Your Agency (`context/` folder)
- `agency.md` — Your agency name, positioning, mission
- `brand_voice.md` — Your tone and style guidelines
- `services.md` — What you offer
- `owner.md` — Owner profile and background

### Your Clients (`clients/{name}/` folders)
- `profile.md` — Client business info, goals, audience
- `rules.md` — Content rules and compliance requirements
- `preferences.md` — Their style preferences
- `history.md` — Past work and outcomes

Context is loaded automatically by Claude before generating any content. Hooks enforce that this loading happens.

---

## Required API Keys

| Key | What It's For | Get It At |
|-----|---------------|-----------|
| `OPENROUTER_API_KEY` | Powers all AI generation (required) | https://openrouter.ai/keys |
| `PERPLEXITY_API_KEY` | Deep research capabilities | https://perplexity.ai/settings/api |
| `FAL_KEY` | AI image generation | https://fal.ai/dashboard/keys |
| `SLACK_WEBHOOK_URL` | Notifications | https://api.slack.com/apps |
| `APIFY_API_TOKEN` | Lead scraping | https://console.apify.com |
| `ANTHROPIC_API_KEY` | Direct Claude access (optional) | https://console.anthropic.com |

---

## Content Standards

| Content Type | Target Length |
|--------------|---------------|
| VSL Script | 2,500–3,000 words (16–20 min video) |
| Sales Page | 1,500–3,000 words |
| Blog Post | 1,500–2,500 words |
| Email | 300–500 words each |

---

## License

Private repository — Client Ascension internal use.
