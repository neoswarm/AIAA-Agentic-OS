# Deploy Workflow to Dashboard

## What This Workflow Is

Complete, error-free deployment of any AIAA workflow to the Railway dashboard. This directive captures all learnings from debugging deployment issues and ensures zero-error deployments.

## Trigger Phrases

- "deploy this workflow to my dashboard"
- "publish this workflow"
- "add this to the dashboard"
- "deploy [workflow_name] to Railway"

## Prerequisites

Before starting, ensure:
- [ ] Railway CLI installed and authenticated (`railway login`)
- [ ] Railway project exists with dashboard deployed
- [ ] Local `.env` file has all required API keys
- [ ] `token.pickle` exists if workflow uses Google APIs

## Step-by-Step Deployment Process

### Phase 1: Pre-Deployment Checks

```bash
# 1. Verify Railway CLI is authenticated
railway whoami

# 2. Get project and service IDs (save these!)
cd railway_apps/aiaa_dashboard
railway status

# 3. Check what services exist in the project
railway service status --all --json
# The "id" field in JSON output is the SERVICE ID
# WARNING: plain-text output shows DEPLOYMENT IDs in the middle column, not service IDs
```

### Phase 2: Identify Workflow Requirements

```bash
# 1. Check what API keys the workflow needs
grep -E "os\.getenv|os\.environ" railway_apps/<workflow_name>/*.py

# 2. Check if workflow uses Google APIs
grep -l "google" railway_apps/<workflow_name>/*.py && echo "NEEDS GOOGLE_OAUTH_TOKEN_PICKLE"

# 3. Check if workflow has a cron schedule
cat railway_apps/<workflow_name>/railway.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('deploy',{}).get('cronSchedule','NOT SET'))"
```

### Phase 3: Deploy the Workflow Service

```bash
cd railway_apps/<workflow_name>

# Link to the SAME project as the dashboard (MUST use -p flag, positional arg fails)
railway link -p 3b96c81f-9518-4131-b2bc-bcd7a524a5ef

# Deploy to Railway (creates new service if doesn't exist)
# With multiple services, MUST specify --service flag
railway up --detach --service <workflow_name>

# Check deployment status (wait for SUCCESS)
railway service status --all
```

### Phase 4: Set Environment Variables

**CRITICAL: Set ALL required variables. Missing any will cause silent failures.**

```bash
cd railway_apps/<workflow_name>

# Preferred method: Railway CLI
railway variable set OPENROUTER_API_KEY="$(grep OPENROUTER_API_KEY ../../.env | cut -d'=' -f2)" --service <workflow_name>
railway variable set SLACK_WEBHOOK_URL="$(grep SLACK_WEBHOOK_URL ../../.env | cut -d'=' -f2)" --service <workflow_name>
railway variable set ANTHROPIC_API_KEY="$(grep ANTHROPIC_API_KEY ../../.env | cut -d'=' -f2)" --service <workflow_name>
railway variable set PERPLEXITY_API_KEY="$(grep PERPLEXITY_API_KEY ../../.env | cut -d'=' -f2)" --service <workflow_name>

# For Google API workflows ONLY
GOOGLE_TOKEN=$(python3 -c "import base64; print(base64.b64encode(open('../../token.pickle','rb').read()).decode())")
railway variable set GOOGLE_OAUTH_TOKEN_PICKLE="$GOOGLE_TOKEN" --service <workflow_name>

# Verify all variables are set
railway variables --json --service <workflow_name> | python3 -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(d.keys()))"
```

**FALLBACK if `railway variable set` times out (504 errors):**
Embed credentials directly in the workflow Python code with env var fallback:
```python
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL") or "hardcoded_fallback_value"
GOOGLE_OAUTH_TOKEN_PICKLE = os.getenv("GOOGLE_OAUTH_TOKEN_PICKLE") or "base64_encoded_fallback"
```
This pattern is the proven workaround when Railway's `variableUpsert` API is unreliable.

### Phase 5: Set Cron Schedule via GraphQL

**IMPORTANT:** `railway.json`'s `cronSchedule` is only applied on initial deploy. For reliability, always confirm via GraphQL mutation.

```bash
# Get the Railway API token
TOKEN=$(python3 -c "import json; d=json.load(open('$HOME/.railway/config.json')); print(d.get('user', {}).get('token', ''))")

# Get the service ID (use --json, NOT the plain-text middle column which is the deployment ID)
railway service status --all --json
# Save the "id" field for your workflow service

# Set cron schedule via GraphQL (this is reliable — serviceInstanceUpdate works)
python3 << 'PYEOF'
import requests, json

TOKEN = "YOUR_RAILWAY_TOKEN"
SERVICE_ID = "YOUR_SERVICE_ID"
ENV_ID = "951885c9-85a5-46f5-96a1-2151936b0314"  # production environment
CRON = "0 */3 * * *"  # Your desired cron expression

query = '''mutation { serviceInstanceUpdate(serviceId: "%s", environmentId: "%s", input: { cronSchedule: "%s" }) }''' % (SERVICE_ID, ENV_ID, CRON)

resp = requests.post("https://backboard.railway.app/graphql/v2",
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    json={"query": query}, timeout=30)
print(json.dumps(resp.json(), indent=2))
PYEOF
```

