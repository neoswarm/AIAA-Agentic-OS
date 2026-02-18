# AIAA Dashboard - One-Click Deployment API

Complete guide to the deployment API system for the AIAA Agentic OS.

## Overview

The deployment API enables one-click deployment of any of the 133 AIAA skills to Railway as:
- **Cron jobs** - Scheduled execution (e.g., daily email campaigns)
- **Webhooks** - HTTP endpoints for external triggers (e.g., Calendly → Slack)
- **Web services** - Public web applications (e.g., dashboards, APIs)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend Dashboard                                           │
│ - Browse 133 skills                                          │
│ - Check deployment requirements                              │
│ - One-click deploy button                                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ API Routes (routes/api.py)                                   │
│ - POST /api/workflows/deploy                                 │
│ - GET  /api/workflows/deployable                             │
│ - GET  /api/workflows/<name>/requirements                    │
│ - POST /api/workflows/<name>/rollback                        │
│ - GET  /api/workflows/<service_id>/health                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Deployment Service (services/deployment_service.py)          │
│ - Find and validate skill                                    │
│ - Scaffold Railway service files                             │
│ - Create Railway service via GraphQL                         │
│ - Deploy code                                                 │
│ - Configure environment variables                            │
│ - Set cron schedules                                          │
│ - Generate public domains                                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Railway Platform                                             │
│ - Build with Nixpacks                                        │
│ - Deploy service                                              │
│ - Execute workflow                                            │
│ - Monitor health                                              │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### 1. Deploy Workflow

**POST** `/api/workflows/deploy`

Deploy a skill to Railway.

**Request:**
```json
{
  "workflow_name": "cold-email-campaign",
  "workflow_type": "cron",
  "config": {
    "name": "Cold Email Automation",
    "description": "Daily cold email campaign execution",
    "schedule": "0 9 * * *",
    "env_vars": {
      "CUSTOM_VAR": "value"
    }
  }
}
```

**Response (Success):**
```json
{
  "status": "success",
  "service_id": "abc123",
  "service_url": "https://abc123.up.railway.app",
  "deployment_id": "dep_456",
  "message": "Workflow 'cold-email-campaign' deployed successfully"
}
```

**Response (Error):**
```json
{
  "status": "error",
  "message": "Missing required environment variables: PERPLEXITY_API_KEY"
}
```

**Auth:** Session or API key

---

### 2. List Deployable Workflows

**GET** `/api/workflows/deployable`

List all 133 skills with deployment status.

**Response:**
```json
{
  "total": 133,
  "workflows": [
    {
      "name": "cold-email-campaign",
      "display_name": "Cold Email Campaign",
      "description": "Generate personalized cold email sequences...",
      "has_script": true,
      "script_count": 1,
      "required_env_vars": ["OPENROUTER_API_KEY", "PERPLEXITY_API_KEY"],
      "missing_env_vars": [],
      "deployable": true
    },
    ...
  ]
}
```

**Auth:** Session or API key

---

### 3. Get Workflow Requirements

**GET** `/api/workflows/<workflow_name>/requirements`

Check required environment variables for a workflow.

**Response:**
```json
{
  "workflow": "cold-email-campaign",
  "required_env_vars": ["OPENROUTER_API_KEY", "PERPLEXITY_API_KEY"],
  "missing_env_vars": ["PERPLEXITY_API_KEY"],
  "configured": false
}
```

**Auth:** Session or API key

---

### 4. Rollback Workflow

**POST** `/api/workflows/<workflow_name>/rollback`

Rollback to previous deployment.

**Request:**
```json
{
  "service_id": "abc123"
}
```

**Response:**
```json
{
  "status": "success",
  "deployment_id": "dep_789",
  "message": "Rollback initiated"
}
```

**Auth:** Session or API key (deploy permission)

---

### 5. Check Workflow Health

**GET** `/api/workflows/<service_id>/health`

Check deployed service health.

**Response:**
```json
{
  "status": "healthy",
  "deployment_status": "SUCCESS",
  "last_deployed": "2026-02-18T10:30:00Z"
}
```

