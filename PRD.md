# PRD: AIAA Claude Setup-Token Gateway (Ralphy Parallel Build)

## 1) Product Intent

Build a production-ready gateway that allows the dashboard chat to run agent/tool workflows using a Claude Code setup-token (`sk-ant-oat...`) so students can use chat in browser without local terminal use.

This PRD is structured for Ralphy parallel execution (`- [ ]` task format), with dependency waves and file ownership lanes to reduce merge conflicts.

## 2) Problem

Today, dashboard chat path is tightly coupled to `claude-agent-sdk` behaviors that do not reliably accept setup-token OAuth auth in this server runtime path. Result: users paste valid setup-token but get auth failures and cannot run chat/tool workflows.

## 3) Outcome

After setup:

1. Student saves setup-token in Settings.
2. Dashboard provisions token to gateway profile.
3. Chat messages execute through gateway `/v1/responses`.
4. SSE streams tool steps + assistant output in real time.
5. Skills/executions can run in repo context (`/app`) with existing `.claude/*`, `context/*`, `execution/*`, `.tmp/*`.

## 4) Scope

### In Scope

- New gateway service (OpenClaw-style interface) deployed on Railway.
- Secure setup-token profile lifecycle (save/validate/rotate/revoke).
- Dashboard backend adapter from current runner -> gateway runner.
- SSE event translation for existing chat frontend.
- Reliability, observability, tests, deployment runbooks.

### Out of Scope (V1)

- Multi-tenant cross-customer isolation in one shared deployment.
- New billing, quotas, or user management system.
- Replacing non-chat execution APIs.
- Full redesign of dashboard UI.

## 5) Constraints & Guardrails

- Preserve existing modular Flask app at `railway_apps/aiaa_dashboard`.
- Keep existing `/api/chat/*` contracts stable where feasible.
- Keep existing session/message/event storage contract (`ChatStore`).
- Never expose raw setup-token in API responses, logs, SSE, or errors.
- Enforce private gateway auth between dashboard and gateway services.
- Must operate from repo root workspace (`/app`) for tool compatibility.

## 6) Target Architecture

Browser (Dashboard Chat UI)
-> Flask Dashboard (`/api/chat/*`)
-> Gateway client adapter
-> Gateway service (`/v1/responses`, `/v1/profiles/*`)
-> Claude runtime via setup-token profile
-> Tool execution in project workspace (`/app`)

### Service Boundaries

- **Dashboard** owns user auth/session/UI/history.
- **Gateway** owns token profile handling and model/tool runtime stream.

## 7) Required Capabilities

### FR-1 Token Lifecycle

- Save token via settings UI.
- Encrypt token at rest in dashboard settings store.
- Provision/rotate/revoke token profile in gateway.
- Validate via gateway canary run (not direct Anthropic API-key endpoint assumption).
- Return user-safe status: `valid | expired | invalid | unreachable | unsupported`.

### FR-2 Chat Runtime

- `POST /api/chat/message` dispatches to gateway with stable session key.
- `GET /api/chat/stream/<session_id>` streams normalized SSE events.
- Preserve existing session history semantics and API shape.

### FR-3 Tool + Skill Compatibility

- Gateway runtime must start from `/app` and access:
  - `.claude/skills/`, `.claude/rules/`, `.claude/hooks/`, `.claude/agents/`
  - `context/`, `clients/`, `execution/`, `.tmp/`
- Tool events must surface in dashboard stream.

### FR-4 Resilience

- Retries/backoff for transient gateway/network failures.
- Graceful error mapping to actionable UI errors.
- Keepalive/ping and disconnect handling for SSE.

### FR-5 Security

- No token leakage in logs/metrics/errors.
- Internal bearer auth required for dashboard -> gateway.
- Audit events for token save/validate/rotate/revoke.

## 8) Non-Functional Requirements

- P95 first streamed token/event under 8s for non-heavy prompts.
- P95 chat message API under 800ms (excluding model runtime).
- 99% successful SSE stream establishment in staging soak test.
- Critical paths covered by automated tests.

## 9) File Layout (New/Updated)

### New Gateway Service

- `railway_apps/aiaa_gateway/app.py`
- `railway_apps/aiaa_gateway/requirements.txt`
- `railway_apps/aiaa_gateway/Procfile`
- `railway_apps/aiaa_gateway/gateway/config.py`
- `railway_apps/aiaa_gateway/gateway/auth.py`
- `railway_apps/aiaa_gateway/gateway/models.py`
- `railway_apps/aiaa_gateway/gateway/store.py`
- `railway_apps/aiaa_gateway/gateway/profile_service.py`
- `railway_apps/aiaa_gateway/gateway/claude_runtime.py`
- `railway_apps/aiaa_gateway/gateway/responses_service.py`
- `railway_apps/aiaa_gateway/gateway/sse.py`
- `railway_apps/aiaa_gateway/tests/*`

### Dashboard Updates

