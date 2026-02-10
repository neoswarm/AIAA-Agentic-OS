# Deploy Workflow to Railway

> **Status:** Production Ready | **Last Updated:** February 9, 2026

## What This Workflow Is
Unified deployment of any AIAA workflow to the user's Railway project. **Every workflow gets deployed as a standalone Railway service** with its own code and URL. **All API keys are project-level shared variables** -- new services inherit them automatically. The dashboard provides visibility and management (toggle, test, run now). Handles cron jobs (scheduled), webhook workflows (event-triggered), and web services (always-on). Automatically discovers the dashboard project, scaffolds files, syncs shared variables, configures cron schedules, and registers the workflow in the dashboard.

## What It Does
1. Parses the target directive to extract scripts, integrations, and env var requirements
2. Discovers the user's Railway project from `workflow_config.json` or Railway CLI config
3. Auto-detects deployment type (cron / webhook / web) from directive content
4. Scaffolds a standalone service in `railway_apps/<name>/` with all required files
5. Deploys to Railway via CLI, confirms cron via GraphQL (if cron)
6. **Syncs API keys as project-level shared variables** via the dashboard's `/api/shared-variables/sync` endpoint (all services inherit them automatically). Only service-specific vars (e.g. GOOGLE_OAUTH_TOKEN_PICKLE) are set per-service.
7. For webhook type: gets the service's public URL, then registers a dashboard webhook with `forward_url` pointing to the new service
8. Registers the workflow in `workflow_config.json` for dashboard display

## Trigger Phrases
- "deploy this workflow to Railway"
- "deploy X to my dashboard"
- "publish X as a cron"
- "add X as a webhook"
- "schedule X to run every 3 hours"
- "deploy this as a webhook"

## Agent Instructions

When user says "deploy [workflow] to Railway" or "deploy [workflow] to my dashboard":

### Step 1: Determine Type
Ask the user or auto-detect:
- **Cron**: Runs on a schedule (every N hours/days). Requires `--schedule`.
- **Webhook**: Triggered by external events (Calendly, Stripe, etc.). Registered via dashboard API, no rebuild.
- **Web**: Always-on service with HTTP endpoints.

### Step 2: Run Deploy
```bash
# Cron workflow
python3 execution/deploy_to_railway.py --directive [workflow_name] --type cron --schedule "0 */3 * * *" --auto

# Webhook workflow (no rebuild needed)
python3 execution/deploy_to_railway.py --directive [workflow_name] --type webhook --slug [slug-name] --slack-notify --auto

# Web service
python3 execution/deploy_to_railway.py --directive [workflow_name] --type web --auto

# Auto-detect type
python3 execution/deploy_to_railway.py --directive [workflow_name] --auto
```

### Step 3: Return Results
After deployment, tell the user:
- Service name and type
- Cron schedule (if cron)
- Webhook URL (if webhook)
- Whether it's visible in the dashboard
- Any env vars that were missing

## How to Run
```bash
# Fully automated cron deploy
python3 execution/deploy_to_railway.py --directive x_keyword_youtube_content --type cron --schedule "0 */3 * * *" --auto

# Fully automated webhook deploy
python3 execution/deploy_to_railway.py --directive calendly_meeting_prep --type webhook --slug calendly --slack-notify --auto

# Web service deploy
python3 execution/deploy_to_railway.py --directive ai_news_digest --type web --auto

# Check what a directive needs before deploying
python3 execution/deploy_to_railway.py --directive calendly_meeting_prep --info

# Preview without deploying
python3 execution/deploy_to_railway.py --directive x_keyword_youtube_content --type cron --schedule "0 */3 * * *" --dry-run

# List all deployable directives
python3 execution/deploy_to_railway.py --list
```

## Inputs
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| directive | string | Yes | Directive name without .md extension |
| type | string | No | `cron`, `webhook`, or `web` (auto-detected if omitted) |
| schedule | string | Cron only | Cron expression (e.g. `0 */3 * * *`) |
| slug | string | Webhook only | URL slug for webhook endpoint |
| forward-url | string | No | URL to forward webhook payloads to |
| slack-notify | flag | No | Enable Slack notifications (webhook) |
| auto | flag | No | Fully automated, no prompts |
| dry-run | flag | No | Show plan without executing |
| list | flag | No | List all deployable directives |
| info | flag | No | Show deployment requirements |

