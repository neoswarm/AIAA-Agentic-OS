#!/usr/bin/env python3
"""
Hook 51: railway_env_var_completeness.py (PreToolUse on Bash)
Before railway up/deploy, checks if required environment variables are likely set.
"""

import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "railway_env_checks.json"

# Required vars by service type
SERVICE_VARS = {
    "dashboard": [
        "DASHBOARD_USERNAME", "DASHBOARD_PASSWORD_HASH",
        "FLASK_SECRET_KEY", "RAILWAY_API_TOKEN"
    ],
    "workflow": [
        "OPENROUTER_API_KEY", "SLACK_WEBHOOK_URL"
    ],
    "research": [
        "OPENROUTER_API_KEY", "PERPLEXITY_API_KEY", "SLACK_WEBHOOK_URL"
    ],
    "scraping": [
        "OPENROUTER_API_KEY", "APIFY_API_TOKEN", "SLACK_WEBHOOK_URL"
    ],
    "google": [
        "OPENROUTER_API_KEY", "GOOGLE_OAUTH_TOKEN_PICKLE", "SLACK_WEBHOOK_URL"
    ]
}

SERVICE_DETECTION = {
    "aiaa_dashboard": "dashboard",
    "aiaa-dashboard": "dashboard",
    "dashboard": "dashboard",
    "research": "research",
    "scrape": "scraping",
    "google": "google",
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": [], "warnings_issued": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def load_env_keys():
    """Read .env file and return list of defined keys."""
    env_path = Path(".env")
    keys = set()
    if env_path.exists():
        try:
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key = line.split("=", 1)[0].strip()
                    keys.add(key)
        except OSError:
            pass
    # Also check environment
    for key in os.environ:
        keys.add(key)
    return keys


def detect_service_type(command):
    """Detect service type from command or directory."""
    # Check --service flag
    service_match = re.search(r'--service\s+["\']?(\S+)', command)
    if service_match:
        service_name = service_match.group(1).strip("\"'")
        for pattern, stype in SERVICE_DETECTION.items():
            if pattern in service_name.lower():
                return stype, service_name

    # Check cd path in command
    cd_match = re.search(r'cd\s+["\']?([^"\';&]+)', command)
    if cd_match:
        cd_path = cd_match.group(1).strip()
        for pattern, stype in SERVICE_DETECTION.items():
            if pattern in cd_path.lower():
                return stype, cd_path

    return "workflow", "unknown"


def show_status():
    state = load_state()
    env_keys = load_env_keys()
    print("=== Railway Env Var Completeness ===")
    print(f"Checks performed: {len(state.get('checks', []))}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    print(f"\nLocal .env keys found: {len(env_keys)}")
    print("\nRequired vars by service type:")
    for stype, vars_list in SERVICE_VARS.items():
        print(f"\n  {stype}:")
        for v in vars_list:
            status = "found" if v in env_keys else "MISSING"
            print(f"    {v}: {status}")
    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("State reset.")
    sys.exit(0)


def main():
    if "--status" in sys.argv:
        show_status()
    if "--reset" in sys.argv:
        reset_state()

    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Bash", "bash"):
        sys.exit(0)

    command = tool_input.get("command", "")
    if not ("railway up" in command or "railway deploy" in command):
        sys.exit(0)

    state = load_state()
    now = datetime.now().isoformat()

    service_type, service_name = detect_service_type(command)
    required_vars = SERVICE_VARS.get(service_type, SERVICE_VARS["workflow"])
    env_keys = load_env_keys()

    missing = [v for v in required_vars if v not in env_keys]

    check_entry = {
        "timestamp": now,
        "service_type": service_type,
        "service_name": service_name,
        "missing_vars": missing
    }
    state["checks"].append(check_entry)
    state["checks"] = state["checks"][-50:]

    if missing:
        state["warnings_issued"] = state.get("warnings_issued", 0) + 1
        sys.stderr.write(f"[railway-env-check] Deploying '{service_name}' (type: {service_type})\n")
        sys.stderr.write(f"  Potentially missing environment variables:\n")
        for v in missing:
            sys.stderr.write(f"    - {v}\n")
        sys.stderr.write(f"  Set via: railway variables set {missing[0]}=\"value\"\n")
    else:
        sys.stderr.write(f"[railway-env-check] All required vars for '{service_type}' appear available.\n")

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
