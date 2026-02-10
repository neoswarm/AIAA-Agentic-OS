# Deploy Workflow to Modal AI

> **Status:** Production Ready | **Last Updated:** February 4, 2026

## What This Workflow Is
Fully automated deployment of any workflow to Modal AI as a serverless webhook. The agent handles ALL setup automatically - just say "deploy X to Modal" and get back working endpoints.

## What It Does
1. Auto-detects if Modal CLI is installed (installs if missing)
2. Auto-creates any missing Modal secrets from .env
3. Parses target directive to extract requirements
4. Auto-detects execution scripts (only includes ones that exist)
5. Uploads required skill bibles (only ones referenced in directive)
6. Uploads Google OAuth tokens for Docs/Sheets/Gmail integrations
7. Generates Modal app with timestamp-based cache busting
8. Deploys and returns ready-to-use webhook URLs

## Agent Instructions

When user says "deploy [workflow] to Modal":

### Step 1: Run Auto-Deploy
```bash
python3 execution/deploy_to_modal.py --directive [workflow_name] --auto
```

The `--auto` flag:
- Skips all confirmation prompts
- Auto-creates missing secrets from .env
- Generates fresh Modal app with cache-busting timestamp
- Deploys immediately
- Returns clean JSON output with endpoints

### Step 2: Return Results to User
After successful deployment, provide:

```
Deployment Complete: [workflow_name]

Webhook URL (POST):
https://[workspace]--[app]-webhook.modal.run

Health Check (GET):
https://[workspace]--[app]-health.modal.run

Info (GET):
https://[workspace]--[app]-info.modal.run

Example Usage:
curl -X POST "[webhook_url]" \
  -H "Content-Type: application/json" \
  -d '{"data": {"param1": "value1"}}'
```

## How to Run (Manual)
```bash
# Fully automated deploy (agent use)
python3 execution/deploy_to_modal.py --directive stripe_client_onboarding --auto

# Interactive deploy (human use)
python3 execution/deploy_to_modal.py --directive stripe_client_onboarding

# List all deployable workflows
python3 execution/deploy_to_modal.py --list

# Check workflow requirements before deploying
python3 execution/deploy_to_modal.py --info stripe_client_onboarding

# Setup secrets only (first time)
python3 execution/deploy_to_modal.py --setup-secrets

# Dry run (generate without deploying)
python3 execution/deploy_to_modal.py --directive stripe_client_onboarding --dry-run
```

## Inputs
- **directive**: string (required) - Name of workflow to deploy (without .md)
- **auto**: flag - Fully automated mode, no prompts, JSON output
- **app-name**: string - Custom Modal app name (defaults to directive name)
- **dry-run**: flag - Generate Modal app file without deploying
- **force**: flag - Skip confirmation prompts in interactive mode

## Auto-Setup Behavior

### Modal CLI
If not installed, script runs:
```bash
pip install modal
python3 -m modal setup
```

### Secrets Auto-Creation
Reads from `.env` and creates Modal secrets:
| .env Variable | Modal Secret |
|---------------|--------------|
| OPENROUTER_API_KEY | openrouter-secret |
| ANTHROPIC_API_KEY | anthropic-secret |
| SLACK_WEBHOOK_URL | slack-webhook |

### Google OAuth Tokens
For workflows using Google integrations, automatically uploads:
- `token_docs.json` → `/app/token_docs.json` AND `/app/token.json`
- `token_gmail.json` → `/app/token_gmail.json`
- `credentials.json` → `/app/credentials.json`
- `token.pickle` → `/app/token.pickle`

### Skill Bibles
Parses directive for skill bible references and uploads only those needed:
- Pattern: `SKILL_BIBLE_*.md` or `skills/SKILL_BIBLE_*`
- Uploaded to `/app/skills/` on Modal

### Execution Scripts
Auto-detects scripts referenced in directive and validates they exist:
- Only includes scripts that exist in `execution/`
- Falls back to directive name as script name if no matches

