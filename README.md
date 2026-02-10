# AIAA Agentic OS

An AI-powered agency operating system that runs inside Claude Code. Just paste prompts and Claude handles everything - from VSL funnels to cold emails to market research. Includes a web dashboard for monitoring workflows, 120 automated enforcement hooks, and a complete DOE architecture.

**Version:** 3.0 | **150 Workflows** | **120 Hooks** | **Last Updated:** February 2026

---

## System Architecture (DOE Pattern)

This system uses a **Directive-Orchestration-Execution (DOE)** architecture:

```
                         USER REQUEST
                "Create a VSL funnel for Acme Corp"
                              |
                              v
              +-------------------------------+
              |  DIRECTIVE (What to do)       |
              |  directives/*.md              |
              |  Natural language SOPs with   |
              |  inputs, steps, quality gates |
              +-------------------------------+
                              |
                              v
              +-------------------------------+
              |  ORCHESTRATION (Claude Code)  |
              |  Reads directives, loads      |
              |  skill bibles, calls scripts  |
              |  Hooks enforce compliance     |
              +-------------------------------+
                              |
                              v
              +-------------------------------+
              |  EXECUTION (Python scripts)   |
              |  execution/*.py               |
              |  Deterministic API calls and  |
              |  data processing              |
              +-------------------------------+
                              |
                              v
                           OUTPUT
              Local files, Google Docs, Slack
```

**Why DOE:** LLMs are probabilistic (90% accuracy = 59% over 5 steps). Push deterministic work into Python scripts. The orchestrator focuses on decision-making. Hooks enforce the pattern automatically.

---

## Directory Structure

```
AIAA-Agentic-OS/
|
|-- .claude/                    # Claude Code configuration
|   |-- hooks/                  # 120 enforcement hooks (Python)
|   `-- settings.local.json     # Hook registrations (126 entries)
|
|-- .env                        # API keys (never committed)
|-- .tmp/                       # Intermediate outputs (gitignored)
|-- credentials.json            # Google OAuth credentials
|-- token.pickle                # Google OAuth token
|
|-- context/                    # AGENCY CONTEXT - Who you are
|   |-- agency.md               # Agency info, services, positioning
|   |-- owner.md                # Owner profile, background, expertise
|   |-- brand_voice.md          # Tone, style, communication preferences
|   `-- services.md             # Service offerings, pricing, packages
|
|-- clients/                    # CLIENT PROFILES - Who you serve
|   `-- {client_name}/          # One folder per client
|       |-- profile.md          # Client info, business, goals
|       |-- rules.md            # Specific rules for this client
|       |-- preferences.md      # Style, tone, do's and don'ts
|       `-- history.md          # Past work, context, outcomes
|
|-- directives/                 # SOPs - What to do (150 files)
|   |-- vsl_funnel_orchestrator.md
|   |-- company_market_research.md
|   `-- ...
|
|-- execution/                  # Python scripts - Doing (151 files)
|   |-- generate_vsl_funnel.py
|   |-- create_google_doc.py
|   `-- ...
|
|-- skills/                     # Domain expertise (286 skill bibles)
|   |-- SKILL_BIBLE_*.md
|   `-- ...
|
|-- railway_apps/               # Dashboard deployment
|   `-- aiaa_dashboard/         # Flask dashboard app
|       |-- app.py
|       |-- Procfile
|       `-- requirements.txt
|
|-- AGENTS.md                   # Full agent instructions
|-- CLAUDE.md                   # Mirrored instructions for Claude Code
|-- QUICKSTART_PROMPT.md        # Setup prompt for new users
`-- requirements.txt            # Python dependencies
```

---

## Quick Start

**Prerequisites:** You just need TWO accounts - Claude will auto-install all tools!
- **GitHub account** - Sign up at https://github.com
- **Railway account** - Sign up at https://railway.app

Claude will automatically install: Homebrew, Python, Git, Node.js, Railway CLI, and the Railway skill.

**Open Claude Code and paste this entire prompt to get started:**

