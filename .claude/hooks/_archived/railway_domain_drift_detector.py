#!/usr/bin/env python3
"""
Hook 128: railway_domain_drift_detector.py (PostToolUse on Bash)
Detects when Railway service domains change, which can break external webhook integrations.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "railway_domain_registry.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"services": {}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def show_status():
    state = load_state()
    services = state.get("services", {})
    print("=== Railway Domain Drift Detector ===")
    print(f"Services tracked: {len(services)}")
    if services:
        print("\nRegistered domains:")
        for name, info in services.items():
            url = info.get("url", "?")
            first_seen = info.get("first_seen", "?")
            prev = info.get("previous_urls", [])
            print(f"  {name}: {url}")
            print(f"    First seen: {first_seen}")
            if prev:
                print(f"    Previous URLs: {', '.join(prev[-5:])}")
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
    if not ("railway up" in command or "railway deploy" in command or "railway domain" in command):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_result_str = str(tool_result)

    # Extract Railway URLs from result
    urls = re.findall(r'https://\S+\.up\.railway\.app', tool_result_str)
    if not urls:
        print(json.dumps({"decision": "ALLOW"}))
        return

    service = extract_service_name(command)
    state = load_state()
    now = datetime.now().isoformat()
    services = state.get("services", {})

    drift_warnings = []

    for url in urls:
        if service in services:
            existing = services[service]
            old_url = existing.get("url", "")
            if old_url and old_url != url:
                # Domain drift detected
                previous_urls = existing.get("previous_urls", [])
                if old_url not in previous_urls:
                    previous_urls.append(old_url)
                previous_urls = previous_urls[-10:]

                drift_warnings.append({
                    "service": service,
                    "old_url": old_url,
                    "new_url": url
                })

                sys.stderr.write(f"[RAILWAY DOMAIN DRIFT] Domain changed for '{service}'!\n")
                sys.stderr.write(f"  Old: {old_url}\n")
                sys.stderr.write(f"  New: {url}\n")
                sys.stderr.write(f"  UPDATE webhook URLs in external services (Calendly, Stripe, etc.)\n")

                services[service] = {
                    "url": url,
                    "first_seen": existing.get("first_seen", now),
                    "last_updated": now,
                    "previous_urls": previous_urls
                }
            else:
                # Same URL, just update timestamp
                services[service]["last_updated"] = now
        else:
            # New service, record it
            services[service] = {
                "url": url,
                "first_seen": now,
                "last_updated": now,
                "previous_urls": []
            }

    state["services"] = services
    save_state(state)

    if drift_warnings:
        parts = []
        for w in drift_warnings:
            parts.append(
                f"DOMAIN DRIFT for '{w['service']}': {w['old_url']} -> {w['new_url']}. "
                f"Update webhook URLs in external services (Calendly, Stripe, etc.)"
            )
        reason = " | ".join(parts)
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