### Phase 6: Register in Dashboard Workflow Config

Update `railway_apps/aiaa_dashboard/workflow_config.json` with the new workflow's metadata:

```json
{
  "project_id": "3b96c81f-9518-4131-b2bc-bcd7a524a5ef",
  "cache_ttl_seconds": 300,
  "workflows": {
    "EXISTING_SERVICE_ID": {
      "name": "Existing Workflow",
      "description": "Already registered",
      "enabled": true
    },
    "NEW_SERVICE_ID": {
      "name": "Friendly Workflow Name",
      "description": "What this workflow does",
      "enabled": true
    }
  }
}
```

**How it works:**
- The dashboard dynamically queries Railway API for all services with cron schedules
- Any cron service auto-appears in Active Workflows even WITHOUT a config entry (using the raw Railway service name)
- The config adds friendly names/descriptions — updating it requires a dashboard redeploy
- Cron schedule changes, toggles, and "Run Now" do NOT require redeploy (live API queries)

### Phase 7: Ensure Dashboard Has RAILWAY_API_TOKEN

**CRITICAL: Without this, cron toggle, dynamic workflow loading, and schedule editing won't work.**

```bash
# Preferred method: Railway CLI
TOKEN=$(python3 -c "import json; d=json.load(open('$HOME/.railway/config.json')); print(d.get('user', {}).get('token', ''))")
railway variable set RAILWAY_API_TOKEN="$TOKEN" --service aiaa-dashboard

# Fallback if CLI times out: embed directly in app.py
# RAILWAY_API_TOKEN = os.getenv("RAILWAY_API_TOKEN", "paste_token_here")
```

**Do NOT use** `variableUpsert` GraphQL mutation — it is known to timeout with 504 errors.

### Phase 8: Redeploy Dashboard

```bash
# Must specify --service when multiple services exist in project
cd railway_apps/aiaa_dashboard
railway up --detach --service aiaa-dashboard

# Wait for deployment to complete
railway service status --all
# Wait until aiaa-dashboard shows SUCCESS

# Verify dashboard is up
curl -s "https://aiaa-dashboard-production.up.railway.app/health"
```

### Phase 9: Verify Everything Works

```bash
# 1. Check workflow appears in dashboard Active Workflows page
# Visit: https://aiaa-dashboard-production.up.railway.app/workflows

# 2. Check active workflows via API
curl -s "https://aiaa-dashboard-production.up.railway.app/api/active-workflows" \
  -H "Cookie: session=YOUR_SESSION_COOKIE"

# 3. Check cron status via Railway API
TOKEN=$(python3 -c "import json; d=json.load(open('$HOME/.railway/config.json')); print(d.get('user', {}).get('token', ''))")

python3 -c "
import requests, json
resp = requests.post('https://backboard.railway.app/graphql/v2',
    headers={'Authorization': 'Bearer $TOKEN', 'Content-Type': 'application/json'},
    json={'query': 'query { service(id: \"NEW_SERVICE_ID\") { name serviceInstances { edges { node { cronSchedule } } } } }'},
    timeout=10)
print(json.dumps(resp.json(), indent=2))
"

# 4. Test workflow with "Run Now" button in dashboard UI
# Or trigger via API: deploymentInstanceExecutionCreate mutation
# NOTE: Requires serviceInstanceId (not serviceId) — get from service.serviceInstances.edges[].node.id

# 5. Force refresh workflow cache if needed
# POST /api/active-workflows/refresh (while logged into dashboard)
```

## Critical Gotchas (From Production Debugging)

### Railway CLI
| Issue | Solution |
|-------|----------|
| `railway link <PROJECT_ID>` positional arg fails | Use `railway link -p <PROJECT_ID>` with `-p` flag |
| `railway service status --all` shows wrong IDs | Middle column is DEPLOYMENT ID, use `--json` for actual service IDs |
| `railway up` fails with "multiple services" | Use `--service <name>` flag |
| macOS has no `timeout` command | Use Python `subprocess` with timeout, or background process + sleep |

