#!/usr/bin/env python3
"""
Hook 126: modal_health_verifier.py (PostToolUse on Bash)
After Modal deploy, outputs verification curl commands for health and webhook endpoints.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "modal_health_endpoints.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"endpoints": [], "total": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def show_status():
    state = load_state()
    print("=== Modal Health Verifier ===")
    print(f"Total endpoints tracked: {state.get('total', 0)}")
    endpoints = state.get("endpoints", [])
    if endpoints:
        print("\nTracked endpoints:")
        for ep in endpoints[-10:]:
            verified = "VERIFIED" if ep.get("verified") else "UNVERIFIED"
            print(f"  [{verified}] {ep.get('timestamp', '?')} - {ep.get('app_name', '?')}")
            if ep.get("health_url"):
                print(f"    Health:  {ep['health_url']}")
            if ep.get("webhook_url"):
                print(f"    Webhook: {ep['webhook_url']}")
    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("State reset.")
    sys.exit(0)


def extract_app_name(command):
    """Extract app name from modal deploy command."""
    match = re.search(r'modal\s+deploy\s+\S*/(\w+)\.py', command)
    if match:
        return match.group(1)
    match = re.search(r'modal\s+deploy\s+(\w+)\.py', command)
    if match:
        return match.group(1)
    return "unknown"


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
    tool_result_str = str(tool_result)

    # Trigger: command contains "modal deploy" AND tool_result contains ".modal.run"
    if "modal deploy" not in command or ".modal.run" not in tool_result_str:
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Extract all Modal URLs
    all_urls = re.findall(r'https://\S+\.modal\.run', tool_result_str)
    if not all_urls:
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Categorize URLs
    webhook_urls = [u for u in all_urls if "-webhook" in u]
    health_urls = [u for u in all_urls if "-health" in u]
    other_urls = [u for u in all_urls if "-webhook" not in u and "-health" not in u]

    # If no health URL but webhook URL exists, derive one
    if not health_urls and webhook_urls:
        derived = webhook_urls[0].replace("-webhook.modal.run", "-health.modal.run")
        health_urls.append(derived)

    app_name = extract_app_name(command)
    now = datetime.now().isoformat()

    health_url = health_urls[0] if health_urls else ""
    webhook_url = webhook_urls[0] if webhook_urls else ""

    state = load_state()

    endpoint_entry = {
        "app_name": app_name,
        "health_url": health_url,
        "webhook_url": webhook_url,
        "other_urls": other_urls,
        "timestamp": now,
        "verified": False
    }

    state["endpoints"].append(endpoint_entry)
    state["endpoints"] = state["endpoints"][-20:]
    state["total"] = state.get("total", 0) + 1

    save_state(state)

    # Build verification reason
    lines = []
    if health_url:
        lines.append(f"VERIFY: curl {health_url}")
    lines.append(f"LOGS:   modal app logs {app_name}")
    if webhook_url:
        lines.append(f"TEST:   curl -X POST '{webhook_url}' -H 'Content-Type: application/json' -d '{{\"message\":\"test\"}}'")
    for url in other_urls:
        lines.append(f"ENDPOINT: {url}")

    reason = "\n".join(lines)
    print(json.dumps({"decision": "ALLOW", "reason": reason}))


if __name__ == "__main__":
    main()
