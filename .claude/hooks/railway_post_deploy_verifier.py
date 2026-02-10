#!/usr/bin/env python3
"""
Hook 127: railway_post_deploy_verifier.py (PostToolUse on Bash)
After Railway deploy, outputs verification steps including health check, logs, and webhook test.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "railway_post_deploy.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"deploys": [], "total": 0, "successes": 0, "failures": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def show_status():
    state = load_state()
    total = state.get("total", 0)
    successes = state.get("successes", 0)
    failures = state.get("failures", 0)
    print("=== Railway Post-Deploy Verifier ===")
    print(f"Total deployments: {total}")
    print(f"Successes: {successes}")
    print(f"Failures: {failures}")
    if total > 0:
        print(f"Success rate: {successes / total * 100:.1f}%")
    deploys = state.get("deploys", [])
    if deploys:
        print("\nRecent deployments:")
        for d in deploys[-10:]:
            status = "SUCCESS" if d.get("success") else "FAILED"
            url = d.get("url", "no URL")
            print(f"  [{status}] {d.get('timestamp', '?')} - {d.get('service', '?')} ({url})")
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
    # Try to detect from cd path
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

    tool_result_str = str(tool_result)
    state = load_state()
    now = datetime.now().isoformat()

    service = extract_service_name(command)
    success = determine_success(tool_result_str)

    # Extract Railway URL from result
    url_match = re.search(r'https://\S+\.up\.railway\.app', tool_result_str)
    url = url_match.group(0) if url_match else ""

    deploy_entry = {
        "timestamp": now,
        "service": service,
        "success": success,
        "url": url,
        "command": command[:200]
    }

    state["deploys"].append(deploy_entry)
    state["deploys"] = state["deploys"][-50:]
    state["total"] = state.get("total", 0) + 1
    if success:
        state["successes"] = state.get("successes", 0) + 1
    else:
        state["failures"] = state.get("failures", 0) + 1

    save_state(state)

    # Build verification reason
    if success and url:
        reason = (
            f"Railway deploy of '{service}' succeeded.\n"
            f"HEALTH: curl {url}/health\n"
            f"LOGS:   railway logs --service {service}\n"
            f"TEST:   curl -X POST '{url}/webhook/test' -H 'Content-Type: application/json' -d '{{\"message\":\"test\"}}'"
        )
    elif success and not url:
        reason = (
            f"Railway deploy of '{service}' succeeded but no public URL detected.\n"
            f"Run `railway domain` to generate a public domain.\n"
            f"LOGS: railway logs --service {service}"
        )
    else:
        reason = (
            f"Railway deploy of '{service}' may have failed.\n"
            f"CHECK: railway logs --service {service}\n"
            f"TRY:   railway login\n"
            f"TRY:   railway link"
        )

    print(json.dumps({"decision": "ALLOW", "reason": reason}))


if __name__ == "__main__":
    main()
