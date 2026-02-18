#!/usr/bin/env python3
"""
Deploy Workflow to Railway

Unified deployment of any AIAA workflow to the user's Railway project.
Handles cron jobs, webhook workflows, and web services. Discovers the
dashboard project automatically from workflow_config.json or Railway CLI.

Usage:
    # Cron workflow
    python3 execution/deploy_to_railway.py --directive x_keyword_youtube_content --type cron --schedule "0 */3 * * *" --auto

    # Webhook workflow (no rebuild -- registers via dashboard API)
    python3 execution/deploy_to_railway.py --directive calendly_meeting_prep --type webhook --slug calendly --slack-notify --auto

    # Web service
    python3 execution/deploy_to_railway.py --directive ai_news_digest --type web --auto

    # Auto-detect type from directive content
    python3 execution/deploy_to_railway.py --directive x_keyword_youtube_content --auto

    # Utilities
    python3 execution/deploy_to_railway.py --list
    python3 execution/deploy_to_railway.py --directive calendly_meeting_prep --info
    python3 execution/deploy_to_railway.py --directive calendly_meeting_prep --dry-run
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DIRECTIVES_DIR = PROJECT_ROOT / "directives"
EXECUTION_DIR = PROJECT_ROOT / "execution"
RAILWAY_APPS_DIR = PROJECT_ROOT / "railway_apps"
DASHBOARD_DIR = RAILWAY_APPS_DIR / "aiaa_dashboard"
WORKFLOW_CONFIG = DASHBOARD_DIR / "workflow_config.json"

RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"


# =============================================================================
# Utility Functions (adapted from deploy_aiaa_dashboard.py)
# =============================================================================

def run_command(cmd: list, cwd: str = None, capture: bool = True) -> tuple:
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, cwd=cwd, timeout=300)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def get_env_vars_from_dotenv() -> dict:
    env_file = PROJECT_ROOT / ".env"
    env_vars = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value:
                    env_vars[key] = value
    return env_vars


# =============================================================================
# Directive Parsing (adapted from deploy_to_modal.py)
# =============================================================================

def list_directives() -> list:
    return sorted([f.stem for f in DIRECTIVES_DIR.glob("*.md")])


def load_directive(name: str) -> str:
    path = DIRECTIVES_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Directive not found: {name}")
    return path.read_text()


def parse_directive(content: str) -> dict:
    result = {
        "execution_scripts": [],
        "integrations": [],
        "inputs": {},
        "description": "",
        "has_llm": False,
    }

    for section_name in ["What This Workflow Is", "What This Workflow Does", "Overview"]:
        desc_match = re.search(rf"##\s+{section_name}\s*\n(.+?)(?=\n##|\Z)", content, re.DOTALL)
        if desc_match:
            result["description"] = desc_match.group(1).strip().split("\n")[0][:200]
            break
    if not result["description"]:
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
        if lines:
            result["description"] = lines[0][:200]

    script_patterns = [
        r"python3?\s+execution/(\w+)\.py",
        r"execution/(\w+)\.py",
        r"`execution/(\w+)\.py`",
    ]
    for pattern in script_patterns:
        result["execution_scripts"].extend(re.findall(pattern, content))
    result["execution_scripts"] = list(set(result["execution_scripts"]))

    integration_keywords = {
        "slack": ["Slack", "slack_notify", "SLACK_WEBHOOK"],
        "google_docs": ["Google Doc", "Google Docs", "create_google_doc", "googleapis"],
        "google_sheets": ["Google Sheet", "read_sheet", "update_sheet", "gspread"],
        "gmail": ["Gmail", "send_email"],
        "openrouter": ["OpenRouter", "OPENROUTER_API_KEY", "openrouter.ai"],
        "anthropic": ["Claude", "Anthropic", "ANTHROPIC_API_KEY"],
        "openai": ["GPT", "OpenAI", "OPENAI_API_KEY", "gpt-4"],
        "perplexity": ["Perplexity", "PERPLEXITY_API_KEY", "perplexity.ai"],
        "calendly": ["Calendly", "CALENDLY_API_KEY"],
        "apify": ["Apify", "APIFY_API_TOKEN"],
        "fal": ["fal.ai", "FAL_KEY"],
    }

    content_lower = content.lower()
    for integration, keywords in integration_keywords.items():
        for keyword in keywords:
            if keyword.lower() in content_lower:
                if integration not in result["integrations"]:
                    result["integrations"].append(integration)
                break

    llm_indicators = ["openrouter", "anthropic", "openai", "claude", "gpt", "llm", "ai agent"]
    result["has_llm"] = any(ind in content_lower for ind in llm_indicators)

    return result


def get_required_env_keys(parsed: dict) -> list:
    key_map = {
        "openrouter": "OPENROUTER_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "perplexity": "PERPLEXITY_API_KEY",
        "slack": "SLACK_WEBHOOK_URL",
        "calendly": "CALENDLY_API_KEY",
        "apify": "APIFY_API_TOKEN",
        "fal": "FAL_KEY",
        "google_docs": "GOOGLE_OAUTH_TOKEN_JSON",
        "google_sheets": "GOOGLE_OAUTH_TOKEN_JSON",
        "gmail": "GOOGLE_OAUTH_TOKEN_JSON",
    }
    keys = []
    for integration in parsed["integrations"]:
        key = key_map.get(integration)
        if key and key not in keys:
            keys.append(key)
    if parsed["has_llm"] and "OPENROUTER_API_KEY" not in keys:
        keys.append("OPENROUTER_API_KEY")
    return keys


def detect_type(content: str) -> str:
    content_lower = content.lower()
    cron_indicators = ["cron", "schedule", "every hour", "every day", "every 3 hour",
                       "runs every", "scheduled", "periodic", "interval"]
    webhook_indicators = ["webhook", "incoming post", "external trigger",
                          "event-driven", "invitee.created", "stripe event",
                          "typeform", "zapier trigger"]
    cron_score = sum(1 for ind in cron_indicators if ind in content_lower)
    webhook_score = sum(1 for ind in webhook_indicators if ind in content_lower)
    if cron_score > webhook_score:
        return "cron"
    elif webhook_score > cron_score:
        return "webhook"
    return "web"


def scan_script_imports(script_name: str) -> list:
    """Scan an execution script's imports and return pip package names."""
    script_path = EXECUTION_DIR / f"{script_name}.py"
    if not script_path.exists():
        return []

    import_to_package = {
        "requests": "requests",
        "flask": "flask",
        "gunicorn": "gunicorn",
        "dotenv": "python-dotenv",
        "openai": "openai",
        "anthropic": "anthropic",
        "slack_sdk": "slack-sdk",
        "apify_client": "apify-client",
        "pandas": "pandas",
        "gspread": "gspread",
        "google": "google-api-python-client",
        "googleapiclient": "google-api-python-client",
        "google_auth_oauthlib": "google-auth-oauthlib",
        "bs4": "beautifulsoup4",
        "PIL": "Pillow",
        "yaml": "pyyaml",
        "scipy": "scipy",
        "numpy": "numpy",
    }

    try:
        source = script_path.read_text()
        tree = ast.parse(source)
    except Exception:
        return ["requests", "python-dotenv"]

    found_packages = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in import_to_package:
                    found_packages.add(import_to_package[top])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in import_to_package:
                    found_packages.add(import_to_package[top])

    found_packages.add("requests")
    found_packages.add("python-dotenv")
    return sorted(found_packages)