**Auth:** Session or API key

---

### 6. List Deployments

**GET** `/api/deployments?limit=50&workflow=cold-email-campaign`

Get deployment history.

**Response:**
```json
{
  "total": 25,
  "deployments": [
    {
      "id": "dep_123",
      "workflow": "cold-email-campaign",
      "status": "success",
      "deployed_at": "2026-02-18T10:30:00Z",
      "deployed_by": "admin"
    }
  ]
}
```

**Auth:** Session or API key

---

### 7. Toggle Favorite

**POST** `/api/favorites/toggle`

Mark a workflow as favorite.

**Request:**
```json
{
  "workflow_name": "cold-email-campaign"
}
```

**Response:**
```json
{
  "status": "success",
  "workflow": "cold-email-campaign",
  "is_favorite": true
}
```

**Auth:** Session or API key (write permission)

---

### 8. Health Check

**GET** `/api/health`

Public health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-02-18T10:30:00Z",
  "service": "aiaa-dashboard-api"
}
```

**Auth:** None (public)

---

## Authentication

Two authentication methods are supported:

### 1. Session Auth (for dashboard)
```javascript
// Frontend makes request with session cookie
fetch('/api/workflows/deploy', {
  method: 'POST',
  credentials: 'include',  // Include session cookie
  body: JSON.stringify({...})
})
```

### 2. API Key Auth (for external integrations)
```bash
curl -X POST https://dashboard.aiaa.dev/api/workflows/deploy \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

Set `DASHBOARD_API_KEY` in `.env` to enable API key auth.

---

## Deployment Process

### What happens when you deploy a workflow:

1. **Validation**
   - Check skill exists in `.claude/skills/`
   - Verify SKILL.md and .py script present
   - Check required environment variables

2. **Scaffolding**
   - Create temp directory
   - Copy skill script(s)
   - Copy shared utilities
   - Generate `requirements.txt`
   - Generate `railway.json` from template
   - Generate `Procfile`
   - For webhooks/web: generate `app.py` wrapper

3. **Railway Service Creation**
   - Create service via GraphQL API
   - Set environment variables
   - Configure cron schedule (if applicable)
   - Generate public domain (if webhook/web)

4. **Deployment**
   - Upload code to Railway
   - Railway builds with Nixpacks
   - Railway deploys service
   - Service starts executing

5. **Health Check**
   - Wait for deployment to complete
   - Verify service is running
   - Check health endpoint (if web/webhook)

6. **Cleanup**
   - Remove temp directory
   - Log deployment event

---

## Configuration Templates

### Cron Workflow

```json
{
  "workflow_name": "cold-email-campaign",
  "workflow_type": "cron",
  "config": {
    "name": "Daily Cold Emails",
    "description": "Send personalized cold emails every morning",
    "schedule": "0 9 * * *",  // 9 AM daily
    "env_vars": {}
  }
}
```

### Webhook Workflow

```json
{
  "workflow_name": "meeting-alert",
  "workflow_type": "webhook",
  "config": {
    "name": "Calendly Meeting Alerts",
    "description": "Notify Slack when meetings are booked",
    "slug": "calendly",  // Creates /webhook endpoint
    "slack_notify": true,
    "env_vars": {}
  }
}
```

### Web Service

```json
{
  "workflow_name": "agency-dashboard",
  "workflow_type": "web",
  "config": {
    "name": "AIAA Dashboard",
    "description": "Main agency dashboard",
    "env_vars": {}
  }
}
```

---

## Cron Schedule Syntax

Standard cron syntax (5 fields):

```
┌───────────── minute (0 - 59)
│ ┌─────────── hour (0 - 23)
│ │ ┌───────── day of month (1 - 31)
│ │ │ ┌─────── month (1 - 12)
│ │ │ │ ┌───── day of week (0 - 6) (Sunday=0)
│ │ │ │ │
* * * * *
```

