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

**Prerequisites:** You just need TWO accounts — Claude will auto-install all tools!
- **GitHub account** — Sign up at https://github.com
- **Railway account** — Sign up at https://railway.app

Claude will automatically install: Homebrew, Python, Git, Node.js, Railway CLI, and the Railway skill.

**Open Claude Code and paste this entire prompt to get started:**

```
I want to set up AIAA Agentic OS v4.1. Please help me through the entire process interactively, asking me ONE question at a time and waiting for my response before moving on.

## Prerequisites Check (Do This FIRST)

Before we begin Step 1, say:

"Before we get started, let me check if you have the required tools installed. I'll automatically install anything that's missing - you don't need to do anything!"

### Step 0a: Check for Homebrew (macOS only)

First, RUN this command to check the operating system:

uname -s

If macOS (Darwin), check if Homebrew is installed by RUNNING:

which brew

If Homebrew is NOT installed (command not found), say "I need to install Homebrew first - this is a package manager that makes installing other tools easy..." and RUN:

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

After Homebrew installs, RUN these commands to add it to the PATH:

echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

### Step 0b: Check and Auto-Install Required Tools

Now check each required tool and AUTOMATICALLY install any that are missing:

**Check Python:**
RUN: python3 --version

If Python is NOT installed, say "Installing Python..." and RUN:
- On macOS: brew install python3
- On Linux: sudo apt-get install -y python3 python3-pip

**Check Git:**
RUN: git --version

If Git is NOT installed, say "Installing Git..." and RUN:
- On macOS: brew install git
- On Linux: sudo apt-get install -y git

**Check npm/Node.js:**
RUN: npm --version

If npm is NOT installed, say "Installing Node.js (includes npm)..." and RUN:
- On macOS: brew install node
- On Linux: curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install -y nodejs

### Step 0c: Install Railway CLI and Railway Skill

After all tools are installed, say "Now I'll install the Railway CLI and Railway skill for easier deployments..."

RUN these commands:

npm install -g @railway/cli
npx add-skill mshumer/claude-skill-railway

### Step 0d: Verify Everything is Ready

RUN these commands to confirm everything is installed:

python3 --version
git --version
npm --version
railway --version

If all 4 commands succeed, say: "All required tools are installed and ready!"

Then ask: "Do you have a Railway account? If not, please:
1. Go to https://railway.app
2. Click 'Sign Up'
3. Connect with GitHub (recommended) or use email
4. Verify your email

Reply 'yes' when you have a Railway account and we'll proceed to Step 1!"

Wait for my response before continuing.

## Step 1: Clone & Install

Say: "Great! Let me download and install AIAA Agentic OS for you..."

Then RUN these commands automatically:

git clone https://github.com/lucassynnott/AIAA-Agentic-OS/
cd AIAA-Agentic-OS
pip install -r requirements.txt

After running them, tell me if they completed successfully or if there were any errors.

## Step 2: Configure API Keys (.env file)

Create my .env file with API keys. Ask me for each one individually, and walk me through getting each key with detailed instructions:

---

### OPENROUTER_API_KEY (REQUIRED - Powers all AI features)

**What it does:** Routes requests to Claude, GPT-4, and other AI models. This is the only required key.

**How to get it:**
1. Go to https://openrouter.ai
2. Click "Sign Up" (top right) - use Google or email
3. Once logged in, click your profile icon > "Keys"
4. Click "Create Key"
5. Name it "AIAA" and click "Create"
6. Copy the key (starts with `sk-or-`)

**Cost:** Pay-as-you-go. Most workflows cost $0.01-0.10. Add $5-10 credits to start.

---

### PERPLEXITY_API_KEY (Recommended - Deep research & prospect intel)

**What it does:** Powers all research workflows - company research, market analysis, prospect intelligence, competitor monitoring.

**How to get it:**
1. Go to https://perplexity.ai
2. Sign up or log in
3. Click your profile icon (bottom left) > "Settings"
4. Click "API" in the left sidebar
5. Click "Generate" to create a new API key
6. Copy the key (starts with `pplx-`)

**Cost:** $5/month for 1000 requests, or pay-as-you-go at ~$0.005 per request.

---

### SLACK_WEBHOOK_URL (Recommended - Notifications & alerts)

**What it does:** Sends notifications when workflows complete, meetings are booked, leads are found, etc.

**How to get it:**
1. Go to https://api.slack.com/apps
2. Click "Create New App" > "From scratch"
3. Name it "AIAA Notifications" and select your workspace
4. Click "Create App"
5. In the left sidebar, click "Incoming Webhooks"
6. Toggle "Activate Incoming Webhooks" to ON
7. Click "Add New Webhook to Workspace"
8. Select the channel for notifications (e.g., #aiaa-alerts)
9. Click "Allow"
10. Copy the Webhook URL (starts with `https://hooks.slack.com/services/`)

**Cost:** Free

---

### ANTHROPIC_API_KEY (Optional - Direct Claude access, faster)

**How to get it:**
1. Go to https://console.anthropic.com
2. Sign up with email
3. Click "Get API Keys" > "Create Key"
4. Copy the key (starts with `sk-ant-`)

