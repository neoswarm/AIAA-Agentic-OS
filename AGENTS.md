# AIAA Agentic OS — Complete Agent Reference

> **Version:** 5.0 | **Last Updated:** February 18, 2026
> Skills-first architecture. Plan before you build. Directives are reference, not starting points.

---

## Quick Reference

| Resource | Count | Location |
|----------|-------|----------|
| **Native Skills** | 133 | `.claude/skills/` |
| **Shared Utilities** | 4 | `.claude/skills/_shared/` |
| **Subagents** | 5 | `.claude/agents/` |
| **Rules** | 9 | `.claude/rules/` |
| **Active Hooks** | 35 | `.claude/hooks/` |
| Archived Hooks | 93 | `.claude/hooks/_archived/` |
| Directives (legacy SOPs) | 150+ | `directives/` |
| Execution Scripts | Bundled in skills | `.claude/skills/*/` (originals in `execution/`) |
| Skill Bibles | 286 | `skills/SKILL_BIBLE_*.md` |
| Agency Context | 4 files | `context/` |
| Client Profiles | per-client | `clients/{name}/` |
| Dashboard | Railway | `railway_apps/aiaa_dashboard/` (modular Flask)

---

## Architecture: Skills-First DOE

This system uses **Directive-Orchestration-Execution (DOE)** with a **skills-first** approach:

```
User Request
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  1. SKILLS (Primary)                                     │
│     .claude/skills/ — 133 native skills                  │
│     Self-contained workflows with context loading,       │
│     script execution, and quality gates built in.        │
│     → Use these FIRST for any supported workflow.        │
└─────────────────────────────────────────────────────────┘
    │ (no matching skill?)
    ▼
┌─────────────────────────────────────────────────────────┐
│  2. DIRECTIVES + SCRIPTS (Fallback)                      │
│     directives/*.md + execution/*.py                     │
│     Legacy SOPs still work. Load directive, then run     │
│     the matching script. 150+ workflows available.       │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  3. SUBAGENTS (Delegation)                               │
│     .claude/agents/ — 5 specialists                      │
│     Delegate research, review, QA, content, or deploy    │
│     to focused subagents with limited tool access.       │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  4. RULES + HOOKS (Guardrails)                           │
│     .claude/rules/ loaded at session start               │
│     .claude/hooks/ fire on every tool call               │
│     35 active hooks: safety, quality, deployment, metrics│
└─────────────────────────────────────────────────────────┘
```

**Key Principle:** LLMs are probabilistic. Skills package deterministic scripts with contextual intelligence. You (the orchestrator) decide WHAT to build. Skills and scripts handle HOW.

---

## Directory Structure

```
Agentic OS/
├── .claude/
│   ├── agents/            # 5 subagent definitions
│   ├── hooks/             # 35 active hooks
│   │   ├── _archived/     # 93 archived hooks (restorable)
│   │   └── HOOK_MANIFEST.md
│   ├── rules/             # 9 rule files (loaded at session start)
│   ├── skills/            # 133 native skills ← PRIMARY
│   │   └── _shared/       # 4 shared utilities (error_reporter, api_health, resilience, skill_validator)
│   └── settings.local.json
├── context/               # Agency context (4 files)
│   ├── agency.md          # Agency identity + positioning
│   ├── owner.md           # Owner profile + expertise
│   ├── brand_voice.md     # Tone, style, vocabulary
│   └── services.md        # Offerings, pricing, packages
├── clients/               # Client profiles (per-client folders)
│   └── {client_name}/     # profile.md, rules.md, preferences.md, history.md
├── directives/            # 150+ SOPs (REFERENCE material)
├── execution/             # Utility scripts + originals (reference)
├── skills/                # 286 skill bibles (REFERENCE material)
├── railway_apps/          # Dashboard + deployed services
│   └── aiaa_dashboard/    # Modular Flask application
│       ├── app.py         # Entry point
│       ├── config.py      # Configuration
│       ├── database.py    # SQLite connection
│       ├── models.py      # Data models
│       ├── routes/        # API and view routes
│       │   ├── api.py
│       │   └── views.py
│       ├── services/      # Business logic
│       │   ├── deployment_service.py
│       │   ├── railway_api.py
│       │   └── webhook_service.py
│       ├── templates/     # Jinja2 templates
│       └── static/        # CSS/JS/images
├── CLAUDE.md              # Slim system brain
└── AGENTS.md              # THIS FILE
```

