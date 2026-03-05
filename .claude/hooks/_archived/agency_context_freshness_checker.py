#!/usr/bin/env python3
"""
Hook 42: Agency Context Freshness Checker (PreToolUse on Bash)

Before content generation scripts (generate_*.py, write_*.py):
- Check .tmp/hooks/context_state.json for last load timestamp of agency context files
- If context was loaded more than 2 hours ago or never loaded: WARN
- Track session start time

Exit 0 always.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "agency_freshness_log.json"
CONTEXT_STATE_FILE = STATE_DIR / "context_state.json"

FRESHNESS_WINDOW_HOURS = 2

# Scripts that should have fresh agency context
CONTENT_SCRIPTS = [
    r"generate_\w+\.py",
    r"write_\w+\.py",
    r"create_\w+\.py",
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "session_start": datetime.now().isoformat(),
        "checks": [],
        "stats": {"total": 0, "warnings": 0}
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def load_context_state():
    try:
        if CONTEXT_STATE_FILE.exists():
            return json.loads(CONTEXT_STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def is_content_script(command):
    """Check if the command runs a content generation script."""
    for pattern in CONTENT_SCRIPTS:
        if re.search(pattern, command):
            return True
    return False


def check_agency_context_freshness(context_state):
    """Check if agency context was recently loaded."""
    loaded_files = context_state.get("loaded_files", [])
    loaded_contexts = context_state.get("loaded_contexts", [])

    # Look for agency context files
    agency_files = ["agency.md", "brand_voice.md", "owner.md", "services.md"]
    latest_load = None

    all_loaded = loaded_files + loaded_contexts
    for entry in all_loaded:
        path = entry if isinstance(entry, str) else entry.get("path", "")
        timestamp = None
        if isinstance(entry, dict):
            timestamp = entry.get("timestamp")

        for agency_file in agency_files:
            if agency_file in path:
                if timestamp:
                    try:
                        load_time = datetime.fromisoformat(timestamp)
                        if latest_load is None or load_time > latest_load:
                            latest_load = load_time
                    except (ValueError, TypeError):
                        pass
                else:
                    # File was loaded but no timestamp - assume it's from this session
                    return True, None

    if latest_load is None:
        return False, None

    # Check freshness
    now = datetime.now()
    age = now - latest_load
    if age > timedelta(hours=FRESHNESS_WINDOW_HOURS):
        return False, age
    return True, age


def handle_status():
    state = load_state()
    print("=== Agency Context Freshness Checker Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"Context state file: {CONTEXT_STATE_FILE}")
    print(f"Context state exists: {CONTEXT_STATE_FILE.exists()}")
    print(f"Freshness window: {FRESHNESS_WINDOW_HOURS} hours")

    context_state = load_context_state()
    is_fresh, age = check_agency_context_freshness(context_state)

    if age:
        hours = age.total_seconds() / 3600
        print(f"\nAgency context age: {hours:.1f} hours")
        print(f"Context is: {'FRESH' if is_fresh else 'STALE'}")
    else:
        print(f"\nAgency context: {'LOADED (no timestamp)' if is_fresh else 'NOT LOADED'}")

    print(f"\nSession start: {state.get('session_start', 'unknown')}")

    stats = state.get("stats", {})
    print(f"Total checks: {stats.get('total', 0)}")
    print(f"Warnings: {stats.get('warnings', 0)}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Agency context freshness checker state reset.")
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

    if not is_content_script(command):
        sys.exit(0)

    state = load_state()
    state["stats"]["total"] = state["stats"].get("total", 0) + 1

    context_state = load_context_state()
    is_fresh, age = check_agency_context_freshness(context_state)

    check_record = {
        "command": command[:80],
        "is_fresh": is_fresh,
        "timestamp": datetime.now().isoformat(),
    }
    if age:
        check_record["age_hours"] = round(age.total_seconds() / 3600, 1)

    state["checks"].append(check_record)
    state["checks"] = state["checks"][-50:]

    if not is_fresh:
        state["stats"]["warnings"] = state["stats"].get("warnings", 0) + 1
        save_state(state)

        if age:
            hours = age.total_seconds() / 3600
            sys.stderr.write(
                f"[CONTEXT FRESHNESS] Agency context loaded {hours:.1f} hours ago "
                f"(threshold: {FRESHNESS_WINDOW_HOURS}h). "
                f"Consider reloading context/agency.md and context/brand_voice.md\n"
            )
        else:
            sys.stderr.write(
                "[CONTEXT FRESHNESS] Agency context not loaded in this session. "
                "Load context/agency.md before generating content.\n"
            )
    else:
        save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