# =============================================================================
# Project Discovery
# =============================================================================

def discover_project() -> dict:
    """Discover the Railway project/environment/dashboard from local config."""
    result = {
        "project_id": None,
        "environment_id": None,
        "dashboard_service_id": None,
        "dashboard_url": None,
    }

    # Source 1: workflow_config.json
    if WORKFLOW_CONFIG.exists():
        try:
            config = json.loads(WORKFLOW_CONFIG.read_text())
            result["project_id"] = config.get("project_id")
        except Exception:
            pass

    # Source 2: ~/.railway/config.json (always check for env/service/URL even if project_id found)
    railway_config_path = Path.home() / ".railway" / "config.json"
    if railway_config_path.exists():
        try:
            rc = json.loads(railway_config_path.read_text())
            projects = rc.get("projects", {})
            for path_key, info in projects.items():
                if "aiaa_dashboard" in path_key:
                    if not result["project_id"]:
                        result["project_id"] = info.get("project")
                    elif result["project_id"] != info.get("project"):
                        continue  # Different project, skip
                    if not result["environment_id"]:
                        result["environment_id"] = info.get("environment")
                    if not result["dashboard_service_id"]:
                        result["dashboard_service_id"] = info.get("service")
                    break
        except Exception:
            pass

    # Source 3: railway status from dashboard dir
    if not result["project_id"] and DASHBOARD_DIR.exists():
        code, stdout, stderr = run_command(["railway", "status", "--json"], cwd=str(DASHBOARD_DIR))
        if code == 0:
            try:
                status = json.loads(stdout)
                result["project_id"] = status.get("id")
                envs = status.get("environments", {}).get("edges", [])
                if envs:
                    env_node = envs[0]["node"]
                    result["environment_id"] = env_node.get("id")
                    instances = env_node.get("serviceInstances", {}).get("edges", [])
                    for inst in instances:
                        node = inst["node"]
                        if "dashboard" in node.get("serviceName", "").lower():
                            result["dashboard_service_id"] = node.get("serviceId")
                            domains = node.get("domains", {}).get("serviceDomains", [])
                            if domains:
                                result["dashboard_url"] = f"https://{domains[0]['domain']}"
            except Exception:
                pass

    # Discover dashboard URL if still missing
    if not result["dashboard_url"]:
        result["dashboard_url"] = _discover_dashboard_url(result)

    return result


