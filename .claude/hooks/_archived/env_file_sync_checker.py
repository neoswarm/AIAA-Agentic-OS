#!/usr/bin/env python3
"""
Hook 39: Env File Sync Checker (PreToolUse on Bash)

Before `railway up` or `railway deploy` commands:
- Read local .env file and list all keys
- Cross-reference required variables
- WARN which keys exist locally but may not be set in Railway
- Also warn if Railway-specific vars are missing

Exit 0 always.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "env_sync_log.json"
ENV_FILE = PROJECT_ROOT / ".env"

# Required for Railway deployment
RAILWAY_REQUIRED = [
    "DASHBOARD_USERNAME",
    "DASHBOARD_PASSWORD_HASH",
    "FLASK_SECRET_KEY",
]

# API keys that should be synced to Railway
API_KEYS_TO_SYNC = [
    "OPENROUTER_API_KEY",
    "PERPLEXITY_API_KEY",
    "ANTHROPIC_API_KEY",
    "SLACK_WEBHOOK_URL",
    "FAL_KEY",
    "APIFY_API_TOKEN",
    "OPENAI_API_KEY",
    "RAILWAY_API_TOKEN",
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": [], "stats": {"total": 0, "warnings": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def read_env_keys():
    """Read all keys from .env file."""
    keys = set()
    if not ENV_FILE.exists():
        return keys

    try:
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key = line.split("=", 1)[0].strip()
                    if key:
                        keys.add(key)
    except OSError:
        pass

    return keys


def is_railway_deploy(command):
    """Check if this is a Railway deployment command."""
    deploy_patterns = [
        r'railway\s+up',
        r'railway\s+deploy',
        r'railway\s+redeploy',
    ]
    for pattern in deploy_patterns:
        if re.search(pattern, command):
            return True
    return False


def handle_status():
    state = load_state()
    print("=== Env File Sync Checker Status ===")
    print(f"State file: {STATE_FILE}")
    print(f".env file: {ENV_FILE}")
    print(f".env exists: {ENV_FILE.exists()}")

    local_keys = read_env_keys()
    if local_keys:
        print(f"\nLocal .env keys ({len(local_keys)}):")
        for key in sorted(local_keys):
            print(f"  {key}")
    else:
        print("\nNo keys found in .env")

    print(f"\nRailway-required variables:")
    for var in RAILWAY_REQUIRED:
        status = "IN .env" if var in local_keys else "NOT IN .env"
        print(f"  {var}: {status}")

    print(f"\nAPI keys to sync:")
    for var in API_KEYS_TO_SYNC:
        status = "IN .env" if var in local_keys else "NOT IN .env"
        print(f"  {var}: {status}")

    stats = state.get("stats", {})
    print(f"\nDeploy checks: {stats.get('total', 0)}")
    print(f"Warnings: {stats.get('warnings', 0)}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Env file sync checker state reset.")
    else:
        print("No state file to reset.")


def main():
    if "--status" in sys.argv:
        handle_status()
        return
    if "--reset" in sys.argv:
        handle_reset()
        return

    # PreToolUse mode
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")

    if not is_railway_deploy(command):
        sys.exit(0)

    state = load_state()
    state["stats"]["total"] = state["stats"].get("total", 0) + 1

    local_keys = read_env_keys()
    warnings = []

    # Check Railway-specific required variables
    for var in RAILWAY_REQUIRED:
        if var not in local_keys:
            warnings.append(f"Railway-required '{var}' not in .env (set via `railway variables set`)")

    # Check API keys that exist locally but might not be in Railway
    local_api_keys = [k for k in API_KEYS_TO_SYNC if k in local_keys]
    if local_api_keys:
        warnings.append(
            f"Ensure these local API keys are set in Railway: "
            f"{', '.join(local_api_keys)}"
        )

    if not ENV_FILE.exists():
        warnings.append("No .env file found! Create one with required API keys.")

    check_record = {
        "command": command[:80],
        "warnings": warnings,
        "local_keys_count": len(local_keys),
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_record)
    state["checks"] = state["checks"][-20:]

    if warnings:
        state["stats"]["warnings"] = state["stats"].get("warnings", 0) + 1
        save_state(state)
        sys.stderr.write(
            "[ENV SYNC] Railway deployment detected. " +
            " | ".join(warnings) + "\n"
        )
    else:
        save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
