#!/usr/bin/env python3
"""
Hook 65: session_productivity_scorer.py (PostToolUse on Bash)
Scores session productivity based on successful outputs, failures, and deliverables.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "productivity_score.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "successful_outputs": 0,
        "failed_runs": 0,
        "deliverables_created": 0,
        "self_anneals": 0,
        "total_commands": 0,
        "session_start": "",
        "session_last": ""
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def calculate_score(state):
    """Calculate productivity score."""
    score = (
        (state.get("successful_outputs", 0) * 10)
        + (state.get("deliverables_created", 0) * 5)
        - (state.get("failed_runs", 0) * 3)
        + (state.get("self_anneals", 0) * 2)
    )
    return max(score, 0)


def is_execution_script(command):
    """Check if command runs an execution script."""
    return bool(re.search(r'python3?\s+.*execution/\w+\.py', command))


def is_self_anneal(command):
    """Check if this is a self-annealing commit."""
    return "self-anneal" in command.lower() or "self_anneal" in command.lower()


def determine_success(tool_result):
    """Determine if command succeeded from result."""
    if not tool_result:
        return None  # Unknown
    result_str = str(tool_result).lower()
    failure_indicators = [
        "error", "traceback", "exception", "failed", "errno",
        "modulenotfounderror", "importerror", "syntaxerror"
    ]
    for ind in failure_indicators:
        if ind in result_str:
            return False
    return True


def show_status():
    state = load_state()
    score = calculate_score(state)
    print("=== Session Productivity Score ===")
    print(f"\nScore: {score}")
    print(f"\nBreakdown:")
    print(f"  Successful outputs:   {state.get('successful_outputs', 0):>4} x 10 = {state.get('successful_outputs', 0) * 10:>5}")
    print(f"  Deliverables created: {state.get('deliverables_created', 0):>4} x  5 = {state.get('deliverables_created', 0) * 5:>5}")
    print(f"  Self-anneals:         {state.get('self_anneals', 0):>4} x  2 = {state.get('self_anneals', 0) * 2:>5}")
    print(f"  Failed runs:          {state.get('failed_runs', 0):>4} x -3 = {state.get('failed_runs', 0) * -3:>5}")
    print(f"  Total commands:       {state.get('total_commands', 0):>4}")

    start = state.get("session_start", "")
    last = state.get("session_last", "")
    if start and last:
        print(f"\nSession: {start[:19]} to {last[:19]}")
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

    if tool_name not in ("Bash", "bash"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    state = load_state()
    now = datetime.now().isoformat()

    # Track session timing
    if not state.get("session_start"):
        state["session_start"] = now
    state["session_last"] = now

    state["total_commands"] = state.get("total_commands", 0) + 1

    # Track execution script runs
    if is_execution_script(command):
        success = determine_success(tool_result)
        if success is True:
            state["successful_outputs"] = state.get("successful_outputs", 0) + 1
        elif success is False:
            state["failed_runs"] = state.get("failed_runs", 0) + 1

    # Track self-annealing
    if is_self_anneal(command):
        state["self_anneals"] = state.get("self_anneals", 0) + 1

    # Check for deliverable creation indicators in command
    if "create_google_doc" in command or "send_slack_notification" in command:
        state["deliverables_created"] = state.get("deliverables_created", 0) + 1

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
