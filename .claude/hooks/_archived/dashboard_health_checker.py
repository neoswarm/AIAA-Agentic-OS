#!/usr/bin/env python3
"""
Hook 56: dashboard_health_checker.py (PostToolUse on Bash)
After dashboard deployment, reminds to verify health and logs the deployment.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "dashboard_deploys.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"deploys": [], "total": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def show_status():
    state = load_state()
    print("=== Dashboard Health Checker ===")
    print(f"Total dashboard deployments: {state.get('total', 0)}")
    deploys = state.get("deploys", [])
    if deploys:
        print("\nRecent dashboard deployments:")
        for d in deploys[-10:]:
            print(f"  [{d.get('timestamp', '?')}] {d.get('command', '?')[:80]}")
    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("State reset.")
    sys.exit(0)


def is_dashboard_deploy(command):
    """Check if this is a dashboard deployment command."""
    indicators = [
        "aiaa-dashboard",
        "aiaa_dashboard",
        "dashboard",
    ]
    if "railway up" in command or "railway deploy" in command:
        # Check for service flag with dashboard
        service_match = re.search(r'--service\s+["\']?(\S+)', command)
        if service_match:
            service = service_match.group(1).strip("\"'").lower()
            return any(ind in service for ind in indicators)
        # Check for cd to dashboard directory
        if "dashboard" in command.lower():
            return True
    return False


def main():
    if "--status" in sys.argv:
        show_status()
    if "--reset" in sys.argv:
        reset_state()

    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Bash", "bash"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    if not is_dashboard_deploy(command):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()

    deploy_entry = {
        "timestamp": now,
        "command": command[:200]
    }
    state["deploys"].append(deploy_entry)
    state["deploys"] = state["deploys"][-50:]
    state["total"] = state.get("total", 0) + 1
    save_state(state)

    print(json.dumps({
        "decision": "ALLOW",
        "reason": (
            "Dashboard deployed. Verify health: "
            "curl https://your-dashboard.up.railway.app/health | "
            "Check Active Workflows page loads correctly."
        )
    }))


if __name__ == "__main__":
    main()