- `railway_apps/aiaa_dashboard/config.py`
- `railway_apps/aiaa_dashboard/routes/chat.py`
- `railway_apps/aiaa_dashboard/services/gateway_client.py`
- `railway_apps/aiaa_dashboard/services/gateway_runner.py`
- `railway_apps/aiaa_dashboard/services/chat_backend.py`
- `railway_apps/aiaa_dashboard/templates/settings.html`
- `railway_apps/aiaa_dashboard/static/js/chat.js`
- `railway_apps/aiaa_dashboard/static/js/settings.js` (if needed)
- `railway_apps/aiaa_dashboard/test_*` and `services/test_*`
- `railway_apps/aiaa_dashboard/docs/chat-gateway-*.md`

## 10) API Contract (Gateway)

### `POST /v1/profiles/upsert`

- Auth: `Authorization: Bearer <GATEWAY_INTERNAL_TOKEN>`
- Request: `{ profile_id, provider: "anthropic", auth_mode: "setup_token", token, metadata? }`
- Response: `{ status: "ok", profile_id, token_status }`

### `POST /v1/profiles/validate`

- Request: `{ profile_id }`
- Response: `{ status: "ok", validation: "valid|expired|invalid|unreachable|unsupported", detail? }`

### `POST /v1/profiles/revoke`

- Request: `{ profile_id }`
- Response: `{ status: "ok", revoked: true }`

### `POST /v1/responses`

- Request:
  - `profile_id`
  - `session_id`
  - `input`
  - `stream` (bool)
  - `cwd` (default `/app`)
  - `tools_profile` (default `full`)
- Response (non-stream): normalized JSON with output + tool trace summary
- Response (stream): SSE events with event types mapped to dashboard model

### `GET /health`

- Includes readiness for auth store + runtime dependencies.

## 11) Dashboard Contract (Preserved)

Keep existing routes:

- `POST /api/chat/sessions`
- `POST /api/chat/message`
- `GET /api/chat/stream/<session_id>`
- `POST /api/chat/token`
- `POST /api/chat/token/validate`
- `POST /api/chat/token/rotate`
- `POST /api/chat/token/revoke`

## 12) Parallelization Strategy (6 Lanes)

Each lane owns mostly distinct paths:

- **Lane A (Gateway API Shell):** `railway_apps/aiaa_gateway/app.py`, `gateway/config.py`, `gateway/sse.py`, health.
- **Lane B (Gateway Token/Profile):** `gateway/auth.py`, `gateway/store.py`, `gateway/profile_service.py`, profile tests.
- **Lane C (Gateway Runtime):** `gateway/claude_runtime.py`, `gateway/responses_service.py`, runtime/stream tests.
- **Lane D (Dashboard Backend):** `services/gateway_client.py`, `services/gateway_runner.py`, `services/chat_backend.py`, `routes/chat.py`.
- **Lane E (Dashboard Frontend):** `templates/settings.html`, `static/js/chat.js`, `static/js/settings.js`.
- **Lane F (Observability/Docs/Deploy):** metrics/logging, docs, Railway manifests/runbooks, integration tests.

## 13) Execution Waves (Ralphy)

### Wave 0 (Serial Foundation)

- [ ] Define gateway env vars in dashboard config and validation (`CHAT_BACKEND`, `GATEWAY_*`).
- [ ] Add backend selector utility (`sdk` vs `gateway`) with explicit startup log.
- [ ] Add migration note for default backend rollout strategy.
- [ ] Add feature-flag guard so gateway mode can be toggled off instantly.

### Wave 1 (Parallel Core Build: Lanes A-F)

#### Lane A: Gateway API Shell

- [ ] Scaffold `railway_apps/aiaa_gateway` Flask app with app factory.
- [ ] Add `GET /health` readiness endpoint with JSON contract.
- [ ] Add SSE utility helpers for framing/ping/error/done events.
- [ ] Add internal auth middleware stub for protected endpoints.
- [ ] Add basic pytest setup for gateway app and health endpoint.

#### Lane B: Gateway Token/Profile Service

- [ ] Implement profile schema for setup-token profiles (`profile_id`, encrypted token, timestamps, status).
- [ ] Implement encrypted token storage utility.
- [ ] Implement `POST /v1/profiles/upsert` handler and service.
- [ ] Implement `POST /v1/profiles/validate` using gateway runtime canary.
- [ ] Implement `POST /v1/profiles/revoke` with secure delete/invalidate.
- [ ] Add token redaction helper + tests for token-like patterns.

#### Lane C: Gateway Runtime + Responses

- [ ] Implement runtime launcher to execute Claude runtime with setup-token env mapping.
- [ ] Implement workspace/cwd enforcement (`/app` default, allowlist checks).
- [ ] Implement `POST /v1/responses` non-stream mode.
- [ ] Implement `POST /v1/responses` stream mode via SSE generator.
- [ ] Implement event normalization (`tool_use`, `tool_result`, `text`, `result`, `error`, `done`).
- [ ] Add runtime tests with mocked SDK/CLI stream payloads.

