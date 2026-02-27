# PRD: Group 10+ Gateway Wiring Batch

## Objective

Complete the missing backend wiring so dashboard chat actually runs through a real gateway profile/stream flow using setup-token profiles, instead of local `AgentRunner`-only behavior.

## Current Gaps (Must Fix)

- `services/chat_runner.py` always returns `AgentRunner`.
- `services/gateway_runner.py` is a stub subclass with no gateway transport logic.
- Gateway service `/v1/responses` rejects `stream=true` and only performs provider passthrough.
- Gateway profile lifecycle endpoints (`/v1/profiles/upsert|validate|revoke`) are not implemented.
- Dashboard token lifecycle still relies on direct local checks and not gateway profile source-of-truth.

## Scope

### In Scope

- Real gateway-backed runner path for chat.
- Gateway profile lifecycle endpoints + secure storage.
- Streaming response flow from gateway to dashboard SSE.
- Token validation/revoke/rotate wired through gateway.
- Tests + health/readiness + redaction hardening.

### Out of Scope

- Multi-tenant authorization model redesign.
- New UI redesign.
- Billing/rate-plan product work.

## Required Result

When `CHAT_BACKEND=gateway`:

1. Save setup-token in dashboard settings.
2. Dashboard upserts token profile in gateway.
3. Chat message routes to gateway `/v1/responses` with stream.
4. Dashboard receives translated tool/text/result events and persists history.
5. Token validate/revoke/rotate all operate against gateway profile APIs.

## Parallel Execution Strategy

Use Ralphy with 6 parallel agents and explicit group ordering.

- Groups `10-14`: implementation core.
- Groups `15-17`: hardening + observability + compatibility.
- Groups `18-19`: integration + release checks.

## Tasks

### Group 10: Backend Selection + Runner Wiring

- [ ] Wire `services/chat_runner.py` to instantiate `GatewayRunner` when backend resolves to `gateway`.
- [ ] Implement concrete `GatewayRunner` transport path using `GatewayClient` (no stub-only inheritance).
- [ ] Add session_id and correlation_id mapping in `GatewayRunner` for stable stream continuity.
- [ ] Update `routes/chat.py` runner init path to respect backend resolver and avoid hard-coded `AgentRunner` behavior.
- [ ] Remove setup-token hard-blocking in chat routes when backend is gateway mode.
- [ ] Add unit tests for backend selection and runner factory behavior in gateway mode.

### Group 11: Gateway Profile API

- [ ] Add internal bearer auth middleware for gateway private endpoints.
- [ ] Implement persistent profile storage model for `profile_id`, encrypted token, status, timestamps.
- [ ] Implement `POST /v1/profiles/upsert` with encrypted token write/update.
- [ ] Implement `POST /v1/profiles/validate` that runs runtime canary against stored profile.
- [ ] Implement `POST /v1/profiles/revoke` with status invalidation and token removal semantics.
- [ ] Add full endpoint tests for upsert/validate/revoke auth + payload validation.

### Group 12: Real Gateway Responses Streaming

- [ ] Implement `POST /v1/responses` support for `stream=true` SSE output.
- [ ] Keep non-stream mode working with normalized response payloads.
- [ ] Add runtime adapter that emits normalized events: `tool_use`, `tool_result`, `text`, `result`, `error`, `done`.
- [ ] Support request fields: `profile_id`, `session_id`, `input`, `cwd`, `tools_profile`.
- [ ] Enforce `/app` workspace defaults and deny unsafe cwd traversal.
- [ ] Add stream contract tests for success, error, and terminal done behavior.

### Group 13: Dashboard Token Lifecycle -> Gateway

- [ ] Update `POST /api/chat/token` to call gateway `profiles/upsert` and store profile status metadata.
- [ ] Update `POST /api/chat/token/validate` to use gateway `profiles/validate` instead of direct provider-only checks.
- [ ] Update token revoke endpoint to call gateway `profiles/revoke` and sync local metadata.
- [ ] Update token rotate flow to perform atomic gateway update with rollback-safe behavior.
- [ ] Ensure token status endpoints report gateway-derived validation states.
- [ ] Add route tests covering save/validate/revoke/rotate with mocked gateway client.

### Group 14: Dashboard Message + Stream Path

- [ ] Route `/api/chat/message` gateway-mode sends through `GatewayRunner`.
- [ ] Translate gateway stream events into existing dashboard SSE event model.
- [ ] Persist translated events/messages via `ChatStore` without breaking existing schema.
- [ ] Add reconnect-safe handling for duplicate/delayed stream chunks.
- [ ] Ensure runner prevents concurrent sends per session in gateway mode.
- [ ] Add integration tests for message -> stream -> done lifecycle via gateway mocks.

### Group 15: Compatibility Endpoint + API Surface

- [ ] Update dashboard `/v1/responses` compatibility route to proxy gateway-mode execution when enabled.
- [ ] Preserve auth behavior (`session` or API key) while delegating runtime to gateway.
- [ ] Ensure setup-token is accepted in gateway mode for `/v1/responses` path.
- [ ] Ensure `stream=true` returns compliant SSE chunks and `[DONE]` terminal.
- [ ] Keep clear error responses for unsupported payloads.
- [ ] Add contract tests for `/v1/responses` in gateway mode.

### Group 16: Security + Redaction Hardening

- [ ] Add gateway-side token redaction utility for logs/exceptions.
- [ ] Prevent token leakage in gateway error payloads and SSE events.
- [ ] Enforce startup validation for required gateway secrets and encryption key.
- [ ] Add cross-service redaction tests for token-like patterns in errors and logs.
- [ ] Add auth-failure throttling behavior for repeated invalid gateway bearer tokens.
- [ ] Add tests for unauthorized and malformed gateway auth requests.

### Group 17: Observability + Readiness

- [ ] Propagate correlation IDs dashboard -> gateway -> logs.
- [ ] Add metrics counters for gateway profile lifecycle outcomes.
- [ ] Add chat latency metrics in gateway path (queue wait, first event, total runtime).
- [ ] Extend gateway `/health` with profile store + runtime readiness details.
- [ ] Extend dashboard readiness to include gateway connectivity state.
- [ ] Add tests for health/readiness payload contracts.

### Group 18: End-to-End Validation

- [ ] Add E2E test: save setup-token -> create session -> send message -> stream complete.
- [ ] Add E2E test: rotate token invalidates old profile behavior.
- [ ] Add E2E test: revoke token blocks new runs with clear user-facing error.
- [ ] Add smoke test covering tool event visibility in chat stream.

### Group 19: Rollout Checklist

- [ ] Add Railway runbook for gateway deploy, env wiring, and rollback toggle.
- [ ] Add staged canary checklist and failure triage steps.
- [ ] Add post-deploy verification checklist for token leakage and readiness metrics.

## Acceptance Criteria

- [ ] Gateway backend is actually used for chat when configured.
- [ ] Profile lifecycle endpoints are functional and secured.
- [ ] Streamed responses work in real time with tool/result events.
- [ ] Dashboard token actions are gateway-backed and consistent.
- [ ] No raw token exposure in API responses/logs/SSE.
- [ ] Integration tests pass for gateway-mode chat lifecycle.

## Suggested Run Command

```bash
ralphy --codex --parallel --max-parallel 6 --max-iterations 10 --prd "/Users/lucasnolan/Agentic OS/PRD.group10plus.md"
```