def _discover_dashboard_url(project_info: dict) -> str:
    """Discover the dashboard URL from Railway CLI variables or API."""
    # Method 1: DASHBOARD_URL env var (explicit)
    env_url = os.getenv("DASHBOARD_URL", "")
    if env_url:
        return env_url

    # Method 2: Read RAILWAY_PUBLIC_DOMAIN from dashboard service variables
    if DASHBOARD_DIR.exists():
        code, stdout, stderr = run_command(
            ["railway", "variables", "--json", "--service", "aiaa-dashboard"],
            cwd=str(DASHBOARD_DIR),
        )
        if code == 0:
            try:
                variables = json.loads(stdout)
                domain = variables.get("RAILWAY_PUBLIC_DOMAIN", "")
                if domain:
                    return f"https://{domain}"
            except Exception:
                pass

    # Method 3: Query Railway API with the token
    token = _get_railway_token()
    if token and project_info.get("dashboard_service_id"):
        query = """
        query service($id: String!) {
            service(id: $id) {
                serviceInstances {
                    edges {
                        node {
                            domains {
                                serviceDomains { domain }
                            }
                        }
                    }
                }
            }
        }
        """
        try:
            data = json.dumps({"query": query, "variables": {"id": project_info["dashboard_service_id"]}}).encode()
            req = urllib.request.Request(RAILWAY_API_URL, data=data, method="POST")
            req.add_header("Authorization", f"Bearer {token}")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
            edges = result.get("data", {}).get("service", {}).get("serviceInstances", {}).get("edges", [])
            if edges:
                domains = edges[0]["node"].get("domains", {}).get("serviceDomains", [])
                if domains:
                    return f"https://{domains[0]['domain']}"
        except Exception:
            pass

    return ""


def _get_railway_token() -> str:
    """Get Railway API token from CLI config."""
    try:
        rc = json.loads((Path.home() / ".railway" / "config.json").read_text())
        return rc.get("user", {}).get("token", "")
    except Exception:
        return os.getenv("RAILWAY_API_TOKEN", "")


# =============================================================================
# Scaffold Templates
# =============================================================================

def scaffold_cron(name: str, parsed: dict, schedule: str) -> dict:
    """Generate files for a cron service."""
    scripts = parsed["execution_scripts"] or [name.replace("-", "_")]
    main_script = scripts[0]

    run_py = f'''#!/usr/bin/env python3
"""
Railway Cron: {name}
Auto-generated by deploy_to_railway.py

Runs: {schedule}
Script: execution/{main_script}.py
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    script = Path(__file__).parent / "{main_script}.py"
    if not script.exists():
        print(f"ERROR: Script not found: {{script}}")
        sys.exit(1)

    print(f"[CRON] Running {main_script}.py ...")
    result = subprocess.run(
        [sys.executable, str(script)],
        env={{**os.environ, "PYTHONPATH": str(Path(__file__).parent.parent)}},
    )
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
'''

    railway_json = json.dumps({
        "$schema": "https://railway.app/railway.schema.json",
        "build": {"builder": "NIXPACKS"},
        "deploy": {
            "startCommand": "python3 run.py",
            "restartPolicyType": "never",
            "cronSchedule": schedule,
        }
    }, indent=2)

    packages = scan_script_imports(main_script)
    requirements = "\n".join(packages) + "\n"

    return {
        "run.py": run_py,
        "railway.json": railway_json,
        "requirements.txt": requirements,
        f"{main_script}.py": (EXECUTION_DIR / f"{main_script}.py").read_text()
            if (EXECUTION_DIR / f"{main_script}.py").exists() else f"# {main_script}.py not found\n",
    }