### Default Packages
All deployments include:
- anthropic, openai, python-dotenv, requests, fastapi
- pandas, apify-client, slack-sdk
- google-auth, google-auth-oauthlib, google-api-python-client, gspread (if Google integration detected)

### Cache Busting
Each deployment includes a BUILD_VERSION timestamp that forces Modal to rebuild the image, ensuring code changes are always deployed.

## Output Format (--auto mode)
```json
{
  "status": "success",
  "directive": "stripe_client_onboarding",
  "description": "Automated client onboarding triggered by Stripe...",
  "endpoints": {
    "webhook": "https://lucas-37998--stripe-client-onboarding-webhook.modal.run",
    "health": "https://lucas-37998--stripe-client-onboarding-health.modal.run",
    "info": "https://lucas-37998--stripe-client-onboarding-info.modal.run"
  },
  "example_curl": "curl -X POST '...' -d '{...}'"
}
```

## Webhook Payload Format
Send POST requests with this structure:
```json
{
  "data": {
    "param_name": "value",
    "another_param": "value"
  }
}
```

Parameters are passed to the execution script as CLI args:
`--param_name "value" --another_param "value"`

## Critical: dotenv Import Pattern for Modal

**BREAKING BUG:** Scripts that bundle `requests` and `dotenv` in the same `try/except` with `sys.exit(1)` will crash on Modal because `python-dotenv` is not installed in the Modal container image. Modal injects env vars via secrets -- no `.env` file is needed.

**Bad (crashes Modal container):**
```python
try:
    import requests
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Error: pip install requests python-dotenv")
    sys.exit(1)
```

**Good (works locally AND on Modal):**
```python
try:
    import requests
except ImportError:
    print("Error: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Not needed on Modal -- env vars injected via secrets
```

**Before deploying any script to Modal**, check its import block and fix this pattern. As of February 2026, 37 scripts in `execution/` still have the crash-causing version.

## Debugging Failed Deployments

When a Modal deployment hangs (requests connect but never return), check container logs:
```bash
modal app logs <app-name>
```

Common causes:
1. **Import crash** (dotenv pattern above) -- container dies on startup, no response sent
2. **Missing secret** -- function can't start without its declared secrets
3. **Cold start timeout** -- first request after idle may take 2-10 seconds

## Edge Cases
- Modal not installed → Auto-installs with pip
- Modal not authenticated → Prompts one-time browser auth
- Missing .env keys → Skips those secrets, deploys anyway
- Directive not found → Returns error with available list
- Script not found → Falls back to directive name or first existing script
- Google token missing → Skips Google token upload, may fail at runtime
- **8 endpoint limit reached** → Stop unused apps with `modal app stop <app-id>`, then redeploy

## Quality Gates
- [ ] Modal CLI accessible
- [ ] At least one LLM secret available (openrouter or anthropic)
- [ ] Directive exists and parses correctly
- [ ] At least one execution script exists
- [ ] Deployment returns valid URL
- [ ] Health endpoint responds

## Testing a Deployment
```bash
# Check health
curl https://[workspace]--[app]-health.modal.run

# Get workflow info
curl https://[workspace]--[app]-info.modal.run

# Trigger workflow
curl -X POST "https://[workspace]--[app]-webhook.modal.run" \
  -H "Content-Type: application/json" \
  -d '{"data": {"client_name": "Test", "client_email": "test@example.com"}}'
```

## Modal Free Tier Limits
- **8 web endpoints max** (across ALL deployed apps combined)
- 30 compute hours/month
- Cold starts: 2-10 seconds after ~15min idle

### Managing Endpoint Limits
```bash
# List all apps and their state
modal app list

# Stop an app to free endpoints (2 per app: webhook + health)
modal app stop <app-id>

# Check logs for a deployed app
modal app logs <app-name>

# List configured secrets
modal secret list
```

## Related
- All directives in `directives/*.md` are deployable
- Generated apps saved to `execution/modal_apps/`
- Execution scripts in `execution/*.py`
- Skill bibles in `skills/SKILL_BIBLE_*.md`
