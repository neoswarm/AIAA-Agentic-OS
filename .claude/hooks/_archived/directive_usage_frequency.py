#!/usr/bin/env python3
"""
Hook 114: directive_usage_frequency.py (PostToolUse on Read)
Purpose: Track which directives are most/least used.
Logic: When directives are read, increment usage counter. Track frequency,
last used date, and usage trends. Surface least-used directives that might be stale.

Protocol:
  - PostToolUse: prints JSON to stdout {"decision": "ALLOW"}
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "directive_usage.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "directives": {},
        "total_reads": 0,
        "daily_reads": {},
        "session_reads": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_directive_name(file_path):
    """Extract directive name from file path."""
    match = re.search(r'directives/(.+?)\.md', file_path)
    if match:
        return match.group(1)
    return None


def show_status():
    state = load_state()
    directives = state.get("directives", {})

    print("=== Directive Usage Frequency ===")
    print(f"Total directive reads: {state.get('total_reads', 0)}")
    print(f"Session reads: {state.get('session_reads', 0)}")
    print(f"Unique directives accessed: {len(directives)}")

    if directives:
        # Most used
        sorted_by_usage = sorted(directives.items(),
                                 key=lambda x: x[1].get("read_count", 0),
                                 reverse=True)

        print(f"\nMost used directives (top {min(10, len(sorted_by_usage))}):")
        for name, data in sorted_by_usage[:10]:
            count = data.get("read_count", 0)
            last_used = data.get("last_read", "?")[:10]
            print(f"  {count:3d}x  {name} (last: {last_used})")

        # Least used (potential stale)
        sorted_by_least = sorted(directives.items(),
                                 key=lambda x: x[1].get("read_count", 0))
        stale = [d for d in sorted_by_least if d[1].get("read_count", 0) <= 2]

        if stale:
            print(f"\nLeast used directives ({len(stale)} with 2 or fewer reads):")
            for name, data in stale[:10]:
                count = data.get("read_count", 0)
                last_used = data.get("last_read", "never")[:10]
                print(f"  {count:3d}x  {name} (last: {last_used})")

        # Usage by day
        daily = state.get("daily_reads", {})
        if daily:
            print("\nDaily read counts (last 7 days):")
            for date in sorted(daily.keys())[-7:]:
                print(f"  {date}: {daily[date]} reads")

        # Recently accessed
        recently_accessed = sorted(directives.items(),
                                   key=lambda x: x[1].get("last_read", ""),
                                   reverse=True)
        print(f"\nRecently accessed (last {min(5, len(recently_accessed))}):")
        for name, data in recently_accessed[:5]:
            last_read = data.get("last_read", "?")[:19]
            count = data.get("read_count", 0)
            print(f"  {name} ({count}x, last: {last_read})")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Directive usage frequency state reset.")
    sys.exit(0)


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

    if tool_name not in ("Read", "read"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    if "directives/" not in file_path or not file_path.endswith(".md"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    directive_name = extract_directive_name(file_path)
    if not directive_name:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()
    today = now[:10]

    # Update directive record
    directives = state.get("directives", {})
    if directive_name not in directives:
        directives[directive_name] = {
            "read_count": 0,
            "first_read": now,
            "last_read": now,
            "read_dates": []
        }

    directives[directive_name]["read_count"] += 1
    directives[directive_name]["last_read"] = now

    read_dates = directives[directive_name].get("read_dates", [])
    if today not in read_dates:
        read_dates.append(today)
    directives[directive_name]["read_dates"] = read_dates[-30:]

    state["directives"] = directives

    # Update totals
    state["total_reads"] = state.get("total_reads", 0) + 1
    state["session_reads"] = state.get("session_reads", 0) + 1

    # Daily
    daily = state.get("daily_reads", {})
    daily[today] = daily.get(today, 0) + 1
    state["daily_reads"] = daily

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