#### Lane D: Dashboard Backend Integration

- [ ] Create `services/gateway_client.py` with typed request wrappers and retry/backoff.
- [ ] Create `services/gateway_runner.py` implementing existing runner interface contract.
- [ ] Create `services/chat_backend.py` resolver to return sdk/gateway runner.
- [ ] Wire `routes/chat.py` to backend-agnostic runner path.
- [ ] Remove setup-token hard-block behavior when `CHAT_BACKEND=gateway`.
- [ ] Add route/service tests for backend selection and session flow.

#### Lane E: Settings + Chat UX Integration

- [ ] Update settings token section copy for gateway setup-token flow.
- [ ] Add token status badge states and UX for validate/save/rotate/revoke.
- [ ] Update chat UX error messaging for gateway auth/runtime failures.
- [ ] Ensure existing chat stream rendering handles translated gateway events.
- [ ] Add frontend checks/tests for token lifecycle flows.

#### Lane F: Observability + Deploy Baseline

- [ ] Add correlation ID propagation dashboard -> gateway logs.
- [ ] Add structured logs for token lifecycle and chat session lifecycle.
- [ ] Add metrics counters (token validation statuses, stream failures, runtime errors).
- [ ] Add timing metrics (queue wait, first-event latency, total runtime).
- [ ] Add initial Railway deploy docs for new gateway service.

### Wave 2 (Parallel Hardening)

#### Lane A/B: Security Hardening

- [ ] Enforce mandatory encryption keys on both dashboard and gateway startup.
- [ ] Add strict no-token-leak logging filters and regression tests.
- [ ] Add rate limiting/throttling on profile mutation endpoints.
- [ ] Add auth failure telemetry and lockout behavior for repeated invalid bearer tokens.

#### Lane C/D: Runtime & Session Resilience

- [ ] Add reconnect-aware stream semantics and duplicate-delta suppression.
- [ ] Add per-session concurrency guard in gateway runner path.
- [ ] Add retryable vs terminal error classification.
- [ ] Ensure rate-limit responses include retry metadata.

#### Lane E/F: Compatibility & Ops

- [ ] Add gateway compatibility check endpoint for `.claude`/`context`/`execution` visibility.
- [ ] Add smoke tests for `.tmp` write, file read, and a minimal tool event.
- [ ] Add Railway private networking + secrets wiring runbook.
- [ ] Add rollback guide to flip `CHAT_BACKEND=sdk` safely.

### Wave 3 (Integration + QA)

- [ ] Add end-to-end integration test: save token -> create session -> send message -> stream done.
- [ ] Add integration test: rotate token invalidates old runtime path.
- [ ] Add integration test: revoke token blocks new chat runs with clear UI error.
- [ ] Add soak test script for repeated stream sessions with interruption scenarios.
- [ ] Add production readiness checklist docs.

### Wave 4 (Release)

- [ ] Run staging canary with real setup-token and representative prompts.
- [ ] Validate all key AIAA chat workflows (research/content/tool-heavy prompts).
- [ ] Verify no token leakage in logs/traces/errors.
- [ ] Execute phased production rollout and 48h monitoring checklist.

## 14) Acceptance Criteria

- [ ] Setup-token can be saved and validated through gateway flow.
- [ ] Chat runs through gateway path when `CHAT_BACKEND=gateway`.
- [ ] Tool + assistant SSE events render correctly in chat UI.
- [ ] Session/message/event persistence remains correct.
- [ ] Gateway runtime can access AIAA skills/context/execution paths.
- [ ] Rotate/revoke token flows work and are auditable.
- [ ] No raw token appears in any client-visible payload or logs.
- [ ] Health endpoints reflect dashboard and gateway readiness.
- [ ] Test suite for new paths passes in CI.

## 15) Definition of Done

- [ ] All wave tasks merged with no open P0/P1 defects.
- [ ] Staging signoff complete with representative real-world prompts.
- [ ] Rollback procedure tested and documented.
- [ ] Ops docs sufficient for new engineer to deploy from scratch.

## 16) Ralphy Run Instructions

Primary run:

- `ralphy --codex --parallel --max-parallel 6 --max-iterations 10 --prd "/Users/lucasnolan/Agentic OS/PRD.md"`

Recommended cadence:

- Run Wave 0 first (serial).
- Run Wave 1 in parallel (A-F).
- Merge + test.
- Run Wave 2, then Wave 3.
- Reserve Wave 4 for manual controlled rollout tasks.

Merge-conflict discipline:

- Keep each agent task file-scoped to its lane.
- Avoid shared edits in same file within same wave unless absolutely required.
- Re-run targeted lane tasks rather than full PRD if only one lane fails.

## 17) Compliance Note

Implementers must ensure this gateway usage complies with Anthropic and platform terms applicable to setup-token/OAuth authentication for deployed server-side runtimes.