---

## Execution Flow (8 Phases)

### Phase 1: Parse Input
Extract intent → map to skill or capability.

### Phase 2: Plan (for complex tasks)
Use plan mode (see `.claude/rules/plan-mode.md`):
- Multi-step tasks → plan first, build second
- Single-shot tasks (quick email, short post) → skip to Phase 3

### Phase 3: Skill Check
Does a native skill exist in `.claude/skills/`?

| Match | Action |
|-------|--------|
| Skill exists | Invoke the skill — it handles context, execution, and quality |
| No skill | Fall through to Phase 4 |

### Phase 4: Capability Check (Fallback)
Check legacy directives and scripts:
```bash
ls directives/ | grep -i "<keyword>"
ls execution/ | grep -i "<keyword>"
```
If nothing exists → create new directive + script.

### Phase 5: Load Context
Before execution, load in this order:
1. `context/agency.md` — always, for any content
2. `clients/{name}/*.md` — if client-specific work
3. Relevant skill bible from `skills/` — domain expertise
4. Directive (if using legacy path) — the SOP

**Never load 10+ context files at once** (context pollution).

### Phase 6: Execute
Run via skill, subagent, or direct script. Save outputs to `.tmp/`.

### Phase 7: Quality + Review
- Run quality gates (hooks handle this automatically)
- For important deliverables: delegate to `reviewer` subagent

### Phase 8: Deliver + Self-Anneal
1. Save locally → `.tmp/<project>/<filename>.md`
2. Create Google Doc → `.claude/skills/google-doc-delivery/create_google_doc.py`
3. Slack notification → `.claude/skills/slack-notifier/send_slack_notification.py`
4. Self-anneal: fix errors, update docs, commit improvements

---

## Native Skills (133)

Skills are the **primary** way to execute workflows. Each skill packages context loading, script execution, and quality validation into a single invocable unit.

### Content & Copy (18)
| Skill | What It Does |
|-------|-------------|
| `vsl-funnel` | Complete VSL funnel: research → script → sales page → emails |
| `vsl-script` | Standalone VSL script writing |
| `blog-post` | SEO-optimized blog posts with keyword targeting |
| `sales-page` | Long-form sales page copy |
| `funnel-copy` | Full funnel copy: sales page, emails, ads |
| `newsletter` | Email newsletters with curated content |
| `press-release` | Company press releases and announcements |
| `product-description` | E-commerce product descriptions |
| `youtube-script` | YouTube video scripts with hooks and structure |
| `youtube-script-workflow` | Multi-step YouTube script pipeline |
| `instagram-reel` | Instagram Reel scripts with hooks and CTAs |
| `twitter-thread` | Twitter/X threads optimized for virality |
| `carousel-post` | LinkedIn/Instagram carousel posts |
| `landing-page` | AI-generated landing page copy |
| `case-study` | Client case studies from results data |
| `podcast-repurposer` | Repurpose podcasts into multi-platform content |
| `rss-content` | Convert RSS feeds into social media content |
| `content-translator` | Translate content into multiple languages |

