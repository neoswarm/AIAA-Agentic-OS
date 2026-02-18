#!/usr/bin/env python3
"""
Hook 53: deployment_rollback_tracker.py (PostToolUse on Bash)
After railway up/deploy, logs deployment history for rollback reference.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "deployment_history.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"deployments": [], "total": 0, "successes": 0, "failures": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def show_status():
    state = load_state()
    total = state.get("total", 0)
    successes = state.get("successes", 0)
    failures = state.get("failures", 0)
    print("=== Deployment Rollback Tracker ===")
    print(f"Total deployments: {total}")
    print(f"Successes: {successes}")
    print(f"Failures: {failures}")
    if total > 0:
        print(f"Success rate: {successes / total * 100:.1f}%")
    deployments = state.get("deployments", [])
    if deployments:
        print("\nRecent deployments:")
        for d in deployments[-10:]:
            status = "SUCCESS" if d.get("success") else "FAILED"
            print(f"  [{status}] {d.get('timestamp', '?')} - {d.get('service', '?')} ({d.get('command_type', '?')})")
    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("State reset.")
    sys.exit(0)


def extract_service_name(command):
    """Extract service name from railway command."""
    match = re.search(r'--service\s+["\']?(\S+)', command)
    if match:
        return match.group(1).strip("\"'")
    # Try to detect from directory
    cd_match = re.search(r'cd\s+["\']?([^"\';&]+)', command)
    if cd_match:
        path = cd_match.group(1).strip()
        parts = path.rstrip("/").split("/")
        return parts[-1] if parts else "unknown"
    return "unknown"


def determine_success(tool_result):
    """Parse tool_result to determine if deployment succeeded."""
    if not tool_result:
        return False
    result_lower = str(tool_result).lower()
    failure_indicators = [
        "error", "failed", "failure", "traceback", "exception",
        "denied", "unauthorized", "not found", "timeout"
    ]
    success_indicators = [
        "deploy", "success", "complete", "done", "live",
        "running", "active", "healthy"
    ]
    has_failure = any(ind in result_lower for ind in failure_indicators)
    has_success = any(ind in result_lower for ind in success_indicators)
    if has_failure and not has_success:
        return False
    return True


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
    tool_result = data.get("tool_result", "")

    if tool_name not in ("Bash", "bash"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    if not ("railway up" in command or "railway deploy" in command):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()

    service = extract_service_name(command)
    success = determine_success(tool_result)

    command_type = "up" if "railway up" in command else "deploy"

    deployment = {
        "timestamp": now,
        "service": service,
        "command_type": command_type,
        "command": command[:200],
        "success": success
    }

    state["deployments"].append(deployment)
    state["deployments"] = state["deployments"][-50:]
    state["total"] = state.get("total", 0) + 1
    if success:
        state["successes"] = state.get("successes", 0) + 1
    else:
        state["failures"] = state.get("failures", 0) + 1

    save_state(state)

    status_str = "succeeded" if success else "may have failed"
    print(json.dumps({
        "decision": "ALLOW",
        "reason": f"Deployment of '{service}' {status_str}. Logged to deployment history."
    }))


if __name__ == "__main__":
    main()
