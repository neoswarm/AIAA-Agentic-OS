# Deploy Webhook Workflow to Dashboard

## What This Workflow Is

Register a webhook-triggered workflow on the AIAA Railway dashboard. **No rebuild required** — webhooks are registered via a live API call and are active immediately.

Webhook workflows are dashboard-hosted — their handler routes live inside `app.py`, and they are registered via the `/api/webhook-workflows/register` endpoint.

## Trigger Phrases

- "deploy a webhook workflow"
- "add a webhook to the dashboard"
- "register a webhook endpoint"
- "deploy [service_name] webhook"

## Prerequisites

Before starting, ensure:
- [ ] Dashboard is deployed and healthy (`curl <DASHBOARD_URL>/health`)
- [ ] Dashboard login credentials available (username + password)
- [ ] `SLACK_WEBHOOK_URL` set in dashboard (if Slack notifications needed)
- [ ] External service ready to send webhooks (Calendly, Stripe, Typeform, etc.)

## Quick Path (No Rebuild)

### Option A: Via Execution Script

```bash
# Simple webhook (default handler: log + Slack)
python3 execution/deploy_webhook_workflow.py \
  --slug ai-news \
  --name "AI News Digest" \
  --description "Searches for latest AI news and sends to Slack" \
  --source "Manual/Automation" \
  --slack-notify

# Webhook with custom processing (forwards to standalone service)
python3 execution/deploy_webhook_workflow.py \
  --slug ai-news \
  --name "AI News Digest" \
  --description "Fetches AI news via Perplexity, sends to Slack" \
  --source "Automation" \
  --forward-url "https://ai-news-processor.up.railway.app/process" \
  --slack-notify
```

The script authenticates with the dashboard, POSTs to `/api/webhook-workflows/register`, and the webhook is live immediately. If `--forward-url` is set, incoming payloads are forwarded to that URL for custom processing.

### Option B: Via curl

```bash
# 1. Login to get session cookie
SESSION=$(curl -s -c - -X POST "https://aiaa-dashboard-production-10fa.up.railway.app/login" \
  -d "username=admin&password=YOUR_PASSWORD" \
  -H "Content-Type: application/x-www-form-urlencoded" | grep session | awk '{print $NF}')

# 2. Register webhook (instantly active, no rebuild)
curl -X POST "https://aiaa-dashboard-production-10fa.up.railway.app/api/webhook-workflows/register" \
  -H "Content-Type: application/json" \
  -H "Cookie: session=$SESSION" \
  -d '{
    "slug": "ai-news",
    "name": "AI News Digest",
    "description": "Searches for latest AI news and sends to Slack",
    "source": "Manual/Automation",
    "slack_notify": true
  }'

# 3. Test it
curl -X POST "https://aiaa-dashboard-production-10fa.up.railway.app/webhook/ai-news" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

### Option C: Via Dashboard UI

1. Navigate to the Active Workflows page
2. Webhook workflows appear in the "Webhook Workflows" section
3. Use Copy URL, Test, Toggle, and Delete buttons directly

## API Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/webhook-workflows` | GET | Yes | List all registered webhooks |
| `/api/webhook-workflows/register` | POST | Yes | Register new webhook (no rebuild) |
| `/api/webhook-workflows/unregister` | POST | Yes | Remove a webhook (no rebuild) |
| `/api/webhook-workflows/toggle` | POST | Yes | Enable/disable a webhook |
| `/api/webhook-workflows/test` | POST | Yes | Send test payload to a webhook |
| `/webhook/<slug>` | POST | No | The actual webhook endpoint (public) |

### Register Payload

```json
{
  "slug": "stripe-payments",
  "name": "Stripe Payment Webhooks",
  "description": "Processes Stripe payment events and notifies Slack",
  "source": "Stripe",
  "slack_notify": true,
  "enabled": true,
  "forward_url": "https://my-processor.up.railway.app/process"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `slug` | Yes | URL slug — maps to `/webhook/<slug>`. Lowercase, hyphens only. |
| `name` | Yes | Display name in dashboard UI |
| `description` | No | What happens when webhook fires |
| `source` | No | External service name (badge in UI). Default: "Unknown" |
| `slack_notify` | No | Send Slack notification on receive. Default: false |
| `enabled` | No | Active on registration. Default: true |
| `forward_url` | No | URL to forward payloads to for custom processing. If set, dashboard acts as router. |

## Architecture: How It Works

```
Registration (no rebuild):
  POST /api/webhook-workflows/register
    → Updates in-memory _webhook_registry (instant)
    → Persists to WEBHOOK_CONFIG env var via Railway API (background, best-effort)
    → Writes webhook_config.json to disk (backup)

On startup, dashboard loads config from:
  1. WEBHOOK_CONFIG env var (primary — survives restarts)
  2. webhook_config.json file (seed fallback — first deploy only)

Incoming webhook (no forward_url):
  POST /webhook/<slug>
    → Checks in-memory registry
    → Returns 404 if not registered, 503 if disabled
    → Sends Slack notification (if slack_notify: true)
    → Returns 200 with JSON response

Incoming webhook (with forward_url):
  POST /webhook/<slug>
    → Checks in-memory registry
    → Returns 404 if not registered, 503 if disabled
    → Forwards payload to forward_url as POST:
        {webhook_slug, webhook_name, source, payload, timestamp}
    → Returns processing service response to caller
    → Sends Slack notification on forward result (if slack_notify: true)
    → Returns 502 if forward fails