```
I want to set up AIAA Agentic OS v3.0. Please help me through the entire process interactively, asking me ONE question at a time and waiting for my response before moving on.

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

python3 execution/create_google_doc.py --test

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

Then RUN this command to generate the hash (using heredoc to avoid escape issues):

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

Check if it returns: {"status": "ok", "version": "3.0", "workflows": 150}

If successful, tell me "Dashboard is live!" If it fails, wait 30 seconds and try again (deployment may still be starting).

### 5f: Provide Login Details
Once everything is deployed, give me:
- Dashboard URL
- Username
- Password (the one I chose)
- Remind me to bookmark it!

Tell me: "Your AIAA Dashboard is now live! You can monitor all 150 workflows, manage environment variables, and track webhook events."

## Step 6: Test the System

Say: "Let's test the system with a quick workflow!"

Ask me: "What type of agency/business are you? (marketing/content/design/other)"

Based on my answer, RUN one of these test commands:
- If marketing: `python3 execution/write_cold_emails.py --sender "Test" --company "TestCo" --offer "Marketing services" --target "Small businesses"`
- If content: `python3 execution/generate_blog_post.py --topic "Getting started with AI" --length 500`
- If design: Ask for a sample project to research
- If other: `python3 execution/research_company_offer.py --company "Apple" --website "https://apple.com"`

Show me the output file location and tell me if it was successful.

## Step 7: Show What's Available

Give me a quick tour of the 150 workflows:

**Content Creation (25+ workflows):**
- Blog posts, LinkedIn posts, Twitter threads
- YouTube scripts, Instagram Reels
- Email newsletters, Content calendars

**Sales & Funnels (30+ workflows):**
- VSL scripts, Sales pages, Landing pages
- Cold email sequences, Follow-up automation
- Webinar funnels, Lead magnets

**Research & Intelligence (20+ workflows):**
- Company research, Competitor monitoring
- Prospect research, Market analysis
- Niche validation, Pricing strategy

**Lead Generation (15+ workflows):**
- Google Maps scraping, LinkedIn scraping
- Email enrichment, Lead scoring
- CRM automation, Prospecting pipelines

**Paid Advertising (15+ workflows):**
- Meta ad campaigns, Google Ads
- Ad creative generation, FB Ad Library analysis
- Video ad scripts, Static ad generation

**Client Management (20+ workflows):**
- Onboarding automation, QBR generation
- Churn risk alerts, Health scores
- Invoice generation, Testimonial requests

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
- Upon completion of all setup, Read agents.md and assume the role of Orchestrator as described

Let's start! Begin with the Prerequisites Check.
```

---

## What This Does

When you paste this prompt, Claude Code becomes your personal setup assistant:

1. **Downloads & installs** - Clones repo and installs dependencies
2. **Configures API keys** - One-by-one walkthrough with detailed instructions
3. **Sets up Google integration** - Drive, Docs & Sheets for auto-documents and exports
4. **Creates agency profile** - Your brand voice and services
5. **Deploys dashboard to Railway** - Fully automated deployment with environment config
6. **Tests the system** - Verifies everything works
7. **Shows capabilities** - Tour of all 150 workflows

---

## System Overview

| Resource | Count | Location |
|----------|-------|----------|
| Workflow Directives | 150 | `directives/` |
| Execution Scripts | 151 | `execution/` |
| Skill Bibles | 286 | `skills/` |
| Enforcement Hooks | 120 | `.claude/hooks/` |
| Hook Registrations | 126 | `.claude/settings.local.json` |

---

## Claude Code Hooks (Automated Enforcement)

The hook system is the enforcement layer of the DOE architecture. Every time Claude uses a tool (reading files, writing code, running commands), the relevant hooks fire automatically to enforce compliance, prevent mistakes, and track system health.

### How Hooks Work

```
Claude decides to use a tool
            |
            v
  +-------------------------+
  |  PreToolUse Hooks       |  <-- BEFORE the tool runs
  |  (52 registrations)     |
  |                         |
  |  Can BLOCK the action   |
  |  Can WARN the agent     |
  |  Can silently log       |
  +-------------------------+
            |
            v
     Tool executes
     (if not blocked)
            |
            v
  +-------------------------+
  |  PostToolUse Hooks      |  <-- AFTER the tool runs
  |  (74 registrations)     |
  |                         |
  |  Can REJECT the result  |
  |  Can flag quality       |
  |  Can track metrics      |
  +-------------------------+
            |
            v
  Claude continues with task
```

Hooks are Python scripts that receive tool call data via stdin and respond with exit codes (PreToolUse) or JSON decisions (PostToolUse). They use only Python standard library -- no pip dependencies.

### 15 Tiers of Enforcement

The 120 hooks are organized into 15 tiers, each targeting a specific layer of system reliability:

| Tier | Name | Hooks | Purpose |
|------|------|-------|---------|
| 1 | System Stability | 1-10 | Prevent dangerous operations, guard secrets, validate API keys |
| 2 | DOE Enforcement | 11-20 | Enforce DOE pattern, context loading, directive compliance |
| 3 | Quality Gates | 21-30 | Output validation, content length, markdown formatting |
| 4 | Operations | 31-40 | API cost tracking, rate limits, execution logging |
| 5 | Workflow Intelligence | 41-50 | VSL/cold email SOP compliance, funnel completeness |
| 6 | Pre-Execution Safety | 51-60 | Script validation, argument checking, dependency chains |
| 7 | Output Validation | 61-65 | JSON validation, Google Docs formatting, delivery pipeline |
| 8 | Railway & Deployment | 66-70 | Deploy guards, env var completeness, cron validation |
| 9 | Analytics | 71-75 | Session tracking, productivity scoring, word counts |
| 10 | Monitoring | 76-80 | Hook health, self-anneal tracking, daily summaries |
| 11 | DOE Structural Integrity | 81-90 | Directive completeness, phase ordering, SOP compliance |
| 12 | Content Intelligence | 91-100 | Brand voice, CTA validation, SEO, tone consistency |
| 13 | Execution Safety | 101-105 | API response validation, retry loops, path traversal |
| 14 | Client & Delivery | 106-115 | Client isolation, SLA monitoring, deliverable tracking |
| 15 | System Optimization | 116-120 | Bottleneck detection, quality trends, health reporting |

