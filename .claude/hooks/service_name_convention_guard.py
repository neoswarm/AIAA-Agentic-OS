#!/usr/bin/env python3
"""
Hook 54: service_name_convention_guard.py (PreToolUse on Bash)
Validates Railway service name conventions (lowercase, hyphens only).
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "service_name_checks.json"

KNOWN_SERVICES = ["aiaa-dashboard"]


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


def show_status():
    state = load_state()
    print("=== Service Name Convention Guard ===")
    print(f"Names checked: {len(state.get('checks', []))}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    print(f"Known services: {', '.join(KNOWN_SERVICES)}")
    checks = state.get("checks", [])
    if checks:
        print("\nRecent checks:")
        for c in checks[-10:]:
            status = "WARN" if c.get("issues") else "OK"
            print(f"  [{status}] '{c.get('name', '?')}' - {c.get('message', '')}")
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
    if "railway up" not in command and "railway deploy" not in command:
        sys.exit(0)

    # Extract --service name
    match = re.search(r'--service\s+["\']?(\S+)', command)
    if not match:
        sys.exit(0)

    service_name = match.group(1).strip("\"'")
    state = load_state()
    now = datetime.now().isoformat()
    issues = []

    # Check lowercase
    if service_name != service_name.lower():
        issues.append("Service name should be lowercase")

    # Check for underscores
    if "_" in service_name:
        issues.append("Use hyphens instead of underscores")

    # Check for spaces
    if " " in service_name:
        issues.append("Service name should not contain spaces")

    # Check for valid characters (lowercase alphanumeric and hyphens)
    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', service_name) and len(service_name) > 1:
        if not re.match(r'^[a-z0-9]$', service_name):
            issues.append("Service name should only contain lowercase letters, numbers, and hyphens")

    # Check against known services
    if service_name not in KNOWN_SERVICES:
        issues.append(f"Unknown service name. Known: {', '.join(KNOWN_SERVICES)}")

    check_entry = {
        "timestamp": now,
        "name": service_name,
        "issues": issues,
        "message": "; ".join(issues) if issues else "Valid service name"
    }
    state["checks"].append(check_entry)
    state["checks"] = state["checks"][-50:]

    if issues:
        state["warnings_issued"] = state.get("warnings_issued", 0) + 1
        sys.stderr.write(f"[service-name-guard] Issues with service name '{service_name}':\n")
        for issue in issues:
            sys.stderr.write(f"  - {issue}\n")

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