## How It Works

### Project Discovery
The script discovers the user's Railway project automatically:
1. Reads `project_id` from `railway_apps/aiaa_dashboard/workflow_config.json` (set during onboarding)
2. Falls back to `~/.railway/config.json` (Railway CLI stores per-directory project linkages)
3. Falls back to `railway status --json` from the dashboard directory

All workflows deploy to the **same Railway project** as the dashboard.

### Architecture: Every Workflow = Standalone Service

**All workflow types get deployed as their own Railway service.** The dashboard provides visibility and management on top.

| Step | Cron | Webhook | Web |
|------|------|---------|-----|
| Scaffold files | `run.py` + `railway.json` | `app.py` + `Procfile` + `railway.json` | `app.py` + `Procfile` + `railway.json` |
| Per-service requirements.txt | Yes (import scan) | Yes (import scan) | Yes (import scan) |
| Railway deploy | `railway up --service <name>` | `railway up --service <name>` | `railway up --service <name>` |
| Sync shared variables | API keys via dashboard `/api/shared-variables/sync` | Same | Same |
| Service-specific vars | Only non-API-key vars (e.g. GOOGLE_OAUTH_TOKEN_PICKLE) | Same | Same |
| Set cron via GraphQL | `serviceInstanceUpdate` | -- | -- |
| Get public domain | -- | Yes (for forwarding) | Yes |
| Dashboard webhook registration | -- | Yes (with `forward_url` -> service) | -- |
| workflow_config.json | Yes | Yes | Yes |

### Generated File Structure (Cron)
```
railway_apps/<service-name>/
├── run.py              # Wrapper that calls the execution script
├── <script>.py         # Copy of the execution script
├── railway.json        # Standardized config (always JSON, never TOML)
└── requirements.txt    # Per-service dependencies (auto-detected from imports)
```

### Generated File Structure (Webhook / Web)
```
railway_apps/<service-name>/
├── app.py              # Flask app with /health and /webhook endpoints
├── <script>.py         # Copy of the execution script
├── railway.json        # Standardized config
├── requirements.txt    # Per-service dependencies
└── Procfile            # gunicorn start command
```

### Webhook Flow
When type is webhook, the deploy does two things:
1. Deploys a standalone Flask service with a `/webhook` POST endpoint (does the heavy processing)
2. Registers a webhook slug on the dashboard with `forward_url` pointing to `https://<service-domain>/webhook`

External services (Calendly, Stripe, etc.) POST to the dashboard webhook URL. The dashboard forwards the payload to the standalone service for processing.

## Prerequisites
- Railway CLI installed and authenticated (`railway login`)
- Dashboard deployed to Railway (`python3 execution/deploy_aiaa_dashboard.py`)
- Local `.env` file with required API keys
- For webhook type: `DASHBOARD_PASSWORD` env var set

## Critical Gotchas

### Railway CLI
| Issue | Solution |
|-------|----------|
| `railway link` positional arg fails | Script uses `railway link -p <PROJECT_ID>` with `-p` flag |
| `railway up` fails with "multiple services" | Script uses `--service <name>` flag |
| `railway service status --all` shows deployment IDs | Script uses `--json` for actual service IDs |

### Railway GraphQL API
| Issue | Solution |
|-------|----------|
| `railway.json` cronSchedule only on first deploy | Script confirms cron via `serviceInstanceUpdate` mutation |
| `cronSchedule: ""` causes errors | Script uses `null` to disable, valid expression to enable |
| `variableUpsert` can timeout (504) | Script uses Railway CLI for env vars instead |

