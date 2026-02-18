# AIAA Agentic OS — Agent Instructions

> **Version:** 5.0 | **Last Updated:** February 18, 2026
> Skills-first architecture. Each skill is self-contained with its own script.

---

## Quick Reference

| Resource | Count | Location |
|----------|-------|----------|
| **Native Skills** | 133 | `.claude/skills/` (each with SKILL.md + script) |
| Shared Utilities | 4 | `.claude/skills/_shared/` |
| Subagents | 5 | `.claude/agents/` |
| Rules | 9 | `.claude/rules/` |
| Active Hooks | 35 | `.claude/hooks/` |
| Directives (reference) | 150+ | `directives/*.md` |
| Skill Bibles | 286 | `skills/SKILL_BIBLE_*.md` |
| Agency Context | 4 files | `context/` |
| Client Profiles | per-client | `clients/{client_name}/` |
| Dashboard | Railway | `railway_apps/aiaa_dashboard/` (modular Flask)

---

## System Overview

This system uses **Skills-First DOE** architecture:
- **Skills** (`.claude/skills/`) — Self-contained packages: SKILL.md + Python script in one folder
- **You** (Claude agent) — Orchestrator that decides WHAT and WHEN
- **Directives** (`directives/`) — Reference SOPs for deeper context
- **Skill Bibles** (`skills/`) — Domain expertise on demand

LLMs are probabilistic. Skills bundle deterministic scripts with contextual intelligence. You focus on decisions.

See `.claude/rules/doe-architecture.md` and `AGENTS.md` for full details.

---

## Rules (`.claude/rules/`)

| Rule File | What It Covers |
|-----------|---------------|
| `doe-architecture.md` | DOE pattern, three layers, flow |
| `workflow-phases.md` | 8-phase execution flow (Parse→Plan→Skill→Capability→Context→Execute→Quality→Deliver) |
| `context-loading.md` | Agency context, client context, skill bibles, loading order |
| `delivery-pipeline.md` | Save locally → Google Docs → Slack notification |
| `quality-gates.md` | Content length minimums, output validation, research quality |
| `self-annealing.md` | Post-task improvement protocol |
| `error-handling.md` | API failures, missing inputs, partial failures |
| `railway-deployment.md` | Railway dashboard + Modal serverless deployment |
| `plan-mode.md` | Plan first, build second — for complex tasks |

---

## Critical Do's and Don'ts

### ALWAYS
- Check `.claude/skills/` for a matching skill FIRST
- Load `context/agency.md` before generating ANY content
- Load `clients/{name}/*.md` for client-specific work
- Follow the 8-phase execution flow
- Save to `.tmp/` before delivering to Google Docs
- Self-anneal after every task (fix, document, commit)
- Plan before building complex multi-step tasks

### NEVER
- Generate content without agency context loaded
- Skip quality gates
- Commit `.env`, `credentials.json`, or API keys
- Inline work that a script can do deterministically
- Ignore recurring errors
- Load 10+ context files at once (context pollution)

---

## Directory Structure

```
Agentic OS/
├── .env                    # API keys (NEVER commit)
├── .tmp/                   # Intermediate outputs (gitignored)
├── .claude/
│   ├── skills/            # 133 self-contained skills (SKILL.md + .py)
│   │   └── _shared/       # 4 shared utilities (error_reporter, api_health, resilience, skill_validator)
│   ├── rules/             # 9 agent rules
│   ├── hooks/             # 35 active hooks
│   ├── agents/            # 5 subagent definitions
│   └── settings.local.json
├── context/               # Agency context (who you are)
├── clients/               # Client profiles (who you serve)
├── directives/            # SOPs — reference material (150+ files)
├── execution/             # Utility scripts + originals (reference)
├── skills/                # Skill bibles — domain expertise (286 files)
├── railway_apps/          # Dashboard deployment
│   └── aiaa_dashboard/    # Modular Flask app (app.py, routes/, services/, models.py, database.py, templates/, static/)
├── CLAUDE.md              # THIS FILE
├── AGENTS.md              # Full agent reference + skill catalog
└── requirements.txt
```

---

## How Skills Work

