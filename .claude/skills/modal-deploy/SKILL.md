---
name: modal-deploy
description: Deploy execution scripts to Modal cloud. Use when user asks to deploy to Modal, push code to cloud, or update Modal functions.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Modal Cloud Deployment

## Goal
Deploy execution scripts to Modal for serverless cloud execution.

## Deploy Command

Using the automated deployment script:
```bash
python3 .claude/skills/modal-deploy/modal_deploy.py \
  --script execution/script_name.py \
  --app-name my-app
```

Or direct Modal CLI:
```bash
modal deploy execution/<script>.py
```

## Currently Deployed Apps

| App | Script | Endpoints |
|-----|--------|-----------|
| `calendly-meeting-prep` | `execution/calendly_meeting_prep.py` | webhook (POST), health (GET) |
| `slack-test` | `execution/modal_slack_test.py` | webhook (POST), health (GET) |

## Pre-Deploy Checklist

**CRITICAL: Fix dotenv imports before deploying.** Modal containers don't have `python-dotenv`. If `requests` and `dotenv` are in the same `try/except sys.exit(1)` block, the container crashes silently (requests hang forever).

```python
# CORRECT pattern for Modal-compatible scripts:
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

37 scripts in `execution/` still have the crash-causing pattern. Fix before deploying.

## Modal Secrets

Secrets are configured at modal.com (not local `.env`):

| Secret Name | Variable |
|-------------|----------|
| `openrouter-secret` | OPENROUTER_API_KEY |
| `perplexity-secret` | PERPLEXITY_API_KEY |
| `slack-webhook` | SLACK_WEBHOOK_URL |
| `google-service-account` | GOOGLE_SERVICE_ACCOUNT_JSON |
| `calendly-secret` | CALENDLY_API_KEY |

```bash
modal secret list          # View configured secrets
modal secret create <name> KEY=value  # Create new secret
```

## Free Tier Limits

- **8 web endpoints max** (~4 apps with webhook+health each)
- 30 compute hours/month
- Cold starts: 2-10 seconds after idle

```bash
modal app list             # See all apps and endpoint count
modal app stop <app-id>    # Free up endpoints
```

## Adding New Modal Apps

Standard structure for a new Modal-deployable script:

```python
try:
    import modal

    app = modal.App("app-name")
    image = modal.Image.debian_slim().pip_install("requests", "fastapi")

    @app.function(
        image=image,
        secrets=[modal.Secret.from_name("slack-webhook")],
        timeout=30,
    )
    @modal.fastapi_endpoint(method="POST")
    def webhook(payload: dict):
        return handle_webhook(payload)

    @app.function(image=image)
    @modal.fastapi_endpoint(method="GET")
    def health():
        return {"status": "ok", "service": "app-name"}

except ImportError:
    pass  # Modal not installed locally
```

## Cron Jobs
```python
@app.function(schedule=modal.Cron("0 * * * *"))  # Every hour
def my_scheduled_function():
    pass
```

## Debugging

```bash
modal app logs <app-name>   # Check container logs (import crashes, errors)
```

If `curl` connects but hangs: check logs for import errors or missing secrets.