### Email & Outreach (14)
| Skill | What It Does |
|-------|-------------|
| `cold-email-campaign` | Personalized cold email sequences with A/B variants |
| `cold-email-personalizer` | AI-powered first-line personalization for cold emails |
| `cold-email-linkedin` | LinkedIn-personalized cold email campaigns |
| `cold-email-mass` | Mass cold email personalization at scale |
| `email-sequence` | Multi-email nurture sequences for funnels |
| `follow-up-sequence` | Automated follow-up email sequences |
| `ecommerce-email` | E-commerce email campaigns (welcome, abandon, win-back) |
| `ecom-email-calendar` | E-commerce email content calendar generation |
| `email-reply-classifier` | Classify email replies (interested, objection, unsubscribe) |
| `email-autoreply` | Automated email reply handling via Instantly |
| `email-validator` | Bulk email validation and deliverability checking |
| `email-deliverability` | Email deliverability reputation management |
| `linkedin-outreach` | LinkedIn DM outreach sequences |
| `linkedin-content` | LinkedIn posts and DMs with hooks and CTAs |

### Research & Analysis (12)
| Skill | What It Does |
|-------|-------------|
| `company-research` | Deep company/offer research using Perplexity AI |
| `prospect-research` | Comprehensive prospect dossiers for sales calls |
| `market-research` | Market/industry research using Perplexity Deep Research |
| `niche-research` | Deep niche research for market entry |
| `competitor-monitor` | Monitor competitor activity and changes |
| `landing-page-cro` | Analyze landing pages for CRO opportunities |
| `seo-audit` | SEO audits with actionable recommendations |
| `ab-test-analyzer` | Analyze A/B test results with statistical insights |
| `niche-outlier-finder` | Find cross-niche viral content outliers |
| `win-loss-analysis` | Analyze won/lost deals for patterns |
| `ai-news-digest` | Curated AI industry news digests |
| `youtube-knowledge-miner` | Mine YouTube videos for market intelligence |

### Advertising (7)
| Skill | What It Does |
|-------|-------------|
| `meta-ads-campaign` | Complete Meta/Facebook/Instagram ad campaigns |
| `google-ads-campaign` | Google Ads campaign creation and optimization |
| `ad-creative` | Ad creative briefs and copy for any platform |
| `reddit-ad-script` | Reddit-sourced pain points → ad scripts |
| `static-ad` | Static image ad copy and creative briefs |
| `video-ad-script` | Video ad scripts with hooks and CTAs |
| `fb-ad-library` | Facebook Ad Library competitive analysis |

### Lead Generation & Scraping (16)
| Skill | What It Does |
|-------|-------------|
| `lead-scraping` | Scrape B2B leads from Apify and Google Maps |
| `lead-scoring` | AI-powered lead scoring and prioritization |
| `lead-list-builder` | Fast multi-source lead pipeline building |
| `lead-deduplication` | Deduplicate lead lists by email/domain |
| `lead-notification` | Slack notifications for new leads |
| `lead-magnet-creator` | Create lead magnets with landing pages |
| `lead-magnet-delivery` | Automated lead magnet delivery workflows |
| `gmaps-leads` | Google Maps lead generation pipeline |
| `google-maps-scraper` | Scrape Google Maps business listings |
| `serp-scraper` | Scrape Google SERP for lead data |
| `crunchbase-leads` | Find leads from Crunchbase funding data |
| `linkedin-lead-scraper` | Scrape LinkedIn profiles via Apify |
| `linkedin-group-scraper` | Extract LinkedIn group member data |
| `job-board-leads` | Find companies hiring as lead signals |
| `yelp-scraper` | Scrape Yelp reviews and business data |
| `website-scraper` | Scrape website contact information |

### Sales & Client Management (16)
| Skill | What It Does |
|-------|-------------|
| `proposal-generator` | Client proposals with scope, pricing, timeline |
| `sales-call-summary` | Summarize sales calls with action items |
| `objection-handler` | Sales objection responses and rebuttals |
| `client-onboarding` | Client onboarding materials and profile setup |
| `stripe-onboarding` | Stripe-integrated client onboarding |
| `client-report` | Monthly/weekly client performance reports |
| `client-feedback` | Collect and analyze client feedback |
| `client-health` | Calculate client health scores |
| `qbr-generator` | Quarterly business review generation |
| `monthly-report` | Monthly performance reporting |
| `invoice-generator` | Professional invoices from project data |
| `pricing-strategy` | Pricing strategy and packaging optimization |
| `demo-scheduler` | Schedule and prep for sales demos |
| `meeting-prep` | Calendly meeting preparation briefs |
| `meeting-alert` | Booked meeting alerts with prospect research |
| `sales-dashboard` | Sales pipeline dashboard generation |

