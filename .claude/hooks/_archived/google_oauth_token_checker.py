#!/usr/bin/env python3
"""
Hook 34: Google OAuth Token Checker (PreToolUse on Bash)

Before running scripts that use Google APIs:
- create_google_doc*.py, read_sheet.py, append_to_sheet.py, update_sheet.py
- Check if token.pickle exists in project root
- Check if file is older than 7 days (may need refresh)
- Check if credentials.json exists (needed for token refresh)
- WARN via stderr if token missing or potentially expired. Exit 0 always.
"""

import json
import sys
import os
import re
import time
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "google_oauth_log.json"

TOKEN_FILE = PROJECT_ROOT / "token.pickle"
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"

# Scripts that need Google OAuth
GOOGLE_SCRIPTS = [
    "create_google_doc",
    "read_sheet",
    "append_to_sheet",
    "update_sheet",
    "export_to_sheets",
    "import_from_sheets",
    "google_docs",
    "google_sheets",
]

TOKEN_MAX_AGE_DAYS = 7


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


def is_google_script(command):
    """Check if the command runs a Google API script."""
    for script_prefix in GOOGLE_SCRIPTS:
        if script_prefix in command:
            return True
    return False


def check_token():
    """Check token.pickle status."""
    issues = []

    if not TOKEN_FILE.exists():
        issues.append("token.pickle not found - Google OAuth not configured")
        return issues

    # Check age
    try:
        mod_time = TOKEN_FILE.stat().st_mtime
        age_days = (time.time() - mod_time) / 86400
        if age_days > TOKEN_MAX_AGE_DAYS:
            issues.append(
                f"token.pickle is {age_days:.0f} days old "
                f"(may need refresh, threshold: {TOKEN_MAX_AGE_DAYS} days)"
            )
    except OSError:
        issues.append("Unable to check token.pickle age")

    return issues


def check_credentials():
    """Check credentials.json status."""
    issues = []

    if not CREDENTIALS_FILE.exists():
        issues.append(
            "credentials.json not found - needed for OAuth token refresh. "
            "Download from Google Cloud Console."
        )

    return issues


def handle_status():
    state = load_state()
    print("=== Google OAuth Token Checker Status ===")
    print(f"State file: {STATE_FILE}")

    print(f"\nToken status:")
    print(f"  token.pickle exists: {TOKEN_FILE.exists()}")
    if TOKEN_FILE.exists():
        try:
            mod_time = TOKEN_FILE.stat().st_mtime
            age_days = (time.time() - mod_time) / 86400
            mod_date = datetime.fromtimestamp(mod_time).isoformat()
            print(f"  Last modified: {mod_date}")
            print(f"  Age: {age_days:.1f} days")
            print(f"  Status: {'STALE' if age_days > TOKEN_MAX_AGE_DAYS else 'OK'}")
        except OSError:
            print("  Unable to read file stats")

    print(f"\nCredentials status:")
    print(f"  credentials.json exists: {CREDENTIALS_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"\nCheck history:")
    print(f"  Total checks: {stats.get('total', 0)}")
    print(f"  Warnings: {stats.get('warnings', 0)}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Google OAuth token checker state reset.")
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

    if not is_google_script(command):
        sys.exit(0)

    state = load_state()
    state["stats"]["total"] = state["stats"].get("total", 0) + 1

    # Check token and credentials
    issues = check_token() + check_credentials()

    check_record = {
        "command": command[:100],
        "issues": issues,
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_record)
    state["checks"] = state["checks"][-50:]

    if issues:
        state["stats"]["warnings"] = state["stats"].get("warnings", 0) + 1
        save_state(state)

        sys.stderr.write(
            "[GOOGLE OAUTH] " + "; ".join(issues) + "\n"
        )
    else:
        save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
