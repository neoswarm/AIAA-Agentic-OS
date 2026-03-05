# Integration Guide: Adding API Routes to Dashboard

This guide shows how to integrate the new API routes into the existing Flask dashboard.

## Step 1: Register the API Blueprint

In your `app.py`, add this import near the top:

```python
from routes.api import api_bp
```

Then register the blueprint after creating the Flask app:

```python
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))

# Register API blueprint
app.register_blueprint(api_bp)
```

## Step 2: Add Required Environment Variables

Add these to your `.env` file:

```bash
# Railway API credentials (required for deployment)
RAILWAY_API_TOKEN=your_railway_token_here
RAILWAY_PROJECT_ID=3b96c81f-9518-4131-b2bc-bcd7a524a5ef
RAILWAY_ENV_ID=production

# Dashboard API key (optional, for API key auth)
DASHBOARD_API_KEY=your_secure_api_key_here

# Project root (optional, auto-detected if not set)
PROJECT_ROOT=/Users/lucasnolan/Agentic OS
```

## Step 3: Update requirements.txt

The new services require `requests`. Update `requirements.txt`:

```txt
flask==3.0.0
requests==2.31.0
gunicorn==21.2.0
python-dotenv==1.0.0
bcrypt==4.1.2
```

## Step 4: Test the API Endpoints

### Health Check (no auth)
```bash
curl http://localhost:8080/api/health
```

### List Deployable Workflows (with session auth)
```bash
curl -H "Cookie: session=..." http://localhost:8080/api/workflows/deployable
```

### Deploy a Workflow (with API key)
```bash
curl -X POST http://localhost:8080/api/workflows/deploy \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "cold-email-campaign",
    "workflow_type": "cron",
    "config": {
      "name": "Cold Email Automation",
      "schedule": "0 9 * * *",
      "env_vars": {}
    }
  }'
```

### Check Workflow Health
```bash
curl -H "X-API-Key: your_api_key" \
  http://localhost:8080/api/workflows/service_id_here/health
```

## Step 5: Frontend Integration

Add a deploy button to your workflow cards in the dashboard HTML:

```html
<button onclick="deployWorkflow('cold-email-campaign', 'cron')">
  🚀 Deploy
</button>

<script>
async function deployWorkflow(name, type) {
  const response = await fetch('/api/workflows/deploy', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      workflow_name: name,
      workflow_type: type,
      config: {
        name: name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        schedule: '0 9 * * *'  // default schedule
      }
    })
  });
  
  const result = await response.json();
  
  if (result.status === 'success') {
    alert(`Deployed! Service URL: ${result.service_url}`);
  } else {
    alert(`Error: ${result.message}`);
  }
}
</script>
```

## Step 6: Error Handling

The API uses standard HTTP status codes:

- `200` - Success
- `400` - Bad request (validation error)
- `401` - Unauthorized (missing or invalid credentials)
- `500` - Internal server error

All responses include a JSON body with `status` and `message` fields:

```json
{
  "status": "success",
  "message": "Workflow deployed successfully"
}
```

## Step 7: Database Integration (Optional)

To enable deployment history tracking, add a database model:

```python
# models/deployment.py
from datetime import datetime

class Deployment:
    def __init__(self, workflow, status, deployed_at, deployed_by):
        self.workflow = workflow
        self.status = status
        self.deployed_at = deployed_at
        self.deployed_by = deployed_by
    
    def save(self):
        # Save to SQLite, PostgreSQL, or JSON file
        pass
    
    @classmethod
    def get_history(cls, limit=50):
        # Retrieve deployment history
        pass
```

Then update `log_deployment()` and `log_event()` in `routes/api.py` to use the model.

## Troubleshooting

### "Missing required environment variables"

Make sure all required env vars are set in `.env`:
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY`
- `PERPLEXITY_API_KEY`
- `SLACK_WEBHOOK_URL`
- etc.

### "Railway credentials not configured"

Set `RAILWAY_API_TOKEN` and `RAILWAY_PROJECT_ID` in `.env`.

### "Skill not found"

Verify the skill exists in `.claude/skills/<workflow_name>/` and has both `SKILL.md` and a `.py` script.

### "Railway API timeout"

Increase the timeout in `deployment_service.py`:
```python
self.timeout = 30  # increase from 10 to 30 seconds
```

## Security Considerations

1. **Never expose `RAILWAY_API_TOKEN`** - Keep it server-side only
2. **Use HTTPS in production** - Railway provides SSL by default
3. **Rotate API keys regularly** - Update `DASHBOARD_API_KEY` monthly
4. **Validate all inputs** - The API validates workflow names and types
5. **Rate limit API endpoints** - Consider adding Flask-Limiter for production

## Next Steps

- Add frontend UI for deployment management
- Implement deployment history tracking
- Add real-time deployment status updates (WebSockets)
- Create deployment rollback UI
- Add deployment analytics and metrics
