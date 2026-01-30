#!/usr/bin/env python3
"""
Hook 92: retry_loop_detector.py - PreToolUse on Bash

Detects and prevents infinite retry loops when scripts fail repeatedly.
If the same script fails 3+ times consecutively, blocks with suggestion
to investigate the root cause.

Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages via sys.stderr.write()
  - Never prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show retry tracking stats
  --reset   Clear retry state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "retry_loop.json"

MAX_CONSECUTIVE_FAILURES = 3


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "script_failures": {},
        "blocked_scripts": [],
        "total_blocks": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_script_name(command):
    match = re.search(r'python3?\s+(?:\S*/)?execution/(\S+\.py)', command)
    return match.group(1) if match else None


def record_failure(state, script_name, error_snippet=""):
    """Record a script failure."""
    if script_name not in state["script_failures"]:
        state["script_failures"][script_name] = {
            "consecutive_failures": 0,
            "total_failures": 0,
            "last_errors": [],
        }
    info = state["script_failures"][script_name]
    info["consecutive_failures"] += 1
    info["total_failures"] += 1
    info["last_failure"] = datetime.now().isoformat()
    if error_snippet:
        info["last_errors"].append(error_snippet[:200])
        info["last_errors"] = info["last_errors"][-5:]


def record_success(state, script_name):
    """Record a script success - resets consecutive failures."""
    if script_name in state["script_failures"]:
        state["script_failures"][script_name]["consecutive_failures"] = 0


def handle_status():
    state = load_state()
    print("Retry Loop Detector Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Total blocks: {state['total_blocks']}")
    print(f"  Scripts tracked: {len(state['script_failures'])}")
    print(f"  Max consecutive failures before block: {MAX_CONSECUTIVE_FAILURES}")
    if state["script_failures"]:
        print("  Script failure tracking:")
        for script, info in state["script_failures"].items():
            consec = info.get("consecutive_failures", 0)
            total = info.get("total_failures", 0)
            status = "BLOCKED" if consec >= MAX_CONSECUTIVE_FAILURES else "tracked"
            print(f"    [{status}] {script}: {consec} consecutive, {total} total")
    if state["blocked_scripts"]:
        print("  Recently blocked:")
        for bs in state["blocked_scripts"][-5:]:
            print(f"    - {bs}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "script_failures": {}, "blocked_scripts": [],
        "total_blocks": 0, "total_checks": 0,
    }))
    print("Retry Loop Detector: State reset.")
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
    script_name = extract_script_name(command)
    if not script_name:
        sys.exit(0)

    state = load_state()
    state["total_checks"] += 1

    # Check if this script has been failing
    if script_name in state["script_failures"]:
        info = state["script_failures"][script_name]
        consec = info.get("consecutive_failures", 0)

        if consec >= MAX_CONSECUTIVE_FAILURES:
            state["total_blocks"] += 1
            block_entry = f"{script_name} ({consec} failures, {datetime.now().isoformat()[:19]})"
            if block_entry not in state["blocked_scripts"]:
                state["blocked_scripts"].append(block_entry)
            save_state(state)

            last_errors = info.get("last_errors", [])
            error_hint = ""
            if last_errors:
                error_hint = f"\n  Last error: {last_errors[-1][:100]}"

            sys.stderr.write(
                f"[Retry Loop] BLOCKED: {script_name} has failed {consec} consecutive times.\n"
                f"  Retrying won't help - investigate the root cause:{error_hint}\n"
                f"  Suggestions:\n"
                f"    1. Check the script with: python3 execution/{script_name} --help\n"
                f"    2. Verify required API keys are set\n"
                f"    3. Check input arguments\n"
                f"    4. Use --reset to clear failure tracking after fixing the issue\n"
            )
            sys.exit(2)

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
