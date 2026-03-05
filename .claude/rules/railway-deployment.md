# Railway & Modal Deployment

## Railway Dashboard Deployment
```bash
cd railway_apps/aiaa_dashboard
railway init    # First time only
railway up      # Deploy/update
railway domain  # Get public URL
```

### Dashboard Variables (per-service)
| Variable | Purpose |
|----------|---------|
| `DASHBOARD_USERNAME` | Login username |
| `DASHBOARD_PASSWORD_HASH` | SHA-256 hashed password |
| `FLASK_SECRET_KEY` | Session security |
| `RAILWAY_API_TOKEN` | Cron management, shared var sync |

### API Keys (project-level shared variables)
Set once — all services inherit: `OPENROUTER_API_KEY`, `PERPLEXITY_API_KEY`, `ANTHROPIC_API_KEY`, `SLACK_WEBHOOK_URL`, `FAL_KEY`, `APIFY_API_TOKEN`, `CALENDLY_API_KEY`, `INSTANTLY_API_KEY`

### Key Endpoints
| Endpoint | Purpose |
|----------|---------|
| `/health` | Health check (public) |
| `/workflows` | Active cron + webhook workflows |
| `/env` | Environment variable management |
| `/webhook/<slug>` | Public webhook receiver |
| `/api/shared-variables/sync` | Bulk-set shared variables |

## Modal Serverless Deployment
```bash
modal deploy execution/<script>.py
```

### Critical: dotenv Import Pattern
Scripts on Modal MUST separate `requests` and `dotenv` imports:
```python
try:
    import requests
except ImportError:
    sys.exit(1)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Not needed on Modal
```

### Modal Limits
- 8 web endpoints max (free tier)
- 30 compute hours/month
- Cold starts: 2-10 seconds

### Pre-Deploy Checklist
- [ ] Procfile and requirements.txt present
- [ ] Environment variables configured
- [ ] Health endpoint responds
- [ ] No secrets in code
- [ ] dotenv import pattern correct (Modal)
