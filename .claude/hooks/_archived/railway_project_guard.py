#!/usr/bin/env python3
"""
Hook 50: railway_project_guard.py (PreToolUse on Bash)
Before railway CLI commands, validates project ID and directory context.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "railway_project_checks.json"

EXPECTED_PROJECT_ID = "3b96c81f-9518-4131-b2bc-bcd7a524a5ef"
KNOWN_APPS = ["aiaa_dashboard", "aiaa-dashboard"]
RAILWAY_COMMANDS_OF_INTEREST = ["link", "up", "deploy", "variables"]


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
    print("=== Railway Project Guard ===")
    print(f"Total checks: {len(state.get('checks', []))}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    print(f"Expected project ID: {EXPECTED_PROJECT_ID}")
    checks = state.get("checks", [])
    if checks:
        print("\nRecent checks:")
        for c in checks[-10:]:
            status = "WARN" if c.get("warning") else "OK"
            print(f"  [{status}] {c.get('command_type', '?')} - {c.get('message', '')}")
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
    if "railway" not in command:
        sys.exit(0)

    state = load_state()
    now = datetime.now().isoformat()
    warnings = []
    command_type = "unknown"

    for cmd in RAILWAY_COMMANDS_OF_INTEREST:
        if f"railway {cmd}" in command or f"railway {cmd}" in command.replace("  ", " "):
            command_type = cmd
            break

    if command_type == "unknown":
        # Not a command we care about
        save_state(state)
        sys.exit(0)

    # Check for project ID in railway link
    if command_type == "link":
        # Look for project ID in command
        id_match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', command)
        if id_match:
            found_id = id_match.group(0)
            if found_id != EXPECTED_PROJECT_ID:
                warnings.append(
                    f"Different project ID detected: {found_id}. "
                    f"Expected: {EXPECTED_PROJECT_ID}"
                )

    # Check if inside railway_apps/ and subfolder matches known app
    if command_type in ("up", "deploy"):
        # Check for cd commands in the command
        cd_match = re.search(r'cd\s+["\']?([^"\';&]+)', command)
        if cd_match:
            cd_path = cd_match.group(1).strip()
            if "railway_apps/" in cd_path:
                subfolder = cd_path.split("railway_apps/")[-1].strip("/")
                if subfolder and subfolder not in KNOWN_APPS:
                    warnings.append(
                        f"Unknown Railway app directory: {subfolder}. "
                        f"Known apps: {', '.join(KNOWN_APPS)}"
                    )

    check_entry = {
        "timestamp": now,
        "command_type": command_type,
        "warning": bool(warnings),
        "message": "; ".join(warnings) if warnings else "OK"
    }
    state["checks"].append(check_entry)
    state["checks"] = state["checks"][-50:]

    if warnings:
        state["warnings_issued"] = state.get("warnings_issued", 0) + 1
        sys.stderr.write(f"[railway-project-guard] Warnings:\n")
        for w in warnings:
            sys.stderr.write(f"  - {w}\n")

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
