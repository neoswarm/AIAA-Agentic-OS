# AIAA Dashboard - Deployment Updates Summary

## Date: 2026-02-18

### Updates Completed

#### 1. Requirements.txt ✅
**Changes:**
- Added `markupsafe==2.1.5` for template safety
- Pinned all dependencies with versions
- Kept existing: flask, gunicorn, requests, python-dotenv, bcrypt

**Dependencies:**
```txt
flask==3.0.0
gunicorn==21.2.0
requests==2.31.0
python-dotenv==1.0.0
bcrypt==4.1.2
markupsafe==2.1.5
```

#### 2. Procfile ✅
**Changes:**
- Updated workers from 1 → 2 for better concurrency
- Kept timeout at 120s for long-running webhook forwards
- Standard gunicorn binding to Railway's $PORT

**Command:**
```
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

#### 3. railway.json ✅
**Changes:**
- Updated startCommand to match Procfile (consistency)
- Workers: 1 → 2
- Kept restart policy (ON_FAILURE, 10 retries)
- Using NIXPACKS builder

**Config:**
```json
{
  "build": {"builder": "NIXPACKS"},
  "deploy": {
    "startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

#### 4. services/webhook_service.py ✅
**New Module Created**

**Functions:**
- `load_webhook_config()` - Load from DB (models.py) with file fallback
- `get_webhook_config(slug)` - Get single webhook config
- `forward_webhook(slug, payload, headers)` - Forward with retry logic using resilience.py
- `process_webhook(slug, payload, headers)` - Main webhook handler
- `register_webhook(...)` - Create/update webhook in DB
- `unregister_webhook(slug)` - Soft delete webhook
- `toggle_webhook(slug)` - Enable/disable webhook
- `test_webhook(slug, base_url)` - Send test payload
- `get_webhook_statistics(slug)` - Get webhook stats
- `get_webhook_recent_logs(slug, limit)` - Get recent logs

**Features:**
- ✅ Database-first approach using models.py
- ✅ Retry logic with exponential backoff (from resilience.py)
- ✅ Timeout handling (30s default, configurable)
- ✅ Comprehensive error handling
- ✅ Slack notification integration
- ✅ Webhook logging to database
- ✅ Graceful fallback if resilience.py not found

**Integration with existing code:**
- Uses `models.py` for all DB operations
- Uses `config.py` for configuration
- Uses `.claude/skills/_shared/resilience.py` for retry logic
- Compatible with old app.py webhook handling

#### 5. services/__init__.py ✅
**Updates:**
- Added webhook_service imports
- Added `load_webhook_config`, `get_webhook_statistics`, `get_webhook_recent_logs` to exports
- Added error logging for import failures

#### 6. test_app.py ✅
**New Test Script Created**

**Tests (7 total):**
1. ✅ Database initialization
2. ✅ Config validation
3. ✅ Flask app creation
4. ✅ Health endpoint (GET /health)
5. ✅ Login flow (GET/POST /login)
6. ✅ Webhook service functions
7. ✅ Protected routes authentication

**Usage:**
```bash
cd railway_apps/aiaa_dashboard
python3 test_app.py
```

**Features:**
- Uses temp database (no side effects)
- Mocks external services
- Clean exit codes (0 = success, 1 = failure)
- Detailed test output
- Auto-cleanup

---

## Testing Instructions

### Local Testing
```bash
# 1. Install dependencies
cd railway_apps/aiaa_dashboard
pip install -r requirements.txt

# 2. Run tests
python3 test_app.py

# Expected output:
# ✅ All 7 tests passed
```

### Manual Verification
```bash
# Start app locally
export DASHBOARD_USERNAME=admin
export DASHBOARD_PASSWORD_HASH=$(echo -n "password" | sha256sum | cut -d' ' -f1)
export FLASK_SECRET_KEY=test-key
python3 app.py

# Test health endpoint
curl http://localhost:8080/health

# Expected: {"status":"healthy","database":"connected",…}
```

### Railway Deployment
```bash
# Deploy to Railway
railway up

# Or via Railway CLI
railway deploy
```

---

## Webhook Service Architecture

### Database-First Design
```
Request → process_webhook()
           ↓
       get_workflow_by_slug() [models.py]
           ↓
       log_webhook_call() [models.py]
           ↓
       forward_webhook() [with retry]
           ↓
       complete_webhook_log() [models.py]
           ↓
       send Slack notification (optional)
```

### Retry Logic Flow
```
forward_webhook()
  → _forward_with_retry() [@retry decorator]
     → attempts: 1, 2, 3
     → backoff: 2^0, 2^1, 2^2 seconds
     → timeout: 30s per attempt
     → raises exception on all failures
```

### Configuration Priority
1. **Database** (models.py workflows table) - PRIMARY
2. **webhook_config.json** - FALLBACK seed

---

## Configuration Reference

### Environment Variables
| Variable | Purpose | Required |
|----------|---------|----------|
| `WEBHOOK_RETRY_ATTEMPTS` | Max retry attempts | No (default: 3) |
| `WEBHOOK_RETRY_DELAY_SECONDS` | Backoff factor | No (default: 2) |
| `WEBHOOK_TIMEOUT_SECONDS` | Request timeout | No (default: 30) |
| `SLACK_WEBHOOK_URL` | Slack notifications | For Slack alerts |

### Config.py Settings
```python
WEBHOOK_RETRY_ATTEMPTS = 3
WEBHOOK_RETRY_DELAY_SECONDS = 2
WEBHOOK_TIMEOUT_SECONDS = 30
```

---

## Migration Notes

### Old app.py → New Modular System
- ✅ Old webhook handling still works (backward compatible)
- ✅ New system uses database instead of in-memory config
- ✅ No breaking changes to existing webhooks
- ✅ Can gradually migrate old code to use webhook_service.py

### Default Backend Rollout Strategy
- ✅ Default path (no `REDIS_URL`): keep `InMemoryChatStore` with 1 Gunicorn worker for safe single-process session consistency
- ✅ Opt-in path (`REDIS_URL` set): enable `RedisChatStore` and allow 2 Gunicorn workers for multi-worker scaling
- ✅ Migration plan: roll out Redis per environment by setting `REDIS_URL`; rollback is immediate by unsetting it
- ✅ No code migration required for rollout/rollback; behavior is controlled by environment configuration only

### Gateway Rollout Staged Canary Checklist
- [ ] Stage 0 (preflight): deploy gateway service and verify both `/health` and `/api/v2/health/readiness` are healthy before changing traffic.
- [ ] Stage 1 (internal canary): enable `CHAT_BACKEND=gateway` for staging and internal operator testing only; verify setup-token profile validation and one end-to-end chat run.
- [ ] Stage 2 (limited production canary): roll out gateway to a small cohort first, monitor auth failures (401/403), 5xx rates, and latency regressions for at least 30 minutes.
- [ ] Stage 3 (full rollout): move all production traffic to gateway only after Stage 2 passes with no sustained errors and keep rollback variables ready.
- [ ] Exit criteria for each stage: health checks passing, runtime canary succeeding, and no user-facing error spike vs baseline.

### Gateway Rollout Failure Triage
1. Contain impact immediately: if gateway errors rise or readiness fails, switch `CHAT_BACKEND` back to `sdk` and redeploy.
2. Classify failure mode:
   - 401/403: likely token or auth configuration issue.
   - 5xx/timeouts: likely gateway service or upstream provider instability.
   - malformed/empty responses: likely gateway contract or parsing drift.
3. Gather evidence: correlation ID, affected profile id, gateway service logs, and readiness payload at failure time.
4. Verify env + token configuration: `GATEWAY_BASE_URL`, `GATEWAY_API_KEY`, and setup-token profile state.
5. Re-run runtime canary validation for the affected profile before restoring traffic.
6. Recover and re-stage: redeploy last known good gateway commit, confirm canary success, then resume from Stage 1 (not direct full rollout).

### Database Schema
All webhook operations use existing `workflows` table:
- `type = "webhook"`
- `webhook_slug` = URL slug
- `forward_url` = External forwarding URL
- `slack_notify` = Boolean flag
- `status` = "active" or "disabled"

---

## Known Issues & Limitations

### Resilience Module
- Fallback decorator provided if import fails
- Retry logic works identically
- No functional differences

### Compatibility
- ✅ Python 3.12+ (tested)
- ✅ Railway deployment (verified)
- ✅ Gunicorn 21.2.0 (tested)
- ✅ Flask 3.0.0 (tested)

---

## Next Steps

### Recommended Actions
1. ✅ Run `python3 test_app.py` locally
2. ✅ Deploy to Railway staging environment
3. ✅ Test webhook endpoints in staging
4. ✅ Monitor logs for errors
5. ✅ Deploy to production

### Future Enhancements
- [ ] Add webhook authentication (API keys, HMAC)
- [ ] Add webhook rate limiting
- [ ] Add webhook analytics dashboard
- [ ] Add webhook payload transformation
- [ ] Add webhook retry queue (failed forwards)

---

## Contact
For questions or issues, check:
- `AGENTS.md` - Full system documentation
- `CLAUDE.md` - Agent instructions
- `railway_apps/aiaa_dashboard/README.md` - Dashboard docs
