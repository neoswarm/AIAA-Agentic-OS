#!/usr/bin/env python3
"""
Hook 55: webhook_slug_validator.py (PreToolUse on Bash)
Validates webhook slug names when deploying webhook workflows.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "webhook_slug_checks.json"

RESERVED_SLUGS = [
    "health", "login", "logout", "api", "webhook", "admin",
    "static", "favicon", "robots", "sitemap", "env",
    "workflows", "logs", "status", "config", "settings"
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": [], "warnings_issued": 0, "slugs_seen": []}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def show_status():
    state = load_state()
    print("=== Webhook Slug Validator ===")
    print(f"Slugs checked: {len(state.get('checks', []))}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    print(f"Reserved slugs: {', '.join(RESERVED_SLUGS[:10])}...")
    slugs = state.get("slugs_seen", [])
    if slugs:
        print(f"\nSlugs used: {', '.join(slugs[-20:])}")
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
    if "deploy_webhook_workflow" not in command:
        sys.exit(0)

    # Extract --slug value
    slug_match = re.search(r'--slug\s+["\']?(\S+)', command)
    if not slug_match:
        sys.exit(0)

    slug = slug_match.group(1).strip("\"'")
    state = load_state()
    now = datetime.now().isoformat()
    issues = []

    # Check lowercase
    if slug != slug.lower():
        issues.append("Slug should be lowercase")

    # Check for valid characters (lowercase alphanumeric and hyphens)
    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', slug) and len(slug) > 1:
        if not re.match(r'^[a-z0-9]$', slug):
            issues.append("Slug should only contain lowercase letters, numbers, and hyphens")

    # Check length
    if len(slug) < 3:
        issues.append(f"Slug too short ({len(slug)} chars, minimum 3)")
    elif len(slug) > 50:
        issues.append(f"Slug too long ({len(slug)} chars, maximum 50)")

    # Check for special characters
    if re.search(r'[^a-z0-9-]', slug):
        issues.append("Slug contains special characters (only lowercase letters, numbers, hyphens allowed)")

    # Check reserved slugs
    if slug in RESERVED_SLUGS:
        issues.append(f"'{slug}' is a reserved slug - will conflict with dashboard routes")

    # Track slug
    slugs_seen = state.get("slugs_seen", [])
    if slug not in slugs_seen:
        slugs_seen.append(slug)
    state["slugs_seen"] = slugs_seen[-100:]

    check_entry = {
        "timestamp": now,
        "slug": slug,
        "issues": issues,
        "message": "; ".join(issues) if issues else "Valid slug"
    }
    state["checks"].append(check_entry)
    state["checks"] = state["checks"][-50:]

    if issues:
        state["warnings_issued"] = state.get("warnings_issued", 0) + 1
        sys.stderr.write(f"[webhook-slug-validator] Issues with slug '{slug}':\n")
        for issue in issues:
            sys.stderr.write(f"  - {issue}\n")

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