### Environment Variables
| Issue | Solution |
|-------|----------|
| API keys duplicated per service | All API keys are now **project-level shared variables** -- set once, inherited by every service |
| Google API fails silently | Script auto-encodes and sets `GOOGLE_OAUTH_TOKEN_PICKLE` as a per-service var |
| Missing API keys | `--info` flag shows what's needed; `--dry-run` previews without deploying |
| Shared vars API only works inside Railway | Dashboard provides `/api/shared-variables/sync` endpoint that proxies to Railway GraphQL API |

### Dashboard Integration
| Issue | Solution |
|-------|----------|
| Cron service not in dashboard | Cron services auto-appear if dashboard has `RAILWAY_API_TOKEN` |
| Shows raw service name | `workflow_config.json` updated with friendly name; redeploy dashboard |
| Webhook not registered | Script calls dashboard API directly; no rebuild needed |

## Quality Gates
- [ ] Railway CLI accessible and authenticated
- [ ] Project discovered from workflow_config.json or Railway CLI
- [ ] All required env vars present in .env
- [ ] Deployment status is SUCCESS
- [ ] Cron schedule confirmed via GraphQL API (cron type)
- [ ] Webhook registered and returning 200 (webhook type)
- [ ] Workflow visible in dashboard Active Workflows page

## Edge Cases
- Directive not found: returns error with `--list` suggestion
- No Railway project: tells user to deploy dashboard first
- Missing .env keys: warns but continues (some may be optional)
- Service directory already exists: overwrites scaffolded files
- Dashboard URL not discoverable: falls back to `DASHBOARD_URL` env var
- Railway CLI not installed: immediate error with install instructions

## Related
- `execution/deploy_to_modal.py` -- Same concept for Modal serverless
- `execution/deploy_aiaa_dashboard.py` -- Deploys the dashboard itself
- `execution/deploy_webhook_workflow.py` -- Standalone webhook registration (still works)
- `railway_apps/aiaa_dashboard/workflow_config.json` -- Dashboard workflow metadata

## Self-Annealing Notes

### 2026-02-09: Initial Creation (Unified)
- **Merged** `deploy_workflow_to_dashboard.md` (cron) + `deploy_webhook_workflow_to_dashboard.md` (webhook) into single directive
- **New execution script**: `deploy_to_railway.py` handles all three types (cron, webhook, web)
- **Project discovery**: Reads from workflow_config.json → Railway CLI config → railway status
- **Architecture**: Mirrors `deploy_to_modal.py` pattern -- parse directive, scaffold, deploy, verify
- **Key design**: All configs standardized on `railway.json` (no more TOML inconsistency)
- **Import scanning**: Uses AST parser to detect pip packages from execution script imports

### 2026-02-09: Project-Level Shared Variables
- **Architecture change**: All API keys (OPENROUTER_API_KEY, PERPLEXITY_API_KEY, SLACK_WEBHOOK_URL, ANTHROPIC_API_KEY, FAL_KEY, etc.) are now set as **project-level shared variables** via the dashboard's `/api/shared-variables/sync` endpoint
- **Rationale**: Railway's GraphQL API only works from inside their network; the dashboard (running inside Railway) proxies these calls
- **Deploy script**: Splits env vars into shared (API keys) and service-specific (GOOGLE_OAUTH_TOKEN_PICKLE, etc.)
- **Dashboard env page**: Setting any variable from the UI now creates a project-wide shared variable via Railway API
- **Dashboard API endpoints**: Added `/api/shared-variables` (GET), `/api/shared-variables/set` (POST), `/api/shared-variables/sync` (POST bulk)
- **Fallback**: If the dashboard is unreachable, falls back to per-service variable setting via CLI

### 2026-02-09: Standalone Service for All Types
- **Architecture change**: ALL workflow types (including webhook) deploy as standalone Railway services
- **Webhook flow**: Deploy standalone Flask service → get public domain → register dashboard webhook with `forward_url` pointing to service
- **Rationale**: Webhook-triggered workflows (e.g. calendly_meeting_prep) need heavy processing (API calls, research, doc creation) that can't run inside the dashboard's simple webhook handler
- **Dashboard role**: Visibility layer only -- toggle, test, copy URL, delete. Processing happens in the standalone service.
- **Domain discovery**: Uses `railway domain` CLI command to get/generate service URLs after deployment
