# Gateway Service Railway Deploy (Initial)

This runbook is the initial deployment path for the new gateway service on Railway.

## Prerequisites

- Railway CLI installed and authenticated (`railway login`)
- Service code present in `railway_apps/gateway_service/`
- Railway project already linked from this repository
- Dashboard service already deployed on Railway

## Required Service Files

- `app.py` (HTTP entrypoint)
- `Procfile` (runtime command)
- `requirements.txt` (Python dependencies)
- `railway.json` (Railway deploy config)

## Required Environment Variables

### Gateway Service (`gateway-service`)

- `ANTHROPIC_API_KEY` (required unless every request sends `Authorization: Bearer ...`)
- `ANTHROPIC_BASE_URL` (optional, defaults to `https://api.anthropic.com`)
- `ANTHROPIC_API_VERSION` (optional, defaults to `2023-06-01`)
- `DEFAULT_ANTHROPIC_MODEL` (optional, defaults to `claude-3-5-sonnet-latest`)
- `DEFAULT_MAX_OUTPUT_TOKENS` (optional, defaults to `1024`)
- `UPSTREAM_REQUEST_TIMEOUT_SECONDS` (optional, defaults to `30`)

### Dashboard Service Wiring

- `CHAT_BACKEND=gateway`
- `GATEWAY_BASE_URL=https://<gateway-service-domain>`
- `GATEWAY_API_KEY=<gateway-bearer-token>`
- `CHAT_GATEWAY_MODE_ENABLED=true` (feature-flag rollout toggle)

## Deploy Steps

1. Move into the gateway service directory:
   ```bash
   cd railway_apps/gateway_service
   ```
2. Confirm the Railway project link:
   ```bash
   railway status
   ```
3. Set gateway service environment variables:
   ```bash
   railway variables --service gateway-service --set "ANTHROPIC_API_KEY=<anthropic-api-key>"
   ```
4. Deploy the service:
   ```bash
   railway up --service gateway-service
   ```
5. Wire dashboard environment variables to route chat traffic through the gateway:
   ```bash
   railway variables --service <dashboard-service> --set "CHAT_BACKEND=gateway"
   railway variables --service <dashboard-service> --set "GATEWAY_BASE_URL=https://<gateway-service-domain>"
   railway variables --service <dashboard-service> --set "GATEWAY_API_KEY=<gateway-bearer-token>"
   railway variables --service <dashboard-service> --set "CHAT_GATEWAY_MODE_ENABLED=true"
   ```

## Verification

1. Confirm deployment status is healthy in Railway dashboard.
2. Call the health endpoint:
   ```bash
   curl -fsS https://<gateway-service-domain>/health
   ```
3. Send a test gateway request and verify logs show successful handling.
4. Verify dashboard health reports gateway readiness with no missing vars:
   - `backend: gateway`
   - `missing_env_vars: []`

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

1. Toggle gateway mode off immediately in dashboard (fast rollback path):
   ```bash
   railway variables --service <dashboard-service> --set "CHAT_GATEWAY_MODE_ENABLED=false"
   ```
2. Revert dashboard backend routing to provider mode:
   ```bash
   railway variables --service <dashboard-service> --set "CHAT_BACKEND=provider"
   ```
3. Optional cleanup: unset dashboard gateway wiring after rollback is stable:
   ```bash
   railway variables --service <dashboard-service> --set "GATEWAY_BASE_URL="
   railway variables --service <dashboard-service> --set "GATEWAY_API_KEY="
   ```
4. If needed, redeploy the last known good commit for `railway_apps/gateway_service/` and run:
   ```bash
   railway up --service gateway-service
   ```