def scaffold_web(name: str, parsed: dict) -> dict:
    """Generate files for a web service."""
    scripts = parsed["execution_scripts"] or [name.replace("-", "_")]
    main_script = scripts[0]
    description = parsed.get("description", name)

    app_py = f'''#!/usr/bin/env python3
"""
Railway Web Service: {name}
Auto-generated by deploy_to_railway.py
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/health")
def health():
    return jsonify({{"status": "healthy", "service": "{name}", "timestamp": datetime.utcnow().isoformat()}})

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json(silent=True) or {{}}
    input_data = payload.get("data", payload)

    args = []
    for key, value in input_data.items():
        if value is not None and value != "":
            args.extend([f"--{{key}}", str(value)])

    script = Path(__file__).parent / "{main_script}.py"
    if not script.exists():
        return jsonify({{"error": "Script not found"}}), 500

    try:
        result = subprocess.run(
            [sys.executable, str(script)] + args,
            capture_output=True, text=True, timeout=600,
            env={{**os.environ, "PYTHONPATH": str(Path(__file__).parent.parent)}},
        )
        return jsonify({{
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
        }})
    except subprocess.TimeoutExpired:
        return jsonify({{"error": "Script timed out"}}), 504
    except Exception as e:
        return jsonify({{"error": str(e)}}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
'''

    railway_json = json.dumps({
        "$schema": "https://railway.app/railway.schema.json",
        "build": {"builder": "NIXPACKS"},
        "deploy": {
            "startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --workers 1",
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 10,
        }
    }, indent=2)

    packages = scan_script_imports(main_script)
    packages_set = set(packages) | {"flask", "gunicorn"}
    requirements = "\n".join(sorted(packages_set)) + "\n"

    procfile = "web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --workers 1\n"

    files = {
        "app.py": app_py,
        "railway.json": railway_json,
        "requirements.txt": requirements,
        "Procfile": procfile,
    }

    script_path = EXECUTION_DIR / f"{main_script}.py"
    if script_path.exists():
        files[f"{main_script}.py"] = script_path.read_text()

    return files


# =============================================================================
# Deployment Actions
# =============================================================================

def set_railway_variables(variables: dict, service_dir: str, service_name: str) -> bool:
    """Set env vars per-service via CLI. Used only for service-specific vars (not API keys)."""
    print(f"  Setting {len(variables)} service-specific variables...")
    for key, value in variables.items():
        cmd = ["railway", "variable", "set", f"{key}={value}", "--service", service_name]
        code, stdout, stderr = run_command(cmd, cwd=service_dir)
        if code != 0:
            cmd_legacy = ["railway", "variables", "--set", f"{key}={value}", "--service", service_name]
            code, stdout, stderr = run_command(cmd_legacy, cwd=service_dir)
        if code != 0:
            print(f"    WARNING: Failed to set {key}: {stderr.strip()}")
        else:
            masked = f"{value[:4]}...{value[-4:]}" if len(value) > 10 else "***"
            print(f"    Set {key} = {masked}")
    return True