### Railway GraphQL API
| Issue | Solution |
|-------|----------|
| `cronSchedule: ""` fails | Use `cronSchedule: null` to disable |
| `variableUpsert` times out (504) | Embed credentials in code with `os.getenv("VAR") or "fallback"` |
| `serviceInstanceRedeploy` fails | Use `railway up` CLI instead |
| Service shows "offline" after deployment removal | Must redeploy with `railway up` |
| `ServiceUpdateInput` missing cron | Use `ServiceInstanceUpdateInput` |
| `serviceInstanceUpdate` for cron works reliably | Use this even when other mutations timeout |
| `railway.json` cronSchedule only works on initial deploy | Use `serviceInstanceUpdate` mutation for changes |

### Environment Variables
| Issue | Solution |
|-------|----------|
| Google Doc creation fails silently | Missing `GOOGLE_OAUTH_TOKEN_PICKLE` |
| API calls return 401 | Missing or expired API keys |
| Cron toggle doesn't work | Missing `RAILWAY_API_TOKEN` in dashboard |
| Dynamic workflow loading shows empty list | Missing `RAILWAY_API_TOKEN` in dashboard |

### Dashboard
| Issue | Solution |
|-------|----------|
| Workflow not in dashboard | Check `RAILWAY_API_TOKEN` is set — cron services auto-discover |
| Workflow shows raw service name | Add entry to `workflow_config.json` and redeploy dashboard |
| Dashboard changes not showing | Redeploy dashboard: `railway up --service aiaa-dashboard` |
| Cron not running | Check `cronSchedule` is set via API AND deployment exists |
| Workflow cache stale | POST `/api/active-workflows/refresh` to force refresh |

## IDs Reference (AIAA Project)

```
Project ID:      3b96c81f-9518-4131-b2bc-bcd7a524a5ef
Environment ID:  951885c9-85a5-46f5-96a1-2151936b0314 (production)

Dashboard Service ID:       415686bb-d10c-40c5-b610-4c5e41bbe762
Dashboard Service Instance: d5605b13-d6a7-40b2-9892-fbecc1b5ac8f

Config File: railway_apps/aiaa_dashboard/workflow_config.json
```

## Deployment Checklist

Before marking deployment complete, verify ALL items:

- [ ] Workflow deployed to Railway in SAME project (`railway link -p <PROJECT_ID> && railway up --service <name>`)
- [ ] Deployment status is SUCCESS (`railway service status --all`)
- [ ] ALL required environment variables set (CLI or embedded fallback)
- [ ] `GOOGLE_OAUTH_TOKEN_PICKLE` set (if uses Google APIs)
- [ ] Cron schedule confirmed via `serviceInstanceUpdate` GraphQL mutation
- [ ] Entry added to `railway_apps/aiaa_dashboard/workflow_config.json` with service ID, name, description
- [ ] Dashboard redeployed to pick up config changes (`railway up --service aiaa-dashboard`)
- [ ] `RAILWAY_API_TOKEN` set in dashboard service (for dynamic loading and cron management)
- [ ] Workflow visible in dashboard Active Workflows page
- [ ] Cron toggle works in dashboard UI
- [ ] Manual test run succeeds (via "Run Now" button or `deploymentInstanceExecutionCreate`)
- [ ] Cron schedule verified in Railway

## Self-Annealing Notes

### 2026-01-28: Initial Creation
- **Context**: Created after extensive debugging of cron toggle feature
- **Key Learning**: Railway GraphQL API has many undocumented quirks
- **cronSchedule gotcha**: Empty string `""` causes "Problem processing request" - must use `null`
- **Deployment gotcha**: After removing deployment, `serviceInstanceRedeploy` fails - must use CLI
- **Token gotcha**: Dashboard needs `RAILWAY_API_TOKEN` to make Railway API calls

### 2026-01-28: Run Now Button Implementation
- **Feature**: "Run Now" button triggers immediate cron execution
- **Mutation**: `deploymentInstanceExecutionCreate` with `serviceInstanceId`
- **Key Insight**: `serviceInstanceId` is different from `serviceId` - get it from `service.serviceInstances.edges[].node.id`
- **Behavior**: Runs the cron job immediately without waiting for the next scheduled time

### 2026-01-28: Schedule Editor Implementation
- **Feature**: Granular cron schedule editor replacing simple dropdown
- **UI Components**:
  - Interval input (1-24) for frequency
  - Unit selector ("hours" or "days")
  - Minute input (0-59) for timing
  - Save button to apply changes
  - Live cron expression display
- **Dynamic Schedule Text**: "Schedule:" display now updates dynamically:
  - On page load: parses cron and converts to human-readable text
  - On save: immediately updates to reflect new schedule
- **cronToText Conversion**: JavaScript function converts cron patterns:
  - `0 */3 * * *` → "Every 3 hours"
  - `30 * * * *` → "Every hour at :30"
  - `0 0 * * *` → "Daily at 00:00"