### Campaign & Funnel (7)
| Skill | What It Does |
|-------|-------------|
| `campaign-report` | Email campaign performance reports |
| `campaign-launcher` | Launch cold email campaigns via Instantly |
| `full-campaign` | End-to-end campaign pipeline orchestration |
| `funnel-strategy` | Funnel outline and strategy planning |
| `webinar-funnel` | Complete webinar funnel: registration → follow-up |
| `webinar-followup` | Webinar follow-up email sequences |
| `content-calendar` | Content calendars with topics and scheduling |

### Video & Media (9)
| Skill | What It Does |
|-------|-------------|
| `video-transcription` | Video/audio transcription and summarization |
| `video-editor` | Smart video editing with silence removal |
| `video-shorts` | Extract short clips from long-form video |
| `jump-cut-editor` | VAD-based jump cut editing for talking heads |
| `pan-3d-transition` | 3D pan transitions for video content |
| `thumbnail-generator` | YouTube thumbnail concept generation |
| `thumbnail-recreator` | Recreate thumbnails with face-swap AI |
| `ai-image-generator` | AI image prompt generation (DALL-E/Midjourney) |
| `product-photoshoot` | AI product photography generation |

### Automation & Ops (14)
| Skill | What It Does |
|-------|-------------|
| `faq-chatbot` | FAQ response generation for chatbots |
| `ticket-responder` | Auto-respond to support tickets |
| `ticket-triage` | Triage and categorize support tickets |
| `whatsapp-bot` | WhatsApp support bot responses |
| `social-scheduler` | Schedule social media posts across platforms |
| `crm-automator` | Automate CRM deal stage movements |
| `task-assignment` | Team task assignment and delegation |
| `milestone-tracker` | Track project milestones and deadlines |
| `n8n-converter` | Convert n8n workflows to directives |
| `utm-generator` | Generate UTM tracking parameters |
| `review-collector` | Collect reviews and testimonials |
| `testimonial-request` | Request testimonials from clients |
| `churn-alert` | Churn risk detection and alerts |
| `contract-renewal` | Contract renewal reminders and outreach |

### Deployment & Infrastructure (5)
| Skill | What It Does |
|-------|-------------|
| `google-doc-delivery` | Upload markdown to formatted Google Docs |
| `modal-deploy` | Deploy execution scripts to Modal cloud |
| `railway-deploy` | Deploy services to Railway |
| `dashboard-deploy` | Deploy the AIAA dashboard |
| `agency-dashboard` | Agency dashboard setup and management |

### Platform-Specific (9)
| Skill | What It Does |
|-------|-------------|
| `upwork-scraper` | Scrape and apply to Upwork jobs |
| `hubspot-enrichment` | Enrich HubSpot contacts with AI data |
| `ghl-prospecting` | GoHighLevel CRM prospecting automation |
| `dream100-instagram` | Dream 100 Instagram DM automation |
| `linkedin-profile-tracker` | Track LinkedIn profile changes |
| `x-youtube-content` | X/Twitter keyword → YouTube content pipeline |
| `youtube-channel-finder` | Find YouTube channels by niche |
| `youtube-to-campaign` | YouTube content → marketing campaign pipeline |
| `zoom-content-repurposer` | Repurpose Zoom calls into multi-format content |

### Strategy & Planning (6)
| Skill | What It Does |
|-------|-------------|
| `automation-builder` | Build and deploy automation workflows |
| `hiring-system` | Hiring workflow and team scaling |
| `payment-reminder` | Payment reminder escalation sequences |
| `funding-tracker` | Track company funding rounds for prospecting |
| `brand-monitor` | Monitor brand mentions across the web |
| `slack-notifier` | Send formatted Slack notifications |

