#!/usr/bin/env python3
"""
Hook 48: concurrent_write_guard.py (PreToolUse on Write)
Warns when a file might be written to by multiple agents simultaneously.
Tracks active writes and auto-cleans after 30 seconds.
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "active_writes.json"
AGENT_FILE = STATE_DIR / "active_agents.json"
WRITE_TTL = 30  # seconds before auto-cleanup


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"active_writes": {}, "warnings_issued": 0, "total_writes": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def load_agents():
    try:
        if AGENT_FILE.exists():
            return json.loads(AGENT_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"active_agents": 0}


def cleanup_stale_writes(state):
    """Remove writes older than TTL seconds."""
    now = time.time()
    active = state.get("active_writes", {})
    cleaned = {}
    for filepath, info in active.items():
        ts = info.get("timestamp_epoch", 0)
        if now - ts < WRITE_TTL:
            cleaned[filepath] = info
    state["active_writes"] = cleaned
    return state


def show_status():
    state = load_state()
    state = cleanup_stale_writes(state)
    save_state(state)
    agents = load_agents()
    print("=== Concurrent Write Guard ===")
    print(f"Active agents: {agents.get('active_agents', 0)}")
    print(f"Active writes: {len(state.get('active_writes', {}))}")
    print(f"Total writes tracked: {state.get('total_writes', 0)}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    active = state.get("active_writes", {})
    if active:
        print("\nCurrently active writes:")
        for fp, info in active.items():
            age = time.time() - info.get("timestamp_epoch", 0)
            print(f"  - {fp} ({age:.0f}s ago)")
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

    if tool_name not in ("Write", "write"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    state = load_state()
    state = cleanup_stale_writes(state)
    state["total_writes"] = state.get("total_writes", 0) + 1

    now = time.time()
    now_iso = datetime.now().isoformat()
    active = state.get("active_writes", {})

    # Check if this file is already being written
    if file_path in active:
        prev = active[file_path]
        age = now - prev.get("timestamp_epoch", 0)
        if age < WRITE_TTL:
            state["warnings_issued"] = state.get("warnings_issued", 0) + 1
            filename = Path(file_path).name
            sys.stderr.write(
                f"[concurrent-write-guard] File '{filename}' may be written to by another agent. "
                f"Possible race condition. (Last write {age:.0f}s ago)\n"
            )

    # Register this write
    active[file_path] = {
        "timestamp": now_iso,
        "timestamp_epoch": now
    }
    state["active_writes"] = active
    save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