def sync_shared_variables(variables: dict, dashboard_url: str) -> bool:
    """Set API keys as project-level shared variables via the dashboard API.
    The dashboard runs inside Railway and can call the Railway GraphQL API.
    """
    if not dashboard_url or not variables:
        return False

    print(f"  Syncing {len(variables)} shared variables via dashboard...")

    # Login to dashboard
    session_cookie = _dashboard_login(dashboard_url)
    if not session_cookie:
        print("    WARNING: Could not login to dashboard -- falling back to per-service vars")
        return False

    # Call the shared-variables/sync endpoint
    try:
        payload = json.dumps({"variables": variables}).encode()
        req = urllib.request.Request(
            f"{dashboard_url}/api/shared-variables/sync",
            data=payload, method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("Cookie", f"session={session_cookie}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        if result.get("status") == "ok":
            print(f"    Synced {result.get('count', 0)} shared variables: {', '.join(result.get('keys', []))}")
            return True
        else:
            print(f"    WARNING: Shared var sync returned: {result}")
            return False
    except Exception as e:
        print(f"    WARNING: Shared var sync failed: {e}")
        return False


# Well-known API keys that should be shared across all services
SHARED_API_KEYS = {
    "OPENROUTER_API_KEY", "PERPLEXITY_API_KEY", "SLACK_WEBHOOK_URL",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "FAL_KEY", "APIFY_API_TOKEN",
    "INSTANTLY_API_KEY", "CALENDLY_API_KEY",
}


def set_cron_via_graphql(service_id: str, environment_id: str, schedule: str) -> bool:
    """Set cron schedule via Railway GraphQL API (more reliable than railway.json)."""
    token = _get_railway_token()
    if not token:
        print("  WARNING: No Railway token -- cannot set cron via API")
        return False

    query = """
    mutation serviceInstanceUpdate($serviceId: String!, $environmentId: String, $input: ServiceInstanceUpdateInput!) {
        serviceInstanceUpdate(serviceId: $serviceId, environmentId: $environmentId, input: $input)
    }
    """
    variables = {
        "serviceId": service_id,
        "environmentId": environment_id,
        "input": {"cronSchedule": schedule},
    }

    try:
        data = json.dumps({"query": query, "variables": variables}).encode()
        req = urllib.request.Request(RAILWAY_API_URL, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        if result.get("errors"):
            print(f"  WARNING: GraphQL cron error: {result['errors'][0].get('message', '')}")
            return False
        return True
    except Exception as e:
        print(f"  WARNING: Failed to set cron via API: {e}")
        return False


def get_new_service_id(project_id: str, service_name: str, service_dir: str = None) -> str:
    """Get the service ID for a deployed service."""
    # Method 1: railway status --json from the service directory (most reliable)
    cwd = service_dir or str(DASHBOARD_DIR)
    code, stdout, stderr = run_command(["railway", "status", "--json"], cwd=cwd)
    if code == 0:
        try:
            status = json.loads(stdout)
            edges = status.get("services", {}).get("edges", [])
            for edge in edges:
                if edge["node"]["name"] == service_name:
                    return edge["node"]["id"]
        except Exception:
            pass

    # Method 2: Railway GraphQL API
    token = _get_railway_token()
    if not token:
        return ""
    query = """
    query($projectId: String!) {
        project(id: $projectId) {
            services {
                edges {
                    node { id name }
                }
            }
        }
    }
    """
    try:
        data = json.dumps({"query": query, "variables": {"projectId": project_id}}).encode()
        req = urllib.request.Request(RAILWAY_API_URL, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        edges = result.get("data", {}).get("project", {}).get("services", {}).get("edges", [])
        for edge in edges:
            if edge["node"]["name"] == service_name:
                return edge["node"]["id"]
    except Exception:
        pass
    return ""


def register_in_workflow_config(service_id: str, name: str, description: str) -> bool:
    """Add the new service to workflow_config.json for dashboard display."""
    if not WORKFLOW_CONFIG.exists():
        return False
    try:
        config = json.loads(WORKFLOW_CONFIG.read_text())
        config.setdefault("workflows", {})[service_id] = {
            "name": name,
            "description": description,
            "enabled": True,
        }
        WORKFLOW_CONFIG.write_text(json.dumps(config, indent=2) + "\n")
        return True
    except Exception as e:
        print(f"  WARNING: Could not update workflow_config.json: {e}")
        return False


# =============================================================================
# Webhook Registration (via dashboard API)
# =============================================================================

def register_dashboard_webhook(directive_name: str, parsed: dict, slug: str,
                               slack_notify: bool, forward_url: str,
                               dashboard_url: str) -> bool:
    """Register a webhook on the dashboard for visibility and forwarding."""
    if not dashboard_url:
        print("  WARNING: No dashboard URL -- skipping webhook registration")
        return False

    if not slug:
        slug = directive_name.replace("_", "-")

    description = parsed.get("description", directive_name)
    name = directive_name.replace("_", " ").replace("-", " ").title()

    payload = {
        "slug": slug,
        "name": name,
        "description": description,
        "source": "Railway Deploy Script",
        "slack_notify": slack_notify,
    }
    if forward_url:
        payload["forward_url"] = forward_url

    print(f"\n  Registering webhook '{slug}' on dashboard...")
    session = _dashboard_login(dashboard_url)
    if not session:
        print("  WARNING: Could not authenticate with dashboard -- skipping webhook registration")
        print("  Set DASHBOARD_PASSWORD env var to enable auto-registration")
        return False

    result = _dashboard_api(dashboard_url, "/api/webhook-workflows/register", data=payload, session=session)
    if result.get("status") in (200, 201):
        webhook_url = result.get("data", {}).get("webhook_url", f"{dashboard_url}/webhook/{slug}")
        print(f"  Webhook registered: {webhook_url}")
        if forward_url:
            print(f"  Forwards to: {forward_url}")
        return True
    else:
        error = result.get("data", {}).get("error", "Unknown error")
        print(f"  WARNING: Webhook registration failed: {error}")
        return False


def _dashboard_login(dashboard_url: str) -> str:
    """Login to the dashboard and return session cookie."""
    username = os.getenv("DASHBOARD_USERNAME", "admin")
    password = os.getenv("DASHBOARD_PASSWORD", "")
    if not password:
        # Also check .env file
        local_env = get_env_vars_from_dotenv()
        password = local_env.get("DASHBOARD_PASSWORD", "")
        username = local_env.get("DASHBOARD_USERNAME", username)
    if not password:
        print("  WARNING: DASHBOARD_PASSWORD not set in environment or .env")
        return ""

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    login_data = urllib.parse.urlencode({"username": username, "password": password}).encode()
    try:
        req = urllib.request.Request(f"{dashboard_url}/login", data=login_data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        opener.open(req, timeout=10)
        for cookie in cj:
            if cookie.name == "session":
                return cookie.value
    except Exception as e:
        print(f"  Login error: {e}")
    return ""


def _dashboard_api(dashboard_url: str, endpoint: str, data: dict = None, session: str = "") -> dict:
    """Make an authenticated API request to the dashboard."""
    url = f"{dashboard_url}{endpoint}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    if session:
        req.add_header("Cookie", f"session={session}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"status": resp.status, "data": json.loads(resp.read())}
    except urllib.error.HTTPError as e:
        try:
            body_data = json.loads(e.read())
        except Exception:
            body_data = {"error": str(e)}
        return {"status": e.code, "data": body_data}
    except Exception as e:
        return {"status": 0, "data": {"error": str(e)}}


# =============================================================================
# Service Domain Discovery
# =============================================================================

def get_service_domain(service_dir: str, service_name: str) -> str:
    """Get or generate a public domain for a Railway service."""
    # Try to get existing domain
    code, stdout, stderr = run_command(
        ["railway", "domain", "--json"],
        cwd=service_dir,
    )
    if code == 0 and stdout.strip():
        try:
            domain_data = json.loads(stdout)
            if isinstance(domain_data, list) and domain_data:
                return domain_data[0].get("domain", "")
            elif isinstance(domain_data, dict):
                return domain_data.get("domain", "")
        except Exception:
            domain = stdout.strip().replace("https://", "").replace("http://", "")
            if "." in domain:
                return domain

    # Generate a new domain
    code, stdout, stderr = run_command(
        ["railway", "domain"],
        cwd=service_dir,
    )
    if code == 0 and stdout.strip():
        domain = stdout.strip().replace("https://", "").replace("http://", "")
        if "." in domain:
            return domain

    return ""


# =============================================================================
# Main Deploy Pipeline
# =============================================================================

def deploy_service(directive_name: str, parsed: dict, deploy_type: str,
                   schedule: str, slug: str, slack_notify: bool,
                   forward_url: str, project_info: dict,
                   dry_run: bool, auto: bool) -> int:
    """Deploy any workflow as a standalone Railway service.

    All types (cron, webhook, web) get a standalone service.
    Webhook types additionally get registered on the dashboard for visibility.
    """
    project_id = project_info.get("project_id")
    environment_id = project_info.get("environment_id")
    dashboard_url = project_info.get("dashboard_url", "")

    if not project_id:
        print("  ERROR: No Railway project found. Deploy your dashboard first.")
        print("  Run: python3 execution/deploy_aiaa_dashboard.py")
        return 1

    service_name = directive_name.replace("_", "-")
    service_dir = RAILWAY_APPS_DIR / service_name

    # Scaffold files -- cron gets run.py, webhook/web get Flask app
    scaffold_type = "cron" if deploy_type == "cron" else "web"
    print(f"\n  Scaffolding {deploy_type} service: {service_name}")
    if scaffold_type == "cron":
        if not schedule:
            print("  ERROR: --schedule required for cron type (e.g. '0 */3 * * *')")
            return 1
        files = scaffold_cron(service_name, parsed, schedule)
    else:
        files = scaffold_web(service_name, parsed)

    if dry_run:
        print(f"\n  [DRY RUN] Would create {service_dir}/")
        for fname, content in files.items():
            lines = content.count("\n")
            print(f"    {fname} ({lines} lines)")
        print(f"\n  Would deploy to project: {project_id}")
        print(f"  Service name: {service_name}")
        if deploy_type == "cron":
            print(f"  Cron schedule: {schedule}")
        if deploy_type == "webhook":
            wh_slug = slug or directive_name.replace("_", "-")
            print(f"  Webhook slug: {wh_slug}")
            print(f"  Dashboard webhook: {dashboard_url}/webhook/{wh_slug} -> https://<service-domain>/webhook")
        env_keys = get_required_env_keys(parsed)
        if env_keys:
            print(f"  Env vars: {', '.join(env_keys)}")
        return 0

    # Create directory and write files
    service_dir.mkdir(parents=True, exist_ok=True)
    for fname, content in files.items():
        (service_dir / fname).write_text(content)
        print(f"    Created: {service_dir / fname}")

    # Link to project
    print(f"\n  Linking to project {project_id}...")
    code, stdout, stderr = run_command(
        ["railway", "link", "-p", project_id],
        cwd=str(service_dir),
    )
    if code != 0:
        print(f"  WARNING: Link returned: {stderr.strip()}")

    # Create the service if it doesn't exist (railway add --service <name>)
    print(f"\n  Creating service '{service_name}'...")
    code, stdout, stderr = run_command(
        ["railway", "add", "--service", service_name, "--json"],
        cwd=str(service_dir),
    )
    if code != 0 and "already exists" not in stderr.lower():
        print(f"  Note: {stderr.strip() or 'Service may already exist'}")

    # Link the new service so railway up targets it
    run_command(
        ["railway", "service", "link", service_name],
        cwd=str(service_dir),
    )

    # Deploy
    print(f"\n  Deploying service '{service_name}'...")
    code, stdout, stderr = run_command(
        ["railway", "up", "--detach", "--service", service_name],
        cwd=str(service_dir),
    )
    if code != 0:
        print(f"  ERROR: Deploy failed: {stderr.strip()}")
        return 1
    print("  Deploy initiated. Waiting for build...")
    time.sleep(15)

    # Set environment variables
    # Split into shared (API keys) and service-specific vars
    env_keys = get_required_env_keys(parsed)
    local_env = get_env_vars_from_dotenv()
    vars_to_set = {k: local_env[k] for k in env_keys if k in local_env}

    # Always include GOOGLE_OAUTH_TOKEN_PICKLE for Google integrations
    google_integrations = {"google_docs", "google_sheets", "gmail"}
    if google_integrations & set(parsed["integrations"]):
        token_pickle = PROJECT_ROOT / "token.pickle"
        if token_pickle.exists():
            import base64
            encoded = base64.b64encode(token_pickle.read_bytes()).decode()
            vars_to_set["GOOGLE_OAUTH_TOKEN_PICKLE"] = encoded

    # Sync API keys as project-level shared variables (all services inherit them)
    shared_vars = {k: v for k, v in vars_to_set.items() if k in SHARED_API_KEYS}
    service_vars = {k: v for k, v in vars_to_set.items() if k not in SHARED_API_KEYS}

    if shared_vars and dashboard_url:
        synced = sync_shared_variables(shared_vars, dashboard_url)
        if not synced:
            # Fallback: set as per-service vars
            service_vars.update(shared_vars)

    if service_vars:
        set_railway_variables(service_vars, str(service_dir), service_name)

    # Get service ID for the new service
    new_service_id = get_new_service_id(project_id, service_name, str(service_dir))

    # Type-specific post-deploy steps
    service_domain = ""

    if deploy_type == "cron" and new_service_id and environment_id:
        # Confirm cron schedule via GraphQL (more reliable than railway.json)
        print(f"\n  Setting cron schedule: {schedule}")
        if set_cron_via_graphql(new_service_id, environment_id, schedule):
            print("  Cron schedule confirmed via API")
        else:
            print("  WARNING: Cron set via railway.json only -- verify in dashboard")

    if deploy_type in ("webhook", "web"):
        # Get public domain for the service
        print("\n  Getting public domain...")
        service_domain = get_service_domain(str(service_dir), service_name)
        if service_domain:
            print(f"  Domain: https://{service_domain}")
        else:
            print("  WARNING: Could not get domain -- generate manually: railway domain")

    if deploy_type == "webhook" and dashboard_url:
        # Register webhook on dashboard with forward_url pointing to this service
        service_url = f"https://{service_domain}/webhook" if service_domain else forward_url or ""
        actual_forward = forward_url or service_url
        if actual_forward:
            register_dashboard_webhook(
                directive_name, parsed, slug, slack_notify,
                actual_forward, dashboard_url,
            )
        else:
            print("  WARNING: No service URL available -- register webhook manually on dashboard")

    # Register in workflow_config.json for dashboard display
    if new_service_id:
        description = parsed.get("description", directive_name)
        friendly_name = directive_name.replace("_", " ").replace("-", " ").title()
        if register_in_workflow_config(new_service_id, friendly_name, description):
            print(f"\n  Registered in workflow_config.json (service ID: {new_service_id})")
            print("  NOTE: Redeploy dashboard to update friendly name in UI")
            if deploy_type == "cron":
                print("  Cron services auto-appear in dashboard even without config entry")
    else:
        print("\n  WARNING: Could not find service ID -- register manually in workflow_config.json")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  Deployed: {service_name}")
    print(f"  Type:     {deploy_type}")
    print(f"  Project:  {project_id}")
    if new_service_id:
        print(f"  Service:  {new_service_id}")
    if deploy_type == "cron":
        print(f"  Schedule: {schedule}")
    if service_domain:
        print(f"  URL:      https://{service_domain}")
        if deploy_type == "webhook":
            print(f"  Webhook:  https://{service_domain}/webhook")
    if deploy_type == "webhook" and dashboard_url:
        wh_slug = slug or directive_name.replace("_", "-")
        print(f"  Dashboard: {dashboard_url}/webhook/{wh_slug}")
    print(f"{'=' * 60}\n")
    return 0


# =============================================================================
# CLI
# =============================================================================

def show_info(directive_name: str):
    """Show info about a directive's deployment requirements."""
    content = load_directive(directive_name)
    parsed = parse_directive(content)
    detected_type = detect_type(content)
    env_keys = get_required_env_keys(parsed)
    project = discover_project()

    print(f"\n  Directive: {directive_name}")
    print(f"  Description: {parsed['description'][:100]}")
    print(f"  Detected Type: {detected_type}")
    print(f"  Scripts: {', '.join(parsed['execution_scripts']) or 'None found'}")
    print(f"  Integrations: {', '.join(parsed['integrations']) or 'None'}")
    print(f"  Required Env Vars: {', '.join(env_keys) or 'None'}")
    print(f"  Uses LLM: {'Yes' if parsed['has_llm'] else 'No'}")
    print(f"\n  Railway Project: {project.get('project_id', 'NOT FOUND')}")
    print(f"  Dashboard URL: {project.get('dashboard_url', 'NOT FOUND')}")

    local_env = get_env_vars_from_dotenv()
    missing = [k for k in env_keys if k not in local_env]
    if missing:
        print(f"\n  WARNING: Missing from .env: {', '.join(missing)}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Deploy any AIAA workflow to Railway")
    parser.add_argument("--directive", "-d", help="Directive name (without .md)")
    parser.add_argument("--type", "-t", choices=["cron", "webhook", "web"], help="Service type (auto-detected if omitted)")
    parser.add_argument("--schedule", "-s", help="Cron schedule (e.g. '0 */3 * * *')")
    parser.add_argument("--slug", help="Webhook URL slug (webhook type only)")
    parser.add_argument("--forward-url", "-f", help="URL to forward webhook payloads to")
    parser.add_argument("--slack-notify", action="store_true", help="Enable Slack notifications (webhook type)")
    parser.add_argument("--auto", action="store_true", help="Fully automated, no prompts")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without doing it")
    parser.add_argument("--list", "-l", action="store_true", help="List all deployable directives")
    parser.add_argument("--info", "-i", action="store_true", help="Show deployment info for a directive")

    args = parser.parse_args()

    # List mode
    if args.list:
        directives = list_directives()
        print(f"\n  Deployable directives ({len(directives)}):\n")
        for d in directives:
            print(f"    {d}")
        print()
        return 0

    if not args.directive:
        parser.print_help()
        return 1

    # Info mode
    if args.info:
        try:
            show_info(args.directive)
        except FileNotFoundError as e:
            print(f"  ERROR: {e}")
            return 1
        return 0

    # Deploy mode
    print("\n" + "=" * 60)
    print("  AIAA Railway Deployment")
    print("=" * 60)

    try:
        content = load_directive(args.directive)
    except FileNotFoundError as e:
        print(f"  ERROR: {e}")
        return 1

    parsed = parse_directive(content)
    deploy_type = args.type or detect_type(content)
    print(f"\n  Directive:  {args.directive}")
    print(f"  Type:       {deploy_type}")
    print(f"  Description: {parsed['description'][:80]}")

    # Check Railway CLI
    code, _, _ = run_command(["railway", "--version"])
    if code != 0:
        print("  ERROR: Railway CLI not installed. Run: brew install railway && railway login")
        return 1

    # Discover project
    print("\n  Discovering Railway project...")
    project_info = discover_project()
    if project_info.get("project_id"):
        print(f"  Project: {project_info['project_id']}")
    else:
        print("  ERROR: No Railway project found. Deploy your dashboard first.")
        return 1

    if project_info.get("dashboard_url"):
        print(f"  Dashboard: {project_info['dashboard_url']}")

    # Deploy (all types get a standalone service)
    return deploy_service(
        args.directive, parsed, deploy_type, args.schedule,
        args.slug, args.slack_notify, args.forward_url,
        project_info, args.dry_run, args.auto,
    )


if __name__ == "__main__":
    sys.exit(main())