**Usage:** Just ask for it. "Create a VSL funnel for Acme Corp" → triggers `vsl-funnel` skill. Run `ls .claude/skills/` to see all 133 available skills.

---

## Subagents (5)

Subagents are specialized workers you can delegate to. They have limited tool access and return results to you.

| Agent | Model | Purpose |
|-------|-------|---------|
| `research` | Sonnet 4.6 | Market research, company analysis, competitive intelligence. Uses web search. Returns condensed summaries with confidence levels. |
| `reviewer` | Sonnet 4.6 | Reviews code and content with zero prior context. Fresh-eyes quality check. Returns PASS / NEEDS_WORK / FAIL verdict. |
| `qa` | Sonnet 4.6 | Generates and runs tests for execution scripts. Validates outputs, checks edge cases, mocks API calls. |
| `content-writer` | Sonnet 4.6 | Generates marketing content following brand voice and client rules. Self-reviews against quality checklist. |
| `deployer` | Sonnet 4.6 | Handles Railway and Modal deployment. Verifies prerequisites, deploys, health-checks, and logs results. |

**When to use subagents:**
- **Research**: Any task requiring web search or multi-source intelligence gathering
- **Reviewer**: Before delivering important client work (second pair of eyes)
- **QA**: After creating or modifying execution scripts
- **Content Writer**: When generating substantial marketing copy
- **Deployer**: Any `railway up` or `modal deploy` operation

---

## Rules (9 files)

Rules in `.claude/rules/` are loaded at session start. They provide persistent guardrails.

| Rule | What It Enforces |
|------|-----------------|
| `doe-architecture.md` | Three-layer DOE pattern (Directive → Orchestration → Execution) |
| `workflow-phases.md` | 8-phase execution flow (Parse → Plan → Skill → Capability → Context → Execute → Quality → Deliver) |
| `context-loading.md` | Agency context first, client context second, skill bibles on demand |
| `delivery-pipeline.md` | Save locally → Google Docs → Slack notification pipeline |
| `quality-gates.md` | Content length minimums, output validation, research quality thresholds |
| `self-annealing.md` | Post-task improvement: fix errors, document learnings, commit |
| `error-handling.md` | API failures, missing inputs, partial failures, graceful degradation |
| `railway-deployment.md` | Railway dashboard + Modal serverless deployment rules |
| `plan-mode.md` | Plan first, build second for complex multi-step tasks |

---

## Active Hooks (35)

Hooks fire automatically on tool calls. 35 active hooks organized into 4 tiers. Full documentation in `.claude/hooks/HOOK_MANIFEST.md`.

### Tier 1: Safety Critical — Hard Blockers (15)

| Hook | Blocks | Purpose |
|------|--------|---------|
| `agent_limiter` | Yes | Max 5 parallel agents |
| `context_budget_guard` | Yes (85%) | Blocks at 85% context usage |
| `secrets_guard` | Yes | Blocks secret exposure in writes |
| `pii_detection_guard` | Yes | Blocks SSN/credit card patterns |
| `file_size_limit_guard` | Yes (500K) | Blocks oversized file writes |
| `large_file_read_blocker` | Yes | Blocks large reads when agents active |
| `context_pollution_preventer` | Yes (12+) | Blocks loading too many context files |
| `script_exists_guard` | Yes | Verifies script exists before running |
| `retry_loop_detector` | Yes (3x) | Blocks scripts failing 3+ times |
| `file_path_traversal_guard` | Yes | Blocks path traversal attacks |
| `command_injection_guard` | Yes | Blocks shell injection |
| `memory_usage_estimator` | Yes (2GB) | Blocks excessive memory usage |
| `backup_before_destructive` | Yes | Blocks rm/reset without backup |
| `json_output_validator` | Yes | Blocks invalid JSON writes |
| `modal_endpoint_limit_tracker` | Yes (8) | Blocks exceeding Modal endpoint limit |