**Common schedules:**
- Every 3 hours: `0 */3 * * *`
- Daily at 9 AM: `0 9 * * *`
- Every Monday at 10 AM: `0 10 * * 1`
- First of month: `0 0 1 * *`
- Every 15 minutes: `*/15 * * * *`

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `workflow_name is required` | Missing workflow name in request | Add `workflow_name` field |
| `Missing required environment variables` | Env vars not set | Set required vars in `.env` or Railway dashboard |
| `Skill not found` | Invalid workflow name | Check skill exists: `ls .claude/skills/` |
| `Railway credentials not configured` | Missing Railway API token | Set `RAILWAY_API_TOKEN` in `.env` |
| `Railway API timeout` | Network issues | Retry or increase timeout |
| `Deployment failed` | Build or runtime error | Check Railway logs |

### Validation Errors

Before deployment, the API checks:
- ✅ Workflow exists
- ✅ SKILL.md present
- ✅ Python script present
- ✅ Required env vars set
- ✅ Railway credentials configured

---

## Testing

### Run Deployment Service Tests

```bash
cd railway_apps/aiaa_dashboard
python3 services/test_deployment_service.py
```

Expected output:
```
✅ PASS: Import
✅ PASS: Initialization
✅ PASS: Env Var Checking
✅ PASS: Skill Finding

Total: 4/4 tests passed
```

### Test API Endpoints Locally

```bash
# Start dashboard
python3 app.py

# In another terminal, test endpoints
curl http://localhost:8080/api/health
curl -H "X-API-Key: test" http://localhost:8080/api/workflows/deployable
```

---

## Security

### API Key Management

Generate a secure API key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Add to `.env`:
```bash
DASHBOARD_API_KEY=your_generated_key_here
```

### Railway Token Security

- ⚠️ Never commit `RAILWAY_API_TOKEN` to git
- ⚠️ Never expose token in frontend code
- ⚠️ Never log token in deployment logs
- ✅ Set token in Railway project environment variables
- ✅ Rotate token monthly

### Permissions

API endpoints require different permission levels:
- `read` - View workflows, check health
- `write` - Toggle favorites, manage preferences
- `deploy` - Deploy, rollback, modify services

---

## Railway Free Tier Limits

Stay within limits:
- 8 web endpoints max
- 500 hours/month execution
- $5 credit/month
- No credit card required

**Recommendations:**
- Deploy only production-ready workflows
- Use cron for scheduled tasks (doesn't count toward web limit)
- Monitor usage in Railway dashboard
- Delete unused services

---

## Monitoring & Logging

### Deployment Events

All deployments are logged with:
- Timestamp
- Workflow name
- Status (success/error)
- Deployed by (user)
- Service ID
- Error message (if failed)

### Health Monitoring

Services report:
- Deployment status
- Last deployed timestamp
- Health check status
- Error counts

### Railway Logs

Access logs in Railway dashboard:
1. Go to service
2. Click "Deployments"
3. Select deployment
4. View "Logs" tab

---

## Troubleshooting

### Deployment stuck "Building"

- Railway build timeout (15 minutes max)
- Check Railway logs for build errors
- Verify `requirements.txt` has valid packages
- Check Python version compatibility

### Service crashes after deploy

- Check Railway logs for runtime errors
- Verify environment variables set correctly
- Check script has proper error handling
- Verify dependencies installed

### Webhook not receiving requests

- Check public domain generated correctly
- Verify webhook endpoint is `/webhook`
- Check Procfile uses correct start command
- Test endpoint with `curl`

### Cron not executing

- Verify cron schedule syntax
- Check Railway service type is "Cron"
- Verify script runs locally first
- Check Railway execution logs

---

## Future Enhancements

- [ ] Real-time deployment status (WebSockets)
- [ ] Deployment analytics dashboard
- [ ] Auto-scaling based on usage
- [ ] Multi-region deployment
- [ ] Blue/green deployments
- [ ] Canary releases
- [ ] Deployment approval workflows
- [ ] Cost estimation before deploy
- [ ] Automated rollback on errors
- [ ] Deployment templates library

---

## Support

For issues or questions:
1. Check this guide
2. Review Railway logs
3. Run validation tests
4. Check skill validator report
5. Contact system admin