### Hook Behavior Summary

| Behavior | Count | What It Does |
|----------|-------|--------------|
| Hard Block | 14 | Stops dangerous actions (secrets in code, path traversal, command injection) |
| Warn / Info | 62 | Alerts on quality issues, missing context, SOP deviations |
| Silent Tracking | 44 | Logs metrics, patterns, and usage data for system improvement |

### Key Use Cases

**DOE Pattern Enforcement**

The `doe_enforcer` and `context_loader_enforcer` hooks ensure Claude follows the Directive-Orchestration-Execution pattern. If Claude tries to generate content without first loading `context/agency.md` or the relevant client profile, the hook warns. If a directive exists for the task but Claude skips it, the hook catches that too.

**Secret Protection**

The `secrets_guard` hook scans every file write for API keys, tokens, webhook URLs, and credentials. If Claude writes a hardcoded secret into a file, the hook blocks the write before it reaches disk. The `pii_detection_guard` does the same for personally identifiable information.

**Quality Gates on Output**

When Claude writes deliverables to `.tmp/`, hooks like `output_quality_gate`, `content_length_enforcer`, and `brand_voice_compliance` validate the output meets minimum standards. Sales copy gets checked for CTAs (`cta_validation`). Blog posts get checked for SEO keywords (`seo_keyword_validator`). Everything gets checked against the brand voice defined in `context/brand_voice.md`.

**Client Data Isolation**

The `multi_client_context_isolation` and `client_data_isolation_guard` hooks prevent cross-contamination between clients. If Claude is working on a deliverable for Client A and accidentally loads context from Client B, the hook catches it. The `client_rules_enforcer` makes sure client-specific rules from `clients/{name}/rules.md` are being followed.

**Workflow SOP Compliance**

Workflow-specific hooks like `vsl_workflow_enforcer` and `cold_email_workflow_enforcer` ensure Claude follows the step-by-step process defined in each directive. If the directive says "research first, then write," and Claude tries to skip research, the hook intervenes.

**Execution Safety**

Before running any Python script, hooks validate that the script exists (`script_exists_guard`), has valid arguments (`script_argument_validator`), and won't exceed resource limits (`memory_usage_estimator`). The `retry_loop_detector` catches infinite retry loops. The `command_injection_guard` blocks shell injection patterns.

**Self-Annealing Support**

After every task, hooks like `self_anneal_reminder` track whether Claude updated directives and skill bibles with what it learned. The `workflow_completion_tracker` and `error_categorizer` log patterns so the system improves over time. The `quality_trend_analyzer` identifies declining output quality before it becomes a problem.

### Hook State & Debugging

All hook state persists in `.tmp/hooks/*.json`. Every hook supports CLI flags:

```bash
# Check what a hook is tracking
python3 .claude/hooks/secrets_guard.py --status

# Reset a hook's state
python3 .claude/hooks/workflow_completion_tracker.py --reset

# Check system-wide hook health
python3 .claude/hooks/system_health_reporter.py --status
```

---

## What You Can Do

Once set up, just tell Claude what you need. Here are example prompts:

### Sales Copy

**VSL Funnel:**
```
Create a complete VSL funnel for [COMPANY NAME]. Their website is [WEBSITE] and they sell [PRODUCT/SERVICE] to [TARGET AUDIENCE].
```

**Sales Page:**
```
Write a long-form sales page for [PRODUCT]. Price point is [PRICE]. Target audience is [AUDIENCE]. Focus on [MAIN BENEFIT].
```

**Cold Emails:**
```
Write a cold email sequence for my [SERVICE] targeting [INDUSTRY]. I'm [YOUR NAME] from [YOUR COMPANY]. Focus on [PAIN POINT].
```

### Content Creation

**Blog Post:**
```
Write a 1500-word blog post about [TOPIC] for [TARGET AUDIENCE]. Tone should be [PROFESSIONAL/CASUAL/etc].
```

**LinkedIn Post:**
```
Write a LinkedIn post about [TOPIC]. Style: [STORY/EDUCATIONAL/LISTICLE]. Make it engaging and end with a call to action.
```

