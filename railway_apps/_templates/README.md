# Railway Configuration Templates

These templates are used by the deployment orchestrator to generate Railway service configurations.

## Templates

### `cron.railway.json`
For scheduled workflows that run periodically.

**Variables:**
- `start_command` - Python script to execute (e.g., `python3 run.py`)
- `restart_policy` - When to restart (ON_FAILURE, NEVER, ALWAYS)
- `max_retries` - Maximum restart attempts
- `cron_schedule` - Cron expression (e.g., `0 */3 * * *`)

**Example Usage:**
```python
from jinja2 import Template

template = Template(Path("cron.railway.json").read_text())
config = template.render(
    start_command="python3 generate_report.py",
    restart_policy="ON_FAILURE",
    max_retries=3,
    cron_schedule="0 9 * * *"  # Daily at 9am
)
```

---

### `webhook.railway.json`
For HTTP-triggered workflows (receive webhooks from external services).

**Variables:**
- `timeout` - Request timeout in seconds (default: 300)

**Defaults:**
- Gunicorn with 1 worker
- Restart on failure (10 retries)
- 5-minute timeout for long processing

**Example Usage:**
```python
template = Template(Path("webhook.railway.json").read_text())
config = template.render(timeout=300)
```

---

### `web.railway.json`
For web services with UI or API endpoints.

**Variables:**
- `timeout` - Request timeout in seconds (default: 120)
- `workers` - Number of Gunicorn workers (default: 1)

**Defaults:**
- Health check at `/health`
- Restart on failure (10 retries)
- 30-second health check timeout

**Example Usage:**
```python
template = Template(Path("web.railway.json").read_text())
config = template.render(
    timeout=120,
    workers=2
)
```

---

## Usage in Deployment Pipeline

The deployment orchestrator automatically selects the correct template based on the workflow's `type` field in YAML frontmatter:

```python
from pathlib import Path
from jinja2 import Template

def generate_railway_config(workflow_type: str, metadata: dict) -> dict:
    """Generate railway.json from template."""
    template_path = Path(__file__).parent / "_templates" / f"{workflow_type}.railway.json"
    template_content = template_path.read_text()

    template = Template(template_content)

    # Extract deployment config
    deploy_config = metadata.get("deployment", {}).get("railway_config", {})

    # Apply defaults
    context = {
        "start_command": deploy_config.get("start_command", f"python3 {metadata['execution_scripts'][0]}"),
        "restart_policy": deploy_config.get("restart_policy", "ON_FAILURE"),
        "max_retries": deploy_config.get("max_retries", 3),
        "cron_schedule": metadata.get("deployment", {}).get("cron_schedule", "0 * * * *"),
        "timeout": deploy_config.get("timeout_seconds", 120),
        "workers": deploy_config.get("workers", 1),
    }

    rendered = template.render(**context)
    return json.loads(rendered)
```

---

## Template Variables Reference

| Variable | Type | Required | Default | Used In |
|----------|------|----------|---------|---------|
| `start_command` | string | Yes | `python3 <script>` | cron |
| `restart_policy` | enum | Yes | ON_FAILURE | cron |
| `max_retries` | int | Yes | 3 | cron, webhook, web |
| `cron_schedule` | string | Yes | - | cron |
| `timeout` | int | Yes | 120/300 | webhook, web |
| `workers` | int | Yes | 1 | web |

---

## Adding Custom Templates

To add a new workflow type:

1. Create `<type>.railway.json` in this directory
2. Use Jinja2 syntax for variables: `{{ variable_name }}`
3. Update `generate_railway_config()` to include default values
4. Document the template in this README

**Example: Custom "manual" type for on-demand execution:**

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "{{ start_command }}",
    "restartPolicyType": "NEVER"
  }
}
```