---

### FAL_KEY (Optional - AI image generation)

**How to get it:**
1. Go to https://fal.ai
2. Sign up > click your profile > "Dashboard" > "Keys"
3. Click "Create Key" and copy it

---

### APIFY_API_TOKEN (Optional - Lead scraping)

**How to get it:**
1. Go to https://console.apify.com
2. Sign up > click "Settings" > "Integrations"
3. Copy your API token

---

For each key, ask me: "Do you have [KEY_NAME]? If yes, paste it. If no, I'll help you get it."

## Step 3: Google Drive, Docs & Sheets Setup (Recommended)

This enables automatic document creation, lead exports to Sheets, and file management.

### Step 3a: Create Google Cloud Project
1. Go to https://console.cloud.google.com
2. Click the project dropdown > "NEW PROJECT"
3. Name it "AIAA Agentic OS" > Click "CREATE"

### Step 3b: Enable Required APIs
1. Go to "APIs & Services" > "Library"
2. Search and ENABLE each: **Google Docs API**, **Google Sheets API**, **Google Drive API**

### Step 3c: Create OAuth 2.0 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "+ CREATE CREDENTIALS" > "OAuth client ID"
3. If prompted, configure consent screen (External, add your email as test user)
4. Application type: "Desktop app" > Name: "AIAA Desktop Client" > CREATE

### Step 3d: Download Credentials
1. Click "DOWNLOAD JSON" on the popup
2. Rename to `credentials.json`
3. Move to project root folder

### Step 3e: Test Integration

Say: "Now let me test the Google integration..."

Then RUN this command:

python3 .claude/skills/google-doc-delivery/create_google_doc.py --test

Tell me: "A browser window should open asking you to sign in to Google. Please:
1. Select your Google account
2. If you see 'Google hasn't verified this app' - click 'Continue' (it's your own app)
3. Grant permissions for Docs, Sheets, and Drive
4. You'll see 'The authentication flow has completed'

Let me know when you've completed the authentication, or if you see any errors!"

Wait for my response. If successful, confirm the test document was created.

## Step 4: Agency Profile Setup

Ask me questions one at a time to create my agency profile:
1. Agency name?
2. Website URL?
3. Services offered?
4. Target audience?
5. What makes you different?
6. Brand voice?

Save to: context/agency.md, context/brand_voice.md, context/services.md

## Step 5: Deploy AIAA Dashboard to Railway (AUTOMATE THIS)

Deploy my monitoring dashboard. Handle as much as possible automatically:

### 5a: Check Prerequisites

Say: "Let me check if Railway CLI is installed..."

Then RUN this command:

railway --version

If not installed, say "I need to install Railway CLI for you..." and RUN:

npm install -g @railway/cli

Then RUN this command to check if you're logged in:

railway whoami

If not logged in, tell me: "Please run 'railway login' in your terminal and complete the browser authentication, then let me know when done!"

Wait for my response before continuing.

### 5b: Get My Credentials
Ask me TWO questions (one at a time):
1. "What username do you want for your dashboard? (default: admin)"
2. "What password do you want for your dashboard?"

After I provide the password, say "Let me generate the secure password hash..."

Then RUN this command to generate the hash:

python3 << 'PYHASH'
import hashlib
password = "THE_PASSWORD_I_GAVE_YOU"
print(hashlib.sha256(password.encode()).hexdigest())
PYHASH

Save the username and hash - you'll need them for environment variables.

### 5c: Deploy

Say: "Now let me deploy your dashboard to Railway..."

Then RUN these commands:

cd railway_apps/aiaa_dashboard
railway init

Tell me: "When prompted, please select 'Empty Project' and give it a name like 'aiaa-dashboard'. Let me know when that's done!"

Wait for my response.

Then say "Deploying the dashboard code to Railway..." and RUN:

railway up

Tell me when the deployment completes.

### 5d: Set Environment Variables

Say: "Now I'll configure the environment variables..."

First, generate the FLASK_SECRET_KEY by RUNNING:

python3 -c "import secrets; print(secrets.token_hex(32))"

Then RUN these commands with the username and hash you saved earlier:

railway variables set DASHBOARD_USERNAME="[USERNAME_I_CHOSE]"
railway variables set DASHBOARD_PASSWORD_HASH="[THE_HASH_YOU_GENERATED]"
railway variables set FLASK_SECRET_KEY="[THE_SECRET_KEY_YOU_JUST_GENERATED]"

If I provided API keys in Step 2, also RUN:

railway variables set OPENROUTER_API_KEY="[MY_KEY_FROM_STEP_2]"
railway variables set PERPLEXITY_API_KEY="[MY_KEY_FROM_STEP_2]"
railway variables set SLACK_WEBHOOK_URL="[MY_WEBHOOK_FROM_STEP_2]"

Tell me when all variables are set.

### 5e: Generate Domain & Verify

Say: "Let me generate a public URL for your dashboard..."

Then RUN:

railway domain

