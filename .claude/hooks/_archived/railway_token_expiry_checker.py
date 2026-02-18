#!/usr/bin/env python3
"""
Hook 57: railway_token_expiry_checker.py (PreToolUse on Bash)
Before railway CLI commands, checks if the Railway config/token might be stale.
"""

import json
import sys
import os
import time
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "railway_token_checks.json"

RAILWAY_CONFIG_PATHS = [
    Path.home() / ".railway" / "config.json",
    Path.home() / ".config" / "railway" / "config.json",
]

MAX_AGE_DAYS = 30


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


def find_config():
    """Find the Railway config file."""
    for path in RAILWAY_CONFIG_PATHS:
        if path.exists():
            return path
    return None


def show_status():
    state = load_state()
    config_path = find_config()
    print("=== Railway Token Expiry Checker ===")
    print(f"Checks performed: {len(state.get('checks', []))}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    if config_path:
        mtime = os.path.getmtime(config_path)
        age_days = (time.time() - mtime) / 86400
        print(f"\nConfig file: {config_path}")
        print(f"Config age: {age_days:.1f} days")
        print(f"Max age before warning: {MAX_AGE_DAYS} days")
        if age_days > MAX_AGE_DAYS:
            print("STATUS: Token may need refresh")
        else:
            print("STATUS: Token appears fresh")
    else:
        print("\nNo Railway config found at expected locations:")
        for p in RAILWAY_CONFIG_PATHS:
            print(f"  - {p}")
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

    config_path = find_config()

    check_entry = {"timestamp": now, "warning": False, "message": ""}

    if config_path is None:
        check_entry["warning"] = True
        check_entry["message"] = "No Railway config found. Run `railway login` first."
        state["warnings_issued"] = state.get("warnings_issued", 0) + 1
        sys.stderr.write("[railway-token-check] No Railway config found. Run `railway login` first.\n")
    else:
        try:
            mtime = os.path.getmtime(config_path)
            age_days = (time.time() - mtime) / 86400

            # Check if token looks valid
            try:
                config_data = json.loads(config_path.read_text())
                token = config_data.get("token", "") or config_data.get("user", {}).get("token", "")
                if not token or len(str(token)) < 10:
                    check_entry["warning"] = True
                    check_entry["message"] = "Railway token appears empty or malformed"
                    state["warnings_issued"] = state.get("warnings_issued", 0) + 1
                    sys.stderr.write("[railway-token-check] Railway token appears empty or malformed.\n")
            except (json.JSONDecodeError, KeyError):
                pass

            if age_days > MAX_AGE_DAYS:
                check_entry["warning"] = True
                check_entry["message"] = f"Config is {age_days:.0f} days old"
                state["warnings_issued"] = state.get("warnings_issued", 0) + 1
                sys.stderr.write(
                    f"[railway-token-check] Railway config is {age_days:.0f} days old. "
                    f"Token may need refresh. Run `railway login` if commands fail.\n"
                )
            else:
                check_entry["message"] = f"Config is {age_days:.0f} days old (OK)"

        except OSError as e:
            check_entry["warning"] = True
            check_entry["message"] = f"Could not read config: {e}"

    state["checks"].append(check_entry)
    state["checks"] = state["checks"][-50:]
    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