### Tier 2: Quality & Workflow — Warnings (10)

| Hook | Purpose |
|------|---------|
| `doe_enforcer` | Directive before execution script |
| `output_quality_gate` | Word count, sections, keywords validation |
| `content_length_enforcer` | Min lengths by deliverable type |
| `execution_logger` | Logs all script runs |
| `error_pattern_detector` | Alerts on recurring failures |
| `self_anneal_reminder` | Reminds to self-anneal after errors |
| `skill_bible_reminder` | Suggests relevant skill bibles |
| `delivery_pipeline_validator` | Reminds about delivery steps |
| `client_work_context_gate` | Warns if client context not loaded |
| `brand_voice_compliance` | Checks content against brand voice |

### Tier 3: Deployment Safety (5)

| Hook | Purpose |
|------|---------|
| `railway_deploy_guard` | Pre-deploy checklist for Railway |
| `deployment_config_validator` | Checks Procfile, requirements.txt |
| `modal_deploy_guard` | Pre-deploy checklist for Modal |
| `modal_dotenv_crash_detector` | Detects crash-causing import pattern |
| `production_safety_guard` | Extra warnings for destructive commands |

### Tier 4: Analytics — Silent (5)

| Hook | Purpose |
|------|---------|
| `api_cost_estimator` | Estimates API costs per session |
| `session_activity_logger` | Logs all session activities |
| `workflow_pattern_tracker` | Tracks workflow usage/success rates |
| `hook_health_monitor` | Monitors all hooks' health |
| `system_health_reporter` | Aggregated system health report |

**Debugging hooks:**
```bash
python3 .claude/hooks/<hook_name>.py --status   # Check status
python3 .claude/hooks/<hook_name>.py --reset     # Reset state
rm -rf .tmp/hooks/*.json                         # Reset ALL hook state
```

**Restoring archived hooks:** See `HOOK_MANIFEST.md` for the full list and restore instructions.

---

## Common Workflows (Skill-Based)

### VSL Funnel
> "Create a VSL funnel for Acme Corp's B2B lead generation service"

Uses `vsl-funnel` skill → runs research → generates VSL script → sales page → email sequence.

```bash
python3 .claude/skills/vsl-funnel/generate_complete_vsl_funnel.py --company "Acme Corp" --website "https://acmecorp.com" --offer "B2B Lead Generation"
```

### Cold Email Campaign
> "Write cold emails for Acme Corp targeting marketing agencies"

Uses `cold-email-campaign` skill → loads client context → generates personalized sequences with A/B variants.

```bash
python3 .claude/skills/cold-email-campaign/write_cold_emails.py --sender "John Smith" --company "Acme Corp" --offer "Lead generation" --target "Marketing agencies"
```

### Market Research
> "Research the AI automation market for a new service offering"

Uses `market-research` skill → delegates to `research` subagent → returns market size, growth rate, key players, trends.

```bash
python3 .claude/skills/market-research/research_market_deep.py --topic "AI automation market" --depth deep
```

### Content Generation
> "Write a blog post about AI in marketing" / "Create a LinkedIn post about agency growth"

Uses `blog-post`, `linkedin-content`, `youtube-script`, or `newsletter` skill depending on content type.

```bash
python3 .claude/skills/blog-post/generate_blog_post.py --topic "AI in marketing" --length 1500
python3 .claude/skills/linkedin-content/generate_linkedin_post.py --topic "Agency growth tips"
```

### Client Delivery
> "Deliver the VSL script to Google Docs and notify on Slack"

Uses `google-doc-delivery` skill → formats markdown as native Google Docs → sends Slack notification.

```bash
python3 .claude/skills/google-doc-delivery/create_google_doc.py --file ".tmp/output.md" --title "VSL Script"
python3 .claude/skills/slack-notifier/send_slack_notification.py --message "Done" --channel "#general"
```

