#!/usr/bin/env python3
"""
Hook 73: phase_ordering_enforcer.py - Dual-mode (Pre+Post on Bash)

Enforces the 7-phase DOE execution flow:
  1. Parse Input
  2. Capability Check
  3. Load Context (read directives/skills/context)
  4. Execute Directive (run scripts)
  5. Quality Gates (validate outputs)
  6. Delivery (write outputs, create docs)
  7. Self-Anneal (git commit, update directives)

Dual Mode Detection:
  - If "tool_result" exists -> PostToolUse: track phase completions
  - If "tool_result" missing -> PreToolUse: warn if phases skipped

CLI Flags:
  --status  Show phase progression
  --reset   Clear phase tracking
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "phase_ordering.json"

# Phase definitions with detection patterns
PHASES = {
    1: {"name": "Parse Input", "auto": True},  # Always assumed done
    2: {"name": "Capability Check", "patterns": [
        r'ls\s+directives/', r'ls\s+execution/', r'grep\s+-i.*directives',
        r'ls\s+skills/', r'find\s+.*directive',
    ]},
    3: {"name": "Load Context", "patterns": [
        r'cat\s+.*directives/', r'cat\s+.*skills/', r'cat\s+.*context/',
        r'cat\s+.*clients/', r'head\s+.*directives/', r'head\s+.*skills/',
    ]},
    4: {"name": "Execute Directive", "patterns": [
        r'python3?\s+(?:\S*/)?execution/\S+\.py',
    ]},
    5: {"name": "Quality Gates", "patterns": [
        r'cat\s+.*\.tmp/', r'wc\s+.*\.tmp/', r'head\s+.*\.tmp/',
        r'python3?\s+.*validate', r'python3?\s+.*check',
    ]},
    6: {"name": "Delivery", "patterns": [
        r'python3?\s+.*create_google_doc', r'python3?\s+.*send_slack',
        r'python3?\s+.*upload', r'python3?\s+.*deliver',
    ]},
    7: {"name": "Self-Anneal", "patterns": [
        r'git\s+add', r'git\s+commit', r'git\s+push',
    ]},
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "completed_phases": [1],  # Phase 1 is always done
        "phase_history": [],
        "warnings_issued": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["phase_history"] = state["phase_history"][-30:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def detect_phase(command):
    """Detect which phase a command belongs to."""
    for phase_num in range(2, 8):
        phase = PHASES[phase_num]
        for pattern in phase.get("patterns", []):
            if re.search(pattern, command, re.IGNORECASE):
                return phase_num
    return None


def get_skipped_phases(current_phase, completed):
    """Get phases that should have been completed before current phase."""
    skipped = []
    for p in range(2, current_phase):
        if p not in completed:
            skipped.append(p)
    return skipped


def handle_status():
    state = load_state()
    print("Phase Ordering Enforcer Status")
    completed = state.get("completed_phases", [1])
    print(f"  Completed phases: {sorted(completed)}")
    print(f"  Warnings issued: {state.get('warnings_issued', 0)}")
    print("  Phase progression:")
    for num in range(1, 8):
        status = "DONE" if num in completed else "pending"
        name = PHASES[num]["name"]
        print(f"    Phase {num}: {name} [{status}]")
    if state.get("phase_history"):
        print("  Recent phase activity:")
        for entry in state["phase_history"][-5:]:
            print(f"    Phase {entry['phase']} ({entry['name']}) - {entry['timestamp'][:19]}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "completed_phases": [1],
        "phase_history": [],
        "warnings_issued": 0,
    }))
    print("Phase Ordering Enforcer: State reset.")
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
        if "tool_result" in data:
            print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    command = tool_input.get("command", "")
    is_post = "tool_result" in data
    detected_phase = detect_phase(command)

    if detected_phase is None:
        if is_post:
            print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    state = load_state()

    if is_post:
        # PostToolUse: track phase completion
        if detected_phase not in state["completed_phases"]:
            state["completed_phases"].append(detected_phase)
        state["phase_history"].append({
            "phase": detected_phase,
            "name": PHASES[detected_phase]["name"],
            "command_snippet": command[:80],
            "timestamp": datetime.now().isoformat(),
        })
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))
    else:
        # PreToolUse: check ordering
        completed = state.get("completed_phases", [1])
        skipped = get_skipped_phases(detected_phase, completed)

        if skipped:
            skipped_names = [f"Phase {p}: {PHASES[p]['name']}" for p in skipped]
            state["warnings_issued"] = state.get("warnings_issued", 0) + 1
            save_state(state)
            sys.stderr.write(
                f"[Phase Ordering] WARNING: Attempting Phase {detected_phase} "
                f"({PHASES[detected_phase]['name']}) but earlier phases may be skipped:\n"
            )
            for name in skipped_names:
                sys.stderr.write(f"  - {name}\n")
            sys.stderr.write(
                "  The DOE flow recommends: Parse -> Capability Check -> "
                "Load Context -> Execute -> Quality Gates -> Delivery -> Self-Anneal\n"
            )
        sys.exit(0)


if __name__ == "__main__":
    main()
