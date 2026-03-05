# AIAA Deployment System - Quick Start

## 5-Minute Setup

### 1. Add to Dashboard (app.py)

```python
# Add this import
from routes.api import api_bp

# Register blueprint
app.register_blueprint(api_bp)
```

### 2. Set Environment Variables (.env)

```bash
RAILWAY_API_TOKEN=your_railway_token
RAILWAY_PROJECT_ID=3b96c81f-9518-4131-b2bc-bcd7a524a5ef
DASHBOARD_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

### 3. Test It

```bash
# Run dashboard
python3 app.py

# Test API (in another terminal)
curl http://localhost:8080/api/health
curl -H "X-API-Key: your_key" http://localhost:8080/api/workflows/deployable
```

---

## Deploy Your First Workflow

### Via API
```bash
curl -X POST http://localhost:8080/api/workflows/deploy \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "cold-email-campaign",
    "workflow_type": "cron",
    "config": {
      "name": "Cold Email Automation",
      "schedule": "0 9 * * *"
    }
  }'
```

### Via Frontend
```html
<button onclick="deployWorkflow('cold-email-campaign', 'cron')">
  🚀 Deploy
</button>

<script>
async function deployWorkflow(name, type) {
  const response = await fetch('/api/workflows/deploy', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      workflow_name: name,
      workflow_type: type,
      config: {name, schedule: '0 9 * * *'}
    })
  });
  const result = await response.json();
  alert(result.status === 'success' ? 
    `✅ Deployed! ${result.service_url}` : 
    `❌ Error: ${result.message}`);
}
</script>
```

---

## Common Commands

### Validate All Skills
```bash
python3 .claude/skills/_shared/skill_validator.py
```

### Test Deployment Service
```bash
cd railway_apps/aiaa_dashboard
python3 services/test_deployment_service.py
```

### Check Required Env Vars
```bash
curl http://localhost:8080/api/workflows/cold-email-campaign/requirements
```

### Check Service Health
```bash
curl http://localhost:8080/api/workflows/SERVICE_ID/health
```

### Rollback Deployment
```bash
curl -X POST http://localhost:8080/api/workflows/cold-email-campaign/rollback \
  -H "Content-Type: application/json" \
  -d '{"service_id": "SERVICE_ID"}'
```

---

## Troubleshooting

### "Missing required environment variables"
→ Set env vars: `OPENROUTER_API_KEY`, `PERPLEXITY_API_KEY`, etc.

### "Railway credentials not configured"
→ Set `RAILWAY_API_TOKEN` and `RAILWAY_PROJECT_ID` in `.env`

### "Skill not found"
→ Check skill exists: `ls .claude/skills/`

### "Import error: services.deployment_service"
→ Run from dashboard directory: `cd railway_apps/aiaa_dashboard`

---

## File Locations

```
railway_apps/aiaa_dashboard/
├── services/
│   ├── deployment_service.py    # Core deployment logic
│   ├── test_deployment_service.py  # Tests
│   └── README.md                 # Service docs
├── routes/
│   └── api.py                    # API endpoints
├── DEPLOYMENT_API_GUIDE.md       # Complete API docs
├── INTEGRATION_GUIDE.md          # Integration guide
└── QUICK_START.md                # This file

.claude/skills/
├── _shared/
│   ├── skill_validator.py        # Skill validation
│   └── __init__.py               # Shared utilities
└── [133 skills]/
    ├── SKILL.md                  # Skill docs
    └── *.py                      # Skill script
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/workflows/deploy` | Deploy a workflow |
| GET | `/api/workflows/deployable` | List all deployable workflows |
| GET | `/api/workflows/<name>/requirements` | Check required env vars |
| POST | `/api/workflows/<name>/rollback` | Rollback deployment |
| GET | `/api/workflows/<service_id>/health` | Check service health |
| GET | `/api/deployments` | List deployment history |
| POST | `/api/favorites/toggle` | Toggle favorite workflow |
| GET | `/api/health` | Health check |

---

## Workflow Types

| Type | Use Case | Example |
|------|----------|---------|
| `cron` | Scheduled execution | Daily email campaigns |
| `webhook` | HTTP endpoint | Calendly → Slack |
| `web` | Web service | Dashboard, API |

---

## Cron Schedules

| Schedule | Frequency |
|----------|-----------|
| `0 9 * * *` | Daily at 9 AM |
| `0 */3 * * *` | Every 3 hours |
| `*/15 * * * *` | Every 15 minutes |
| `0 10 * * 1` | Every Monday at 10 AM |
| `0 0 1 * *` | First of every month |

---

## Railway Free Tier

- 8 web endpoints max
- 500 hours/month
- $5 credit/month
- No credit card required

**Tip:** Use cron for scheduled tasks (doesn't count toward web limit)

---

## Need More Help?

1. Read `DEPLOYMENT_API_GUIDE.md` - Complete API documentation
2. Read `INTEGRATION_GUIDE.md` - Integration instructions
3. Read `services/README.md` - Service-level docs
4. Run tests: `python3 services/test_deployment_service.py`
5. Validate skills: `python3 .claude/skills/_shared/skill_validator.py`
6. Check Railway logs in Railway dashboard