### 2026-01-28: RAILWAY_API_TOKEN Critical Fix
- **Issue**: Schedule updates from dashboard were silently failing
- **Root Cause**: `RAILWAY_API_TOKEN` was not set in dashboard environment
- **Symptom**: UI showed success toast but cron didn't actually change in Railway
- **Fix**: Set token via Railway CLI: `railway variable set RAILWAY_API_TOKEN="$TOKEN" --service aiaa-dashboard`
- **Learning**: Always verify `RAILWAY_API_TOKEN` is set when dashboard API calls fail silently
- **Do NOT use** `variableUpsert` GraphQL mutation — it times out with 504 errors

### 2026-01-29: Dynamic Workflow Loading + Self-Anneal
- **Change**: Replaced hardcoded `active_workflows` list in `app.py` with dynamic Railway API queries
- **Architecture**: Dashboard queries `project.services.edges[].node.serviceInstances.edges[].node.cronSchedule` and filters to cron services
- **Config**: `workflow_config.json` provides friendly names/descriptions, merges with live API data
- **Caching**: In-memory cache with configurable TTL (default 5 min), thread-safe
- **API Endpoints Added**:
  - `GET /api/active-workflows` — returns current workflow list as JSON
  - `POST /api/active-workflows/refresh` — invalidates cache and re-fetches
- **Cache Invalidation**: automatic (TTL), manual (refresh endpoint), on delete (api_workflow_delete)
- **Key Gotchas Added**:
  - `railway link` requires `-p` flag (positional arg fails)
  - `railway service status --all` plain text shows deployment IDs, not service IDs — use `--json`
  - `railway up` with multiple services needs `--service` flag
  - `railway.json` cronSchedule only applies on initial deploy
  - `variableUpsert` mutation unreliable (504 timeouts) — embed credentials in code as fallback
  - macOS lacks `timeout` command
- **Result**: New workflows auto-appear in dashboard without code changes; only friendly metadata requires a redeploy

### 2026-01-29: Railway Domain / Deployment URL Gotcha
- **Issue**: `railway up` creates new deployments with SUCCESS status, but the old production URL (`aiaa-dashboard-production.up.railway.app`) keeps serving old code
- **Root Cause**: Railway assigns per-deployment static URLs (e.g., `aiaa-dashboard-production-10fa.up.railway.app`). The old domain was from a previous deployment and not auto-updated
- **Diagnosis**: Use the GraphQL API to find the current service domain:
  ```graphql
  service(id) { serviceInstances { edges { node { domains { serviceDomains { domain } } } } } }
  ```
- **Fix**: Use `RAILWAY_PUBLIC_DOMAIN` env var or query the API for current domain
- **Key Learning**: Always verify the deployment-specific URL, not a cached/bookmarked production URL
- **`railway run`**: Runs LOCALLY (not in container) — shows local files, not Docker image content
- **`railway variables set`**: Setting any env var triggers automatic redeploy with latest image

### 2026-01-29: Webhook Workflow System (Companion Directive)
- **New Directive**: `deploy_webhook_workflow_to_dashboard.md` — covers webhook-triggered workflows
- **Key Difference**: Webhook workflows are dashboard-hosted (handler in `app.py`), registered via live API (no rebuild). Cron workflows are standalone Railway services requiring `railway up`
- **Webhook UI**: Active Workflows page now shows both cron and webhook workflows side by side
- **Webhook Actions**: Copy URL, Test, Toggle (enable/disable), Delete — all work without rebuild
- **HTTP Forwarding**: `forward_url` field routes webhook payloads to standalone processing services
- **When to use which directive**:
  - Cron-triggered workflow → use THIS directive (`deploy_workflow_to_dashboard.md`)
  - Webhook-triggered workflow → use `deploy_webhook_workflow_to_dashboard.md`

### Railway API Mutations Reference
```graphql
# Modify cron schedule (RELIABLE — use this one)
serviceInstanceUpdate(serviceId, environmentId, input: {cronSchedule})

# Set environment variable (UNRELIABLE — may 504 timeout)
variableUpsert(input: {projectId, serviceId, environmentId, name, value})

# Get service info (includes service instance ID)
service(id) { name projectId serviceInstances { edges { node { id cronSchedule environmentId } } } }

# Get all services in project (for dynamic workflow loading)
project(id) { services { edges { node { id name serviceInstances { edges { node { id cronSchedule } } } } } } }

# Trigger immediate cron execution (bypasses schedule)
# NOTE: Requires serviceInstanceId, not serviceId!
deploymentInstanceExecutionCreate(input: {serviceInstanceId: "INSTANCE_ID"})
```
