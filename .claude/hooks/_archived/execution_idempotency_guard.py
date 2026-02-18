#!/usr/bin/env python3
"""
Hook 80: execution_idempotency_guard.py - PreToolUse on Bash

Warns when the same execution script is run twice with the same arguments
in a session to prevent duplicate work.

Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages via sys.stderr.write()
  - Never prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show invocation history
  --reset   Clear invocation tracking
"""

import json
import sys
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "execution_idempotency.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "invocations": {},
        "duplicates_warned": 0,
        "total_invocations": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_execution_command(command):
    """Extract the execution script and its arguments."""
    match = re.search(r'(python3?\s+(?:\S*/)?execution/\S+\.py(?:\s+.*)?)\s*$', command)
    if match:
        return match.group(1).strip()
    return None


def extract_script_name(command):
    match = re.search(r'python3?\s+(?:\S*/)?execution/(\S+\.py)', command)
    return match.group(1) if match else None


def compute_invocation_hash(exec_command):
    """Compute a hash of the full execution command (script + args)."""
    normalized = re.sub(r'\s+', ' ', exec_command.strip())
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


def handle_status():
    state = load_state()
    print("Execution Idempotency Guard Status")
    print(f"  Total invocations tracked: {state['total_invocations']}")
    print(f"  Duplicate warnings: {state['duplicates_warned']}")
    print(f"  Unique invocations: {len(state['invocations'])}")
    if state["invocations"]:
        print("  Recent invocations:")
        items = list(state["invocations"].items())[-10:]
        for inv_hash, info in items:
            count = info.get("count", 1)
            script = info.get("script", "unknown")
            dup = " [DUPLICATE]" if count > 1 else ""
            print(f"    {script} (x{count}){dup}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "invocations": {}, "duplicates_warned": 0, "total_invocations": 0,
    }))
    print("Execution Idempotency Guard: State reset.")
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
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")
    exec_command = extract_execution_command(command)
    if not exec_command:
        sys.exit(0)

    script_name = extract_script_name(command)
    inv_hash = compute_invocation_hash(exec_command)

    state = load_state()
    state["total_invocations"] += 1

    if inv_hash in state["invocations"]:
        prev = state["invocations"][inv_hash]
        prev["count"] = prev.get("count", 1) + 1
        prev["last_seen"] = datetime.now().isoformat()
        state["duplicates_warned"] += 1
        save_state(state)

        sys.stderr.write(
            f"[Idempotency Guard] WARNING: Duplicate execution detected!\n"
            f"  Script: {script_name}\n"
            f"  Command: {exec_command[:100]}\n"
            f"  Previously run: {prev.get('first_seen', 'unknown')[:19]}\n"
            f"  Times executed: {prev['count']}\n"
            f"  This may produce duplicate outputs. Consider checking .tmp/ first.\n"
        )
        sys.exit(0)  # Warn but allow
    else:
        state["invocations"][inv_hash] = {
            "script": script_name,
            "command": exec_command[:200],
            "count": 1,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
        }
        save_state(state)
        sys.exit(0)


if __name__ == "__main__":
    main()
