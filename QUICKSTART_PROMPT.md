# AIAA Agentic OS -- Quick Start

**Version 5.0** | **133 Native Skills** | **Skills-First Agency Operating System**

---

## Before You Start

1. **Install Claude Code** (your AI setup assistant):
   - **Mac:** Press Cmd+Space, type "Terminal", press Enter
   - **Windows:** Install WSL first: https://learn.microsoft.com/en-us/windows/wsl/install
   - **Linux:** Press Ctrl+Alt+T
   - If you don't have Node.js, install it from https://nodejs.org (download LTS, run the installer)
   - Then paste this into your terminal: `npm install -g @anthropic-ai/claude-code`
   - Type `claude` to launch it

2. **Create a GitHub account** if you don't have one: https://github.com

That's it. Pick one of the three options below.

---

## Option A: Auto-Installer (easiest -- no Claude Code needed)

Paste this one line into your terminal. It installs everything and walks you through setup:

```bash
curl -fsSL https://raw.githubusercontent.com/lucassynnott/AIAA-Agentic-OS/main/install.sh | bash
```

This installs Python, Git, Node.js, Claude Code, and Railway CLI automatically, clones the repo, then launches an interactive setup wizard that asks for your API key and configures everything. Takes about 5 minutes. By default, this installs core dependencies only. Use `install.sh --full` to install all 133 skill dependencies.

---

## Option B: One-Liner (if you already have Claude Code open)

Type this into Claude Code:

```
Clone https://github.com/lucassynnott/AIAA-Agentic-OS and set it up for me following QUICKSTART_PROMPT.md. Ask me one question at a time.
```

---

## Option C: Full Setup Prompt

Copy everything between the lines below and paste it into Claude Code:

```
═══════════════════════════════════════════════════════════
      COPY EVERYTHING BELOW THIS LINE
═══════════════════════════════════════════════════════════

Set up AIAA Agentic OS v5.0 for me. One question at a time. Wait for my answer before moving on.

If anything goes wrong at any step, just diagnose and fix it. If I say "skip", move to the next step. If I say "something broke", stop and help me.

STEP 1 — INSTALL
Ensure Python 3.8+, Git, and Node.js are installed. Auto-install anything missing.
Clone https://github.com/lucassynnott/AIAA-Agentic-OS/ and run pip install -r requirements.txt.
(This installs core deps. For all skills: `pip install -r requirements-full.txt`)
Then read CLAUDE.md so you understand the system.

STEP 2 — ONE API KEY (required, 5 min)
I need ONE key to start: OpenRouter (powers all AI features).
Walk me through getting it:
  1. Sign up at https://openrouter.ai
  2. Profile icon → Keys → Create Key → name it "AIAA"
  3. Copy the key (starts with sk-or-). Add $5-10 credits.
Ask me to paste it. Create .env from .env.example with it.

STEP 3 — FIRST WIN (see the system work)
Ask what type of business I run (marketing / content / design / other).
Run a matching test skill so I can see real output immediately:
  - Marketing → cold-email-campaign with test data
  - Content → blog-post with a sample topic
  - Other → company-research on a well-known company
Show me where the output file is. Celebrate the win.

STEP 4 — AGENCY PROFILE (optional)
Ask if I want to personalize the system. If yes, ask me about my agency name,
services, target audience, brand voice, and founder info one question at a time.
Save to context/agency.md, context/brand_voice.md, context/services.md, context/owner.md.
If I say skip, move on.

STEP 5 — MORE API KEYS (optional)
Ask if I want to add research and notifications now or later. If yes:
  - Perplexity (research): sign up at https://perplexity.ai → Settings → API
  - Slack (notifications): https://api.slack.com/apps → Create App → Incoming Webhooks
Update .env with whatever I provide. If I say skip, move on.

STEP 6 — WEB DASHBOARD (optional)
Ask if I want a web dashboard to monitor skills and executions.
If yes: install Railway CLI, walk me through railway login (a browser
tab will open -- tell me exactly what I'll see and when to come back),
ask for a dashboard username and password, then deploy
railway_apps/aiaa_dashboard/ to Railway. Set all env vars including
DASHBOARD_USERNAME, DASHBOARD_PASSWORD_HASH (SHA-256), FLASK_SECRET_KEY,
and any API keys from .env. Generate a public domain. Verify /health.
Give me my URL and login credentials.
If I say skip, say I can deploy it anytime later.

STEP 7 — GOOGLE DOCS (optional)
Ask if I want auto-delivery to Google Docs. If yes, walk me through
Google Cloud OAuth setup (create project, enable Docs/Sheets/Drive APIs,
create OAuth credentials, download credentials.json, test it).
If I say skip, say the system works fine without it.

RULES
- Run all commands automatically. Never ask me to type commands.
- When a browser opens for authentication, tell me: "A tab opened in your
  browser. Do [X] there. When the page says you can close it, come back
  here and say 'done'."
- After setup, read AGENTS.md and become the skills-first orchestrator.
- For deploying scheduled workflows later, see PUBLISHING.md.
- Run `bash install.sh --verify` to re-check the installation at any time.

Let's go. Start with Step 1.

═══════════════════════════════════════════════════════════
      STOP COPYING HERE
═══════════════════════════════════════════════════════════
```

---

## What Happens Next

Claude Code becomes your personal setup assistant:

1. **Installs everything** -- Python, Git, Node, all dependencies (2 min)
2. **Gets your AI key** -- One key, one signup, five minutes
3. **Shows you it works** -- Runs a real skill so you see output immediately
4. **Personalizes (optional)** -- Your agency name, voice, services
5. **More keys (optional)** -- Research and notifications
6. **Dashboard (optional)** -- Web UI at a public URL to monitor everything
7. **Google Docs (optional)** -- Auto-deliver content to Google Docs

**First win in under 5 minutes. Full setup in 15-30.**

---

## After Setup

Just tell Claude what you need. It finds the right skill from 133 available and handles everything:

- "Write cold emails for Acme Corp targeting marketing agencies"
- "Research the AI automation market"
- "Create a VSL funnel for my coaching program"
- "Write a blog post about getting started with AI"
- "Find leads for plumbers in Austin, Texas"
- "Generate a Meta ads campaign for my SaaS product"

Browse all skills: `ls .claude/skills/`

Full documentation: `CLAUDE.md` and `AGENTS.md`

---

## Troubleshooting

**Something broke during setup?** Just tell Claude "something broke" and it will diagnose the issue.

**Locked out of dashboard?** Visit your dashboard URL + `/setup` to reset credentials. Or run:
```bash
railway variables set DASHBOARD_PASSWORD_HASH=""
```
Then visit `/setup` to set a new password.

**Need to re-run setup?** Just paste the prompt again. Claude will detect what's already done and skip ahead.

---

## Support

- **GitHub Issues:** https://github.com/lucassynnott/AIAA-Agentic-OS/issues
- **Full Docs:** `CLAUDE.md` (system brain) and `AGENTS.md` (complete reference)
- **Publishing Workflows:** `PUBLISHING.md`