Save the generated URL (it will look like: https://aiaa-dashboard-production.up.railway.app)

Then say: "Testing that your dashboard is live..."

RUN (using the domain from above):

curl -s "https://[THE_GENERATED_DOMAIN]/health"

Check if it returns: {"status": "ok", "version": "4.1", "skills": 133}

If successful, tell me "Dashboard is live!" If it fails, wait 30 seconds and try again (deployment may still be starting).

### 5f: Provide Login Details
Once everything is deployed, give me:
- Dashboard URL
- Username
- Password (the one I chose)
- Remind me to bookmark it!

Tell me: "Your AIAA Dashboard is now live! You can monitor all 133 skills, manage environment variables, and track webhook events."

## Step 6: Test the System

Say: "Let's test the system with a quick workflow!"

Ask me: "What type of agency/business are you? (marketing/content/design/other)"

Based on my answer, RUN one of these test commands:
- If marketing: `python3 .claude/skills/cold-email-campaign/write_cold_emails.py --sender "Test" --company "TestCo" --offer "Marketing services" --target "Small businesses"`
- If content: `python3 .claude/skills/blog-post/generate_blog_post.py --topic "Getting started with AI" --length 500`
- If design: Ask for a sample project to research
- If other: `python3 .claude/skills/company-research/research_company_offer.py --company "Apple" --website "https://apple.com"`

Show me the output file location and tell me if it was successful.

## Step 7: Show What's Available

Give me a quick tour of the 133 native skills organized by category:

**Content & Copy (18 skills):**
VSL funnels, sales pages, blog posts, YouTube scripts, Instagram Reels, LinkedIn posts, Twitter threads, carousel posts, landing pages, case studies, newsletters, press releases, and more.

**Email & Outreach (14 skills):**
Cold email campaigns, AI personalization, LinkedIn-personalized emails, mass cold emails, email sequences, follow-up automation, e-commerce emails, email validation, and deliverability management.

**Research & Analysis (12 skills):**
Company research, prospect research, market research, niche research, competitor monitoring, CRO analysis, SEO audits, A/B test analysis, and YouTube knowledge mining.

**Advertising (7 skills):**
Meta ads campaigns, Google Ads, ad creative generation, Reddit ad scripts, static ads, video ad scripts, and FB Ad Library analysis.

**Lead Generation (16 skills):**
Google Maps scraping, LinkedIn scraping, lead scoring, lead list building, deduplication, lead magnets, SERP scraping, Crunchbase leads, Yelp scraping, and more.

**Sales & Client Management (16 skills):**
Proposals, sales call summaries, objection handling, client onboarding, client reports, QBR generation, invoicing, pricing strategy, meeting prep, and sales dashboards.

**Campaign & Funnel (7 skills):**
Campaign reports, campaign launching, end-to-end campaigns, funnel strategy, webinar funnels, content calendars, and more.

**Video & Media (9 skills):**
Video transcription, smart editing, shorts extraction, jump cuts, 3D pan transitions, thumbnail generation, AI image generation, and product photography.

**Automation & Ops (14 skills):**
FAQ chatbots, ticket triage, WhatsApp bots, social scheduling, CRM automation, task assignment, milestone tracking, n8n conversion, UTM generation, and churn alerts.

**Deployment & Infrastructure (5 skills):**
Google Doc delivery, Modal deploy, Railway deploy, dashboard deploy, and agency dashboard management.

**Platform-Specific (9 skills):**
Upwork scraping, HubSpot enrichment, GoHighLevel prospecting, Dream100 Instagram, LinkedIn profile tracking, YouTube channel finding, and more.

**Strategy & Planning (6 skills):**
Automation building, hiring systems, payment reminders, funding tracking, brand monitoring, and Slack notifications.

## Important Instructions for Claude

- Ask me ONE question at a time
- Wait for my response before continuing
- **RUN ALL COMMANDS AUTOMATICALLY** - Don't ask me to run them manually
- When you see "RUN this command" or "Run these commands", execute them using your Bash tool
- If I don't know something, help me or skip it
- Save files as we complete each section
- Be encouraging and explain why each step matters
- If errors occur, help me debug them
- For the Railway deployment, DO AS MUCH AUTOMATICALLY AS POSSIBLE
- Generate hashes, secrets, and execute all commands for me
- Only ask me for input when you absolutely need it (username, password, API keys, confirming interactive prompts)
- Save any important values (URLs, hashes, passwords) so you can reuse them later in the setup
- Upon completion of all setup, Read AGENTS.md and assume the role of Orchestrator as described

Let's start! Begin with the Prerequisites Check.
```

---

## What This Does

When you paste the prompt above, Claude Code becomes your personal setup assistant:

1. **Downloads & installs** — Clones repo and installs dependencies
2. **Configures API keys** — One-by-one walkthrough with detailed instructions
3. **Sets up Google integration** — Drive, Docs & Sheets for auto-documents and exports
4. **Creates agency profile** — Your brand voice and services
5. **Deploys dashboard to Railway** — Fully automated deployment with environment config
6. **Tests the system** — Verifies everything works
7. **Shows capabilities** — Tour of all 133 native skills

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