**YouTube Script:**
```
Write a YouTube script about [TOPIC]. Target length: [X] minutes. Style: [EDUCATIONAL/TUTORIAL/STORY].
```

### Research

**Company Research:**
```
Research [COMPANY NAME]. Their website is [WEBSITE]. I need to understand their business model, target audience, competitors, and positioning.
```

**Market Research:**
```
Research the [INDUSTRY] market. I need to understand key players, trends, opportunities, and challenges.
```

### Ad Creatives

**Meta Ads Campaign (with AI images):**
```
Generate a Meta ads campaign for [PRODUCT] targeting [AUDIENCE]. Generate images for the ads.
```

**Static Ad Creatives:**
```
Create static ad creatives for [PRODUCT] on [PLATFORM]. Generate the actual images.
```

### Lead Generation

**Google Maps Leads:**
```
Find [BUSINESS TYPE] in [LOCATION]. I need their name, address, phone, website, and reviews.
```

**LinkedIn Scraping:**
```
Find [JOB TITLES] at companies in [INDUSTRY] located in [LOCATION].
```

### Landing Pages

**AI Landing Page:**
```
Generate a landing page for [PRODUCT] targeting [AUDIENCE]. Style: [modern-gradient/neo-noir/editorial-luxury]. Deploy to Cloudflare.
```

### Client Work

**Add a New Client:**
```
Help me add a new client: [CLIENT NAME]. Their website is [WEBSITE]. They're in the [INDUSTRY] industry and sell [PRODUCTS/SERVICES] to [AUDIENCE].
```

**Monthly Report:**
```
Create a monthly report for [CLIENT NAME]. Key metrics: [LIST METRICS]. Highlights: [ACHIEVEMENTS].
```

---

## AIAA Dashboard

A web dashboard for monitoring and managing your AIAA system. Deploy to Railway in minutes.

### Dashboard Features

- **150 Documented Workflows** - Full descriptions, prerequisites, how-to-run instructions
- **Active Workflow Management** - Run Now, Schedule Editor, Cron Toggle
- **Webhook Workflows** - Register, test, toggle, and delete webhooks with optional HTTP forwarding to standalone services
- **Project-Wide Shared Variables** - Set API keys once, all services inherit them automatically
- **Light/Dark Mode** - Toggle with localStorage persistence
- **Environment Variables** - View and set API keys from the UI (sets project-wide shared variables)
- **Real-time Logs** - See all workflow executions and webhook events
- **Mobile Responsive** - Works on phones and tablets
- **Password Protected** - Secure SHA-256 hashed login

### Deploy to Railway

**Prerequisites:**
- Railway account (https://railway.app)
- Railway CLI installed: `npm install -g @railway/cli`

```bash
railway login
cd railway_apps/aiaa_dashboard
railway init       # Select "Empty Project"
railway up         # Deploy
railway domain     # Generate public URL
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

Shared variables are set via the dashboard's Environment page (which calls the Railway API internally) or via the `/api/shared-variables/sync` endpoint. New services automatically inherit all shared variables.

### Deploy Workflows

All workflows are deployed via a single unified script:

```bash
# Cron workflow (runs on schedule)
python3 execution/deploy_to_railway.py --directive x_keyword_youtube_content --type cron --schedule "0 */3 * * *" --auto

# Webhook workflow (triggered by external events)
python3 execution/deploy_to_railway.py --directive calendly_meeting_prep --type webhook --slug calendly --slack-notify --auto

# Web service (always-on)
python3 execution/deploy_to_railway.py --directive ai_news_digest --type web --auto

# List deployable directives
python3 execution/deploy_to_railway.py --list
```

Every workflow deploys as a standalone Railway service. API keys are synced as project-level shared variables (not duplicated per service). The deploy script handles scaffolding, deployment, env var sync, cron configuration, webhook registration, and dashboard config updates.

**Generate password hash:**
```bash
python3 << 'PYHASH'
import hashlib
password = "YOUR_PASSWORD_HERE"
print(hashlib.sha256(password.encode()).hexdigest())
PYHASH
```

---

## Context System

### Your Agency (`context/` folder)
- `agency.md` - Your agency name, positioning, mission
- `brand_voice.md` - Your tone and style guidelines
- `services.md` - What you offer
- `owner.md` - Owner profile and background

### Your Clients (`clients/{name}/` folders)
- `profile.md` - Client business info, goals, audience
- `rules.md` - Content rules and compliance requirements
- `preferences.md` - Their style preferences
- `history.md` - Past work and outcomes

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
| VSL Script | 2,500-3,000 words (16-20 min video) |
| Sales Page | 1,500-3,000 words |
| Blog Post | 1,500-2,500 words |
| Email | 300-500 words each |

---

## License

Private repository - Client Ascension internal use.