```

## Adding Custom Processing Logic

There are two approaches for custom processing. **Prefer forwarding** (no rebuild needed).

### Option 1: HTTP Forwarding (No Rebuild)

Deploy your processing logic as a standalone Railway service, then register the webhook with `forward_url` pointing to it:

```bash
# Register webhook that forwards to your processing service
python3 execution/deploy_webhook_workflow.py \
  --slug ai-news \
  --name "AI News Digest" \
  --description "Fetches AI news via Perplexity, sends to Slack" \
  --source "Automation" \
  --forward-url "https://ai-news-processor.up.railway.app/process" \
  --slack-notify
```

The dashboard receives the webhook and forwards the full payload to your service:

```json
{
  "webhook_slug": "ai-news",
  "webhook_name": "AI News Digest",
  "source": "Automation",
  "payload": { ... original webhook payload ... },
  "timestamp": "2026-01-29T12:00:00"
}
```

Your processing service just needs a single POST endpoint that returns JSON.

### Option 2: Inline Handler (Requires Rebuild)

For simple cases, add slug-specific handling directly in `webhook_handler()` in `app.py`:

```python
# In webhook_handler(), before the generic response:
if slug == "ai-news":
    result = handle_ai_news_webhook(payload)
```

**This requires a dashboard rebuild.** Use forwarding instead when possible.

## Critical Gotchas

### Registration
| Issue | Solution |
|-------|----------|
| Need to rebuild for new webhook | NO — use `/api/webhook-workflows/register` API |
| Webhook lost after restart | Persisted to WEBHOOK_CONFIG env var automatically |
| `variableUpsert` times out | Best-effort — file backup on disk + in-memory still works |
| Custom processing needed | Use `forward_url` to route to standalone service (no rebuild) |

### Webhook Handler
| Issue | Solution |
|-------|----------|
| Webhook returns 404 | Not registered — call `/api/webhook-workflows/register` |
| Webhook returns 503 | Disabled — toggle via dashboard UI or API |
| Webhook returns 502 | Forward failed — check processing service is healthy |
| Slack notification not sent | Check `SLACK_WEBHOOK_URL` set + `slack_notify: true` |
| Empty payload | External service must send `Content-Type: application/json` |

### Forwarding
| Issue | Solution |
|-------|----------|
| Processing service unreachable | Dashboard returns 502 — check service URL and deployment |
| Forward timeout | Dashboard uses 30s timeout — increase if processing is slow |
| Want to change forward_url | Re-register with same slug + new `forward_url` (updates in place) |
| Remove forwarding | Re-register with same slug, omit `forward_url` (reverts to default handler) |

### External Service
| Issue | Solution |
|-------|----------|
| Can't reach webhook | Verify dashboard URL is correct and deployment is healthy |
| Duplicate deliveries | Implement idempotency in processing service if needed |

## IDs Reference (AIAA Project)

```
Dashboard URL:   https://aiaa-dashboard-production-10fa.up.railway.app
Project ID:      3b96c81f-9518-4131-b2bc-bcd7a524a5ef
Environment ID:  951885c9-85a5-46f5-96a1-2151936b0314 (production)
Service ID:      415686bb-d10c-40c5-b610-4c5e41bbe762
```

## Deployment Checklist

- [ ] Webhook registered via API (or execution script)
- [ ] Webhook visible in dashboard Active Workflows page
- [ ] Test button works from dashboard UI
- [ ] curl test returns 200 with JSON response
- [ ] Slack notification received (if `slack_notify: true`)
- [ ] External service configured to POST to webhook URL
- [ ] If using forwarding: processing service deployed and healthy
- [ ] If using forwarding: `forward_url` set and "Forwarding" badge visible in dashboard

## Self-Annealing Notes

### 2026-01-29: Initial Creation
- Dashboard-hosted webhooks, registered via `webhook_config.json` file
- Required full dashboard rebuild to register new webhooks

### 2026-01-29: No-Rebuild Architecture
- **Breaking Change**: Replaced file-only config with in-memory registry + API registration
- **New Flow**: POST to `/api/webhook-workflows/register` → webhook is live instantly
- **Persistence**: In-memory → env var (WEBHOOK_CONFIG) via Railway API → file backup
- **Startup Priority**: env var > file seed
- **Execution Script**: Now calls live API instead of editing files + `railway up`
- **Key Insight**: `variableUpsert` is flaky but best-effort is fine — in-memory is the source of truth, env var is durability layer

### 2026-01-29: HTTP Forwarding for Custom Processing
- **New Feature**: `forward_url` field in webhook config enables payload forwarding to standalone services
- **No Rebuild**: Register webhook with `forward_url` via API — dashboard routes payloads automatically
- **Architecture**: Dashboard acts as router; processing services are standalone Railway deployments
- **Forwarded Payload**: `{webhook_slug, webhook_name, source, payload, timestamp}`
- **Error Handling**: Returns 502 on forward failure, Slack notification on forward result if configured
- **UI**: "Forwarding" badge + "Forwards to:" URL displayed on webhook cards
- **Execution Script**: Added `--forward-url` flag
- **Zero rebuild needed**: Neither webhook registration NOR custom processing requires a dashboard rebuild

### 2026-01-29: Delete Button + UI Actions
- **New Feature**: Delete button on webhook workflow cards in Active Workflows page
- **Function**: `deleteWebhookWorkflow(slug, name)` — confirmation dialog → POST to `/api/webhook-workflows/unregister` → page reload
- **Page Reload**: Delete success handler uses `window.location.reload()` (not card animation removal) so the server-rendered Available Endpoints list also updates
- **Full UI Actions**: Webhook cards now have Copy URL, Test, Toggle (enable/disable), and Delete buttons
- **All actions work without rebuild**: Toggle, Test, Delete all use live API calls; no `railway up` needed
