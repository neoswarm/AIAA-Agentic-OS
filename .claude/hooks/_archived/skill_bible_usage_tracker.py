#!/usr/bin/env python3
"""
Hook 62: skill_bible_usage_tracker.py (Dual: PostToolUse/Read + status)
Tracks which skill bibles are used and correlates with execution scripts.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "skill_bible_usage.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"skill_bibles": {}, "session_scripts": [], "total_reads": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_skill_name(file_path):
    """Extract skill bible name from file path."""
    match = re.search(r'SKILL_BIBLE_(.+?)\.md', file_path)
    if match:
        return match.group(1)
    return None


def show_status():
    state = load_state()
    bibles = state.get("skill_bibles", {})
    print("=== Skill Bible Usage Tracker ===")
    print(f"Total skill bible reads: {state.get('total_reads', 0)}")
    print(f"Unique skill bibles used: {len(bibles)}")

    if bibles:
        # Sort by usage count
        sorted_bibles = sorted(bibles.items(), key=lambda x: x[1].get("count", 0), reverse=True)

        print("\nMost used:")
        for name, info in sorted_bibles[:10]:
            count = info.get("count", 0)
            last = info.get("last_used", "?")[:10]
            workflows = info.get("workflows_used_with", [])
            print(f"  {name}: {count} reads (last: {last})")
            if workflows:
                print(f"    Used with: {', '.join(workflows[-5:])}")

        if len(sorted_bibles) > 10:
            print("\nLeast used:")
            for name, info in sorted_bibles[-5:]:
                count = info.get("count", 0)
                print(f"  {name}: {count} reads")
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
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    has_result = "tool_result" in data

    # This is a dual-mode hook
    if tool_name not in ("Read", "read"):
        if has_result:
            print(json.dumps({"decision": "ALLOW"}))
        else:
            sys.exit(0)
        return

    file_path = tool_input.get("file_path", "")
    if "SKILL_BIBLE_" not in file_path:
        if has_result:
            print(json.dumps({"decision": "ALLOW"}))
        else:
            sys.exit(0)
        return

    skill_name = extract_skill_name(file_path)
    if not skill_name:
        if has_result:
            print(json.dumps({"decision": "ALLOW"}))
        else:
            sys.exit(0)
        return

    state = load_state()
    now = datetime.now().isoformat()
    state["total_reads"] = state.get("total_reads", 0) + 1

    bibles = state.get("skill_bibles", {})
    if skill_name not in bibles:
        bibles[skill_name] = {
            "count": 0,
            "last_used": "",
            "workflows_used_with": []
        }

    bibles[skill_name]["count"] = bibles[skill_name].get("count", 0) + 1
    bibles[skill_name]["last_used"] = now

    # Correlate with recent scripts from session
    session_scripts = state.get("session_scripts", [])
    for script in session_scripts:
        if script not in bibles[skill_name].get("workflows_used_with", []):
            bibles[skill_name]["workflows_used_with"].append(script)
    # Keep only last 20 correlations
    bibles[skill_name]["workflows_used_with"] = bibles[skill_name]["workflows_used_with"][-20:]

    state["skill_bibles"] = bibles
    save_state(state)

    if has_result:
        print(json.dumps({"decision": "ALLOW"}))
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
