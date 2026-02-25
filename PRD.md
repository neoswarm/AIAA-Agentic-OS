# AIAA Dashboard Chat Hardening & Scale PRD

This PRD is formatted for `ralphy` markdown mode (`- [ ]` tasks).

## Outcome

Ship a production-ready dashboard chat system that:
- supports multi-instance Railway deployments,
- secures Claude setup token handling end-to-end,
- provides resilient streaming/resume behavior,
- and adds test + rollout guardrails.

## Constraints

- Keep existing Flask modular architecture.
- Preserve current chat routes and backward compatibility where possible.
- Avoid regressions in existing dashboard pages and APIs.
- Keep the default entrypoint as `PRD.md` for direct `ralphy` usage.

## Tasks

### 1) Redis Session/Event Store (Multi-Instance Safe)

- [x] Add Redis dependency and config flags for chat storage backend.
- [x] Add `REDIS_URL` and chat TTL env vars to dashboard config.
- [x] Create `services/chat_store.py` interface for sessions/messages/events.
- [x] Implement `InMemoryChatStore` as a fallback backend.
- [x] Implement `RedisChatStore` with atomic session/message writes.
- [x] Add session schema with fields: id, title, status, sdk_session_id, created_at, updated_at.
- [x] Add message schema with fields: role, content, timestamp, type, metadata.
- [x] Add event schema for streamed tool/system/result events.
- [x] Add Redis key naming convention with clear namespace prefix.
- [x] Add TTL policy for idle sessions and stale event streams.
- [ ] Wire chat routes to use store abstraction instead of in-memory runner state.
- [ ] Verify cross-process session visibility with two app instances locally.

### 2) Claude Token Security & Lifecycle

- [ ] Add encrypted-at-rest storage for `claude_setup_token` in settings table.
- [ ] Add encryption key config (`CHAT_TOKEN_ENCRYPTION_KEY`) with validation.
- [ ] Add token decrypt utility with safe failure handling.
- [ ] Ensure APIs never return raw token values (only redacted form).
- [ ] Add token metadata fields: `last_validated_at`, `validation_status`, `last_error`.
- [ ] Add token rotation endpoint to replace token atomically.
- [ ] Add token clear/revoke endpoint to remove token and invalidate runner usage.
- [ ] Add settings UI controls for rotate and revoke token actions.
- [ ] Add confirmation modal before token revoke.
- [ ] Persist rotated token to Railway variables in background with retry.
- [ ] Add audit event logging for save/rotate/revoke token actions.

### 3) Rate Limits & Concurrency Guardrails

- [ ] Add per-user message rate limiting for `/api/chat/message`.
- [ ] Add per-session max pending/running run guard.
- [ ] Add global max concurrent chat runs per instance.
- [ ] Add clear API errors for limit violations with retry guidance.
- [ ] Add configurable limits in `config.py` with sensible defaults.
- [ ] Add unit tests for each guardrail path.

### 4) Persistent Chat History APIs

- [ ] Add paginated session history endpoint (messages + metadata).
- [ ] Add session listing filters (status/date/search).
- [ ] Add session soft-delete endpoint.
- [ ] Add optional transcript export endpoint (markdown/json).
- [ ] Ensure history load is efficient for long conversations.
- [ ] Add DB/Redis integration tests for history consistency.

### 5) Streaming Resilience & Reconnect

- [ ] Add server event IDs for SSE messages.
- [ ] Support resume from last event ID on reconnect.
- [ ] Add keepalive strategy and idle timeout behavior docs in code.
- [ ] Add frontend auto-reconnect with backoff for transient disconnects.
- [ ] Add frontend handling for duplicate event IDs on reconnect.
- [ ] Add “runner still active” recovery flow when page reloads mid-run.
- [ ] Add integration test for interrupted stream + resume.

### 6) Agent Permission Profiles

- [ ] Add named tool profiles: `safe`, `default`, `full`.
- [ ] Map each profile to explicit `allowed_tools` sets.
- [ ] Add settings UI selector for default chat profile.
- [ ] Add per-session override capability on new session creation.
- [ ] Add API validation to reject unknown profiles.
- [ ] Add telemetry field for profile used per run.
- [ ] Add tests for profile resolution and fallback behavior.

### 7) Observability & Diagnostics

- [ ] Add structured logs for session lifecycle events.
- [ ] Add structured logs for tool events and terminal statuses.
- [ ] Add request correlation IDs for chat APIs and streams.
- [ ] Add latency metrics (queue wait, first-token, total runtime).
- [ ] Add token validation metric counters by status (valid/expired/invalid/unreachable).
- [ ] Add health endpoint extension for chat subsystem readiness.
- [ ] Add dashboard-visible admin diagnostics card for chat health.

### 8) Test Expansion & CI Hardening

- [ ] Add parser contract tests for varied SDK event payload shapes.
- [ ] Add mocked SDK streaming tests for success/error/tool-result sequences.
- [ ] Add route auth tests for all new chat endpoints.
- [ ] Add regression tests for settings token UI API interactions.
- [ ] Add CI job running chat-focused test subset on each PR.
- [ ] Add smoke test script: create session -> send message -> stream done.

### 9) Docs, Onboarding, and Operator Runbooks

- [ ] Add `docs/chat-architecture.md` with sequence diagrams and data flow.
- [ ] Add `docs/chat-token-setup.md` with student setup-token flow.
- [ ] Add `docs/chat-troubleshooting.md` for common validation/stream issues.
- [ ] Update dashboard README with new chat endpoints and env vars.
- [ ] Add Railway deployment notes for Redis and token encryption key setup.
- [ ] Add local dev instructions for running chat with and without Redis.

### 10) Rollout Plan

- [ ] Define acceptance checklist for local, staging, and production gates.
- [ ] Ship to local dev and validate acceptance checklist.
- [ ] Ship to staging Railway environment with Redis enabled.
- [ ] Run pilot with limited users and monitor telemetry/error rates.
- [ ] Address pilot findings and finalize production defaults.
- [ ] Promote to production and monitor first 48h with rollback plan ready.

## Definition of Done

- [ ] All chat endpoints pass auth, validation, and regression tests.
- [ ] SSE reconnect/resume works under forced network interruption tests.
- [ ] Token storage is encrypted and raw token is never exposed in API responses.
- [ ] Multi-instance session continuity works with Redis-backed store.
- [ ] CI includes chat test gate and passes on default branch.
- [ ] Docs are updated for setup, operations, and troubleshooting.
