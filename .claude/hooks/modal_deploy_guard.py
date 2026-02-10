#!/usr/bin/env python3
"""
Hook 121: Modal Deploy Guard
Type: PreToolUse on Bash tool
Tier: Advisory (never blocks)

When a command contains 'modal deploy' or 'deploy_to_modal.py', prints a
deployment checklist to stderr as a reminder. Also checks if the Modal CLI
is on PATH.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {"command": "..."}}
  - Exit 0 = allow (always)
  - Warnings/info written to stderr
  - NEVER prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show deploy checklist and recent deploy attempts
  --reset   Clear deploy attempt history
"""

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR = Path("/Users/lucasnolan/Agentic OS/.tmp/hooks")
STATE_FILE = STATE_DIR / "modal_deploy_checks.json"
MAX_ENTRIES = 50

DEPLOY_CHECKLIST = """[MODAL DEPLOY CHECKLIST]
- Modal CLI authenticated? (modal token show)
- Required secrets created? (modal secret list)
- Under 8 endpoint limit? (modal app list)
- Target script free of dotenv crash bug?
- Expect 2-10s cold start on first request
- Debug with: modal app logs <app-name>"""


def load_state():
    """Load deploy attempt tracking data."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {"deploy_attempts": []}


def save_state(data):
    """Save deploy attempt tracking data."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Cap entries
    entries = data.get("deploy_attempts", [])
    if len(entries) > MAX_ENTRIES:
        data["deploy_attempts"] = entries[-MAX_ENTRIES:]
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def check_status():
    """Print deploy checklist and recent attempts."""
    print("Modal Deploy Guard - Status")
    print("=" * 50)
    print()
    print(DEPLOY_CHECKLIST)
    print()

    # Check Modal CLI availability
    modal_path = shutil.which("modal")
    if modal_path:
        print(f"  Modal CLI: found at {modal_path}")
    else:
        print("  Modal CLI: NOT FOUND on PATH")

    # Show recent deploy attempts
    data = load_state()
    attempts = data.get("deploy_attempts", [])
    if attempts:
        print(f"\n  Recent deploy attempts ({len(attempts)} total):")
        for entry in attempts[-10:]:
            ts = entry.get("timestamp", "?")[:19]
            cmd = entry.get("command", "?")[:60]
            print(f"    {ts} - {cmd}")
    else:
        print("\n  No deploy attempts recorded yet.")

    sys.exit(0)


def check_reset():
    """Clear deploy attempt history."""
    print("Modal Deploy Guard - Reset")
    if STATE_FILE.exists():
        os.remove(STATE_FILE)
        print("Deploy attempt history cleared.")
    else:
        print("No state file to clear.")
    sys.exit(0)


def main():
    # Handle CLI flags first
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            check_status()
        elif sys.argv[1] == "--reset":
            check_reset()

    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not command:
        sys.exit(0)

    # Check for modal deploy commands
    is_modal_deploy = "modal deploy" in command or "deploy_to_modal.py" in command
    if not is_modal_deploy:
        sys.exit(0)

    # Print the checklist
    sys.stderr.write(f"\n{DEPLOY_CHECKLIST}\n\n")

    # Check if modal is on PATH
    if not shutil.which("modal"):
        sys.stderr.write(
            "[MODAL WARNING] 'modal' CLI not found on PATH.\n"
            "  Install: pip install modal\n"
            "  Auth:    modal token set\n\n"
        )

    # Track the deploy attempt
    state = load_state()
    state["deploy_attempts"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command[:200],
    })
    save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
