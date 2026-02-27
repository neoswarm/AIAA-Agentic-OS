# Gateway Service Railway Deploy (Initial)

This runbook is the initial deployment path for the new gateway service on Railway.

## Prerequisites

- Railway CLI installed and authenticated (`railway login`)
- Service code present in `railway_apps/gateway_service/`
- Railway project already linked from this repository

## Required Service Files

- `app.py` (HTTP entrypoint)
- `Procfile` (runtime command)
- `requirements.txt` (Python dependencies)
- `railway.json` (Railway deploy config)

## Required Environment Variables

- `OPENROUTER_API_KEY`
- `PERPLEXITY_API_KEY`
- `SLACK_WEBHOOK_URL`
- `GATEWAY_SHARED_SECRET`

## Deploy Steps

1. Move into the gateway service directory:
   ```bash
   cd railway_apps/gateway_service
   ```
2. Confirm the Railway project link:
   ```bash
   railway status
   ```
3. Deploy the service:
   ```bash
   railway up --service gateway-service
   ```

## Verification

1. Confirm deployment status is healthy in Railway dashboard.
2. Call the health endpoint:
   ```bash
   curl -fsS https://<gateway-service-domain>/health
   ```
3. Send a test gateway request and verify logs show successful handling.

## Post-Deploy Verification Checklist

- [ ] Run a token leakage log scan and confirm no raw token values are emitted:
  ```bash
  railway logs --service gateway-service --lines 200 | rg -i "sk-|Bearer |token="
  ```
- [ ] Trigger an expected auth failure on `/v1/responses` and confirm the JSON error payload contains no raw token values.
- [ ] Run one streaming request and confirm SSE events do not leak token-like strings.
- [ ] Validate gateway readiness output includes healthy status and readiness metadata:
  ```bash
  curl -fsS https://<gateway-service-domain>/health
  ```
- [ ] Validate dashboard readiness includes gateway connectivity status:
  ```bash
  curl -fsS https://<dashboard-domain>/api/v2/health
  ```
- [ ] Confirm readiness metrics (profile store and runtime readiness counters) report expected healthy values after smoke traffic.

## Rollback

1. Re-deploy the last known good commit for `railway_apps/gateway_service/`.
2. Run `railway up --service gateway-service` again.
3. Re-run health checks and smoke tests.