---

## Agency Context & Client Profiles

### Loading Order (ALWAYS follow this)

1. **Agency context** (`context/agency.md`, `context/brand_voice.md`) — load before generating ANY content
2. **Client context** (`clients/{name}/profile.md`, `rules.md`) — load for client-specific work
3. **Skill bible** (`skills/SKILL_BIBLE_*.md`) — load for domain expertise on demand

### Client Profile Structure
```
clients/{client_name}/
├── profile.md       # Business info, goals, audience, competitors
├── rules.md         # MUST-FOLLOW rules for this client
├── preferences.md   # Style, tone, formatting preferences
└── history.md       # Past work, outcomes, learnings
```

---

## Environment Setup

### Required API Keys

| Key | Purpose | Required |
|-----|---------|----------|
| `OPENROUTER_API_KEY` | LLM access (Claude/GPT) | Yes |
| `PERPLEXITY_API_KEY` | Market research | Yes |
| `SLACK_WEBHOOK_URL` | Notifications | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google Docs delivery | For delivery |
| `OPENAI_API_KEY` | OpenAI direct | Optional |
| `ANTHROPIC_API_KEY` | Direct Claude | Optional |
| `FAL_KEY` | Image generation | Optional |
| `APIFY_API_TOKEN` | Lead scraping | Optional |

### First-Time Setup
```bash
pip install -r requirements.txt
cp .env.example .env               # Configure API keys
# Place credentials.json in project root for Google Docs
npm install -g @railway/cli        # Railway CLI
railway login                      # Authenticate
```

---

## Railway Dashboard

**v5.0 Modular Architecture** — The dashboard has been refactored from a 5,362-line monolith into a clean, maintainable Flask application with SQLite persistence.

### Architecture

**Entry Point:**
- `app.py` — Flask app initialization, registers routes

**Data Layer:**
- `database.py` — SQLite connection and initialization
- `models.py` — Event, Execution, Deployment, and WebhookLog models
- SQLite replaces in-memory deque for persistent storage

**Business Logic:**
- `services/deployment_service.py` — One-click deploy from UI
- `services/railway_api.py` — Railway API integration
- `services/webhook_service.py` — Webhook management with retry logic

**Routes:**
- `routes/views.py` — Dashboard UI endpoints
- `routes/api.py` — RESTful API with authentication

**Frontend:**
- `templates/` — Jinja2 templates with component structure
- `static/` — Design system, dark/light theme, visual cron builder

### Key Features

- **SQLite Persistence** — Events, executions, deployments, webhook logs persist across restarts
- **One-Click Deploy** — Deploy any skill to Railway from the dashboard UI
- **Visual Cron Builder** — Build cron schedules with interactive UI
- **API Authentication** — API keys for programmatic access
- **Webhook Management** — Register, test, retry, and monitor webhooks
- **Execution Timeline** — Visual execution history with filtering
- **Dark/Light Theme** — Design system with theme toggle
- **Mobile Responsive** — Works on all devices

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/` | Dashboard home with skill catalog |
| `/workflows` | Active workflows (cron + webhook) |
| `/executions` | Execution history with timeline view |
| `/deployments` | Deployment history and one-click deploy wizard |
| `/webhooks` | Webhook management UI |
| `/env` | Environment variable management |
| `/api/skills` | API: List all skills |
| `/api/execute` | API: Execute a skill |
| `/webhook/<slug>` | Public webhook endpoints |
| `/health` | Health check (no auth) |

### Deployment

```bash
cd railway_apps/aiaa_dashboard
railway up  # Deploy to Railway
# OR
python3 app.py  # Run locally on port 5000
```

**Full Railway deployment rules** are in `.claude/rules/railway-deployment.md` and `directives/deploy_to_railway.md`.

---

## Shared Utilities (4)

All skills have access to 4 shared utilities in `.claude/skills/_shared/`:

### 1. Error Reporter (`error_reporter.py`)
**Purpose:** Centralized error reporting with Slack integration

**Features:**
- Captures full stack traces
- Sends formatted error notifications to Slack
- Includes context (skill name, args, timestamp)
- Graceful degradation if Slack webhook fails

**Usage:**
```python
from _shared.error_reporter import report_error

