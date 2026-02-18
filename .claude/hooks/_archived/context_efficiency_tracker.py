#!/usr/bin/env python3
"""
Hook 61: context_efficiency_tracker.py (PostToolUse on Read)
Tracks how much context is loaded per workflow, categorized by type.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "context_efficiency.json"

# Approximate tokens per line (rough estimate)
TOKENS_PER_LINE = 10

CATEGORY_PATTERNS = {
    "directives": [r"directives/"],
    "context": [r"context/"],
    "skill_bibles": [r"skills/SKILL_BIBLE"],
    "client_profiles": [r"clients/"],
    "execution_scripts": [r"execution/"],
    "tmp_outputs": [r"\.tmp/"],
    "config_files": [r"\.env", r"requirements\.txt", r"Procfile", r"railway\.json"],
    "dashboard": [r"railway_apps/"],
    "hooks": [r"\.claude/hooks/"],
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "reads": [],
        "by_category": {},
        "total_lines": 0,
        "total_reads": 0,
        "estimated_tokens": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def categorize_file(file_path):
    """Determine category of the file being read."""
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, file_path):
                return category
    return "other"


def estimate_lines_from_result(tool_result):
    """Estimate line count from the tool result."""
    if not tool_result:
        return 0
    result_str = str(tool_result)
    return result_str.count("\n") + 1


def show_status():
    state = load_state()
    print("=== Context Efficiency Tracker ===")
    print(f"Total reads: {state.get('total_reads', 0)}")
    print(f"Total lines loaded: {state.get('total_lines', 0)}")
    print(f"Estimated tokens: {state.get('estimated_tokens', 0):,}")

    by_cat = state.get("by_category", {})
    if by_cat:
        print("\nContext by category:")
        sorted_cats = sorted(by_cat.items(), key=lambda x: x[1].get("lines", 0), reverse=True)
        for cat, info in sorted_cats:
            lines = info.get("lines", 0)
            reads = info.get("reads", 0)
            tokens = lines * TOKENS_PER_LINE
            print(f"  {cat}:")
            print(f"    Reads: {reads}, Lines: {lines:,}, Est. tokens: {tokens:,}")

    reads = state.get("reads", [])
    if reads:
        print("\nRecent reads:")
        for r in reads[-10:]:
            print(f"  [{r.get('category', '?')}] {r.get('file', '?')[:60]} ({r.get('lines', 0)} lines)")
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
    tool_result = data.get("tool_result", "")

    if tool_name not in ("Read", "read"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    if not file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()

    category = categorize_file(file_path)
    lines = estimate_lines_from_result(tool_result)

    # Update totals
    state["total_reads"] = state.get("total_reads", 0) + 1
    state["total_lines"] = state.get("total_lines", 0) + lines
    state["estimated_tokens"] = state.get("total_lines", 0) * TOKENS_PER_LINE

    # Update by category
    by_cat = state.get("by_category", {})
    if category not in by_cat:
        by_cat[category] = {"reads": 0, "lines": 0}
    by_cat[category]["reads"] = by_cat[category].get("reads", 0) + 1
    by_cat[category]["lines"] = by_cat[category].get("lines", 0) + lines
    state["by_category"] = by_cat

    # Log individual read
    read_entry = {
        "timestamp": now,
        "file": file_path,
        "category": category,
        "lines": lines
    }
    state["reads"] = state.get("reads", [])
    state["reads"].append(read_entry)
    state["reads"] = state["reads"][-200:]

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
