#!/usr/bin/env python3
"""
Hook 63: directive_coverage_tracker.py (Dual: PostToolUse/Read)
Tracks which directives have been used and calculates coverage.
"""

import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "directive_coverage.json"
DIRECTIVES_DIR = Path("directives")


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"directives_used": {}, "total_reads": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def count_total_directives():
    """Count total .md files in directives/ directory."""
    if not DIRECTIVES_DIR.exists():
        return 0
    count = 0
    try:
        for f in DIRECTIVES_DIR.iterdir():
            if f.suffix == ".md":
                count += 1
    except OSError:
        pass
    return count


def extract_directive_name(file_path):
    """Extract directive name from file path."""
    match = re.search(r'directives/(.+?)\.md', file_path)
    if match:
        return match.group(1)
    return None


def show_status():
    state = load_state()
    used = state.get("directives_used", {})
    total = count_total_directives()
    used_count = len(used)

    print("=== Directive Coverage Tracker ===")
    print(f"Total directives: {total}")
    print(f"Directives used: {used_count}")
    print(f"Unused directives: {total - used_count}")
    if total > 0:
        coverage = (used_count / total) * 100
        print(f"Coverage: {coverage:.1f}%")
    print(f"Total reads: {state.get('total_reads', 0)}")

    if used:
        print("\nUsed directives (by frequency):")
        sorted_dirs = sorted(used.items(), key=lambda x: x[1].get("use_count", 0), reverse=True)
        for name, info in sorted_dirs[:15]:
            count = info.get("use_count", 0)
            last = info.get("last_used", "?")[:10]
            print(f"  {name}: {count} uses (last: {last})")

    # Show some unused directives
    if DIRECTIVES_DIR.exists() and total > used_count:
        print(f"\nSample unused directives:")
        count_shown = 0
        try:
            for f in sorted(DIRECTIVES_DIR.iterdir()):
                if f.suffix == ".md":
                    name = f.stem
                    if name not in used:
                        print(f"  - {name}")
                        count_shown += 1
                        if count_shown >= 10:
                            remaining = (total - used_count) - count_shown
                            if remaining > 0:
                                print(f"  ... and {remaining} more")
                            break
        except OSError:
            pass
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

    if tool_name not in ("Read", "read"):
        if has_result:
            print(json.dumps({"decision": "ALLOW"}))
        else:
            sys.exit(0)
        return

    file_path = tool_input.get("file_path", "")
    if "directives/" not in file_path:
        if has_result:
            print(json.dumps({"decision": "ALLOW"}))
        else:
            sys.exit(0)
        return

    directive_name = extract_directive_name(file_path)
    if not directive_name:
        if has_result:
            print(json.dumps({"decision": "ALLOW"}))
        else:
            sys.exit(0)
        return

    state = load_state()
    now = datetime.now().isoformat()
    state["total_reads"] = state.get("total_reads", 0) + 1

    used = state.get("directives_used", {})
    if directive_name not in used:
        used[directive_name] = {"use_count": 0, "last_used": ""}

    used[directive_name]["use_count"] = used[directive_name].get("use_count", 0) + 1
    used[directive_name]["last_used"] = now
    state["directives_used"] = used

    save_state(state)

    if has_result:
        print(json.dumps({"decision": "ALLOW"}))
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
