#!/usr/bin/env python3
"""
Hook 79: skill_bible_freshness_checker.py - PostToolUse on Read

When reading a skill bible, checks if it might be outdated (older than 90 days).
Tracks which skill bibles have been flagged.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional staleness warnings

CLI Flags:
  --status  Show skill bible freshness stats
  --reset   Clear state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
SKILLS_DIR = BASE_DIR / "skills"
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "skill_freshness.json"

FRESHNESS_DAYS = 90


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "checked_bibles": {},
        "stale_bibles": [],
        "fresh_bibles": [],
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_skill_bible(file_path):
    """Check if the file is a skill bible."""
    path_str = str(file_path)
    return "skills/" in path_str and "SKILL_BIBLE" in path_str and path_str.endswith(".md")


def get_file_age_days(file_path):
    """Get file age in days from last modification time."""
    try:
        mtime = os.path.getmtime(file_path)
        age = datetime.now() - datetime.fromtimestamp(mtime)
        return age.days
    except OSError:
        return -1


def format_age(days):
    """Format age in human-readable format."""
    if days < 0:
        return "unknown"
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    months = days // 30
    if months < 12:
        return f"~{months} month{'s' if months != 1 else ''} ago"
    years = days // 365
    remaining_months = (days % 365) // 30
    return f"~{years}y {remaining_months}m ago"


def handle_status():
    state = load_state()
    print("Skill Bible Freshness Checker Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Fresh bibles: {len(state['fresh_bibles'])}")
    print(f"  Stale bibles (>{FRESHNESS_DAYS} days): {len(state['stale_bibles'])}")

    if state["stale_bibles"]:
        print("  Stale skill bibles:")
        for sb in state["stale_bibles"][-10:]:
            print(f"    - {sb}")

    if state["checked_bibles"]:
        print("  Recently checked:")
        items = list(state["checked_bibles"].items())[-5:]
        for name, info in items:
            age = info.get("age_days", "?")
            stale = "STALE" if info.get("is_stale") else "fresh"
            print(f"    [{stale}] {name} ({format_age(int(age) if isinstance(age, (int, float)) else -1)})")

    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "checked_bibles": {}, "stale_bibles": [],
        "fresh_bibles": [], "total_checks": 0,
    }))
    print("Skill Bible Freshness Checker: State reset.")
    sys.exit(0)


def main():
    if "--status" in sys.argv:
        handle_status()
    if "--reset" in sys.argv:
        handle_reset()

    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, IOError):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Read" or "tool_result" not in data:
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    if not is_skill_bible(file_path):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    bible_name = Path(file_path).name
    age_days = get_file_age_days(file_path)
    is_stale = age_days > FRESHNESS_DAYS if age_days >= 0 else False

    state["checked_bibles"][bible_name] = {
        "age_days": age_days,
        "is_stale": is_stale,
        "last_checked": datetime.now().isoformat(),
        "path": file_path,
    }

    if is_stale:
        if bible_name not in state["stale_bibles"]:
            state["stale_bibles"].append(bible_name)
        save_state(state)
        reason = (
            f"Skill bible {bible_name} may be outdated "
            f"(last modified {format_age(age_days)}, threshold: {FRESHNESS_DAYS} days). "
            f"Consider reviewing and updating it."
        )
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        if bible_name not in state["fresh_bibles"]:
            state["fresh_bibles"].append(bible_name)
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