Each skill is a self-contained folder in `.claude/skills/{name}/`:
```
.claude/skills/cold-email-campaign/
├── SKILL.md                  # Workflow definition, args, quality gates
└── write_cold_emails.py      # The execution script
```

Just ask for what you need. "Write cold emails for Acme Corp" → triggers the `cold-email-campaign` skill. The SKILL.md tells you the exact command, required inputs, and quality checklist.

Browse all skills: `ls .claude/skills/`

---

## Environment Variables

| Key | Purpose | Required |
|-----|---------|----------|
| `OPENROUTER_API_KEY` | LLM access (Claude/GPT via OpenRouter) | Yes |
| `PERPLEXITY_API_KEY` | Market research | Yes |
| `SLACK_WEBHOOK_URL` | Notifications | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Docs/Sheets | For delivery |
| `OPENAI_API_KEY` | OpenAI direct | Optional |
| `ANTHROPIC_API_KEY` | Direct Claude | Optional |
| `FAL_KEY` | Image generation | Optional |
| `APIFY_API_TOKEN` | Lead scraping | Optional |

---

## Quick Commands

```bash
# Run any skill's script directly
python3 .claude/skills/vsl-funnel/generate_complete_vsl_funnel.py --company "X" --website "Y" --offer "Z"
python3 .claude/skills/cold-email-campaign/write_cold_emails.py --sender "Name" --company "X" --offer "Y" --target "Z"
python3 .claude/skills/blog-post/generate_blog_post.py --topic "Topic" --length 1500
python3 .claude/skills/company-research/research_company_offer.py --company "X" --website "Y"

# Delivery
python3 .claude/skills/google-doc-delivery/create_google_doc.py --file ".tmp/output.md" --title "Title"
python3 .claude/skills/slack-notifier/send_slack_notification.py --message "Done" --channel "#general"

# Dashboard
cd railway_apps/aiaa_dashboard && railway up        # Deploy to Railway
python3 railway_apps/aiaa_dashboard/app.py          # Run locally

# Check any script's args
python3 .claude/skills/{skill-name}/{script}.py --help
```

---

## First-Time Setup

```bash
pip install -r requirements.txt     # Python deps
cp .env.example .env                # Configure API keys
# Place credentials.json in project root for Google Docs
npm install -g @railway/cli         # Railway CLI
railway login                       # Authenticate
```

---

## Key Skill Bibles

| Category | Key Files |
|----------|-----------|
| VSL/Funnels | `SKILL_BIBLE_vsl_writing_production.md`, `SKILL_BIBLE_funnel_copywriting_mastery.md` |
| Cold Email | `SKILL_BIBLE_cold_email_mastery.md`, `SKILL_BIBLE_email_deliverability.md` |
| Agency/Sales | `SKILL_BIBLE_agency_sales_system.md`, `SKILL_BIBLE_offer_positioning.md` |
| AI/Automation | `SKILL_BIBLE_ai_automation_agency.md`, `SKILL_BIBLE_monetizable_agentic_workflows.md` |

Find more: `ls skills/ | grep -i "<topic>"`

---

## Creating New Capabilities

When a capability doesn't exist:
1. Check: `ls .claude/skills/ | grep -i "<keyword>"`
2. Create skill folder: `.claude/skills/new-skill/SKILL.md` + `.py` script
3. Optionally create directive: `directives/new_workflow.md` (reference SOP)
4. Create skill bible if new domain: `skills/SKILL_BIBLE_<topic>.md`

---

## Hooks Reference

35 active hooks in `.claude/hooks/` enforce the DOE pattern, protect secrets, validate quality, and track metrics. 93 archived hooks available in `.claude/hooks/_archived/`. Full hook documentation is in `AGENTS.md`.

Key hooks: `secrets_guard.py` (blocks secret exposure), `doe_enforcer.py` (directive before script), `output_quality_gate.py` (validates outputs).

Debug: `python3 .claude/hooks/<hook>.py --status`
Reset: `rm -rf .tmp/hooks/*.json`

---

## Your Role

You are the **brain**. Parse intent → Check skills → Load context → Execute → Deliver → Self-anneal.

Skills are your primary tools. Directives and skill bibles are reference. Subagents are your team. Hooks are your safety net.