try:
    # Skill logic
    pass
except Exception as e:
    report_error(e, skill_name="cold-email-campaign", context={"company": "Acme"})
```

### 2. API Health Checker (`api_health.py`)
**Purpose:** Pre-flight validation of API keys and connectivity

**Features:**
- Tests API key validity before execution
- Verifies network connectivity
- Returns detailed health status
- Prevents wasted execution on bad credentials

**Usage:**
```python
from _shared.api_health import check_api_health

health = check_api_health("OPENROUTER_API_KEY")
if not health["healthy"]:
    print(f"API health check failed: {health['error']}")
    sys.exit(1)
```

### 3. Resilience Decorators (`resilience.py`)
**Purpose:** Automatic retry and fallback logic for API calls

**Features:**
- `@retry` — Automatic retry with exponential backoff
- `@timeout` — Enforce maximum execution time
- `@fallback` — Graceful degradation with fallback values
- Configurable retry attempts and delay

**Usage:**
```python
from _shared.resilience import retry, timeout

@retry(max_attempts=3, delay=2)
@timeout(seconds=30)
def call_api():
    # API call logic
    pass
```

### 4. Skill Validator (`skill_validator.py`)
**Purpose:** Validate skill structure and integrity

**Features:**
- Verifies SKILL.md exists and is valid
- Checks Python script exists and is executable
- Validates required arguments are documented
- Ensures quality gates are defined

**Usage:**
```python
from _shared.skill_validator import validate_skill

is_valid, errors = validate_skill("cold-email-campaign")
if not is_valid:
    print(f"Skill validation failed: {errors}")
```

**When to use shared utilities:**
- Error Reporter: In every skill's exception handler
- API Health: Before expensive API operations
- Resilience: Around all external API calls
- Skill Validator: When creating or modifying skills

---

## Modal Serverless Deployment

Deploy execution scripts as serverless webhooks on Modal.

**Deploy:** `modal deploy .claude/skills/<skill-name>/<script>.py`

**Critical rule:** Separate `requests` and `dotenv` imports (Modal has no `python-dotenv`):
```python
try:
    import requests
except ImportError:
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Not needed on Modal
```

**Free tier limits:** 8 web endpoints max, 30 compute hours/month.

Use the `modal-deploy` skill or `deployer` subagent for deployment operations.

---

## Quality Rules

| Deliverable | Min Words | Notes |
|-------------|-----------|-------|
| VSL Scripts | 3000 | Full persuasion script |
| Sales Pages | 2000 | Long-form copy |
| Case Studies | 1500 | Detailed success story |
| Blog Posts | 1200 | SEO long-form |
| YouTube Scripts | 1500 | Full video script |
| Newsletters | 800 | Digest format |
| Email Sequences | 300/email | Per email |
| LinkedIn Posts | 150-3000 chars | Platform limits |

---

## Creating New Capabilities

When no skill, directive, or script exists:

1. **Check existing:** `ls .claude/skills/ | grep -i "<keyword>"`
2. **Create skill** (preferred): New folder `.claude/skills/<name>/` with `SKILL.md` + `.py` script
3. **Create directive** (optional reference): `directives/<name>.md` with inputs, steps, quality gates
4. **Create skill bible** (if new domain): `skills/SKILL_BIBLE_<topic>.md`

---

## Your Role

You are the **orchestrator**. Parse intent → Plan (if complex) → Find the right skill → Load context → Execute → Review → Deliver → Self-anneal.

Skills are your primary tools. Directives and skill bibles are reference. Subagents are your team. Hooks are your safety net. The bottleneck isn't capability — it's deciding what to build next.
