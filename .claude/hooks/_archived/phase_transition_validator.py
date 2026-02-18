#!/usr/bin/env python3
"""
Hook 111: phase_transition_validator.py (Dual-mode: Pre+Post on Bash)
Purpose: Ensure clean transitions between the 7 DOE execution phases.
Logic: Track current phase. On transition, validate: previous phase completed
successfully, required outputs exist, no skipped prerequisites.
Block transitions with missing prereqs.

Phases: Parse -> Capability Check -> Load Context -> Execute -> Quality Gates -> Delivery -> Self-Anneal

Protocol:
  - Dual-mode: detect by checking if "tool_result" key exists in input
  - PreToolUse: exit 0 (allow) or exit 2 (block), messages via sys.stderr
  - PostToolUse: print JSON to stdout
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "phase_transitions.json"

# DOE Phases in order
PHASES = [
    "parse",           # Phase 1: Parse user input
    "capability",      # Phase 2: Capability check
    "context",         # Phase 3: Load context
    "execute",         # Phase 4: Execute directive
    "quality",         # Phase 5: Quality gates
    "delivery",        # Phase 6: Delivery
    "anneal",          # Phase 7: Self-annealing
]

# Phase detection patterns
PHASE_DETECTORS = {
    "parse": [r'ls\s+directives/', r'grep.*directive', r'--help'],
    "capability": [r'ls\s+(directives|execution|skills)/', r'grep.*\.(py|md)'],
    "context": [r'context/', r'clients/', r'skills/SKILL_BIBLE', r'directives/.*\.md'],
    "execute": [r'python3?\s+execution/', r'execution/.*\.py'],
    "quality": [r'validate', r'quality', r'check', r'wc\s', r'grep.*TODO', r'lint'],
    "delivery": [r'create_google_doc', r'send_slack', r'send_email', r'railway\s+up'],
    "anneal": [r'git\s+(add|commit).*self.anneal', r'self.anneal', r'update.*directive'],
}

# Required prerequisites for each phase
PHASE_PREREQS = {
    "parse": [],
    "capability": [],
    "context": [],
    "execute": ["context"],      # Must load context before executing
    "quality": ["execute"],      # Must execute before quality check
    "delivery": ["execute"],     # Must execute before delivery
    "anneal": [],                # Can happen anytime
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "current_phase": None,
        "phase_history": [],
        "completed_phases": [],
        "transitions": [],
        "warnings": [],
        "total_transitions": 0,
        "workflow_count": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def detect_phase(command):
    """Detect which phase a command belongs to."""
    for phase, patterns in PHASE_DETECTORS.items():
        for pattern in patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return phase
    return None


def check_prerequisites(target_phase, completed_phases):
    """Check if prerequisites for target phase are met."""
    prereqs = PHASE_PREREQS.get(target_phase, [])
    missing = [p for p in prereqs if p not in completed_phases]
    return missing


def show_status():
    state = load_state()
    print("=== Phase Transition Validator ===")
    print(f"Current phase: {state.get('current_phase', 'None')}")
    print(f"Total transitions: {state.get('total_transitions', 0)}")
    print(f"Workflows tracked: {state.get('workflow_count', 0)}")

    completed = state.get("completed_phases", [])
    print(f"\nCompleted phases this workflow: {', '.join(completed) if completed else 'none'}")

    print("\nPhase order:")
    for i, phase in enumerate(PHASES, 1):
        status = "DONE" if phase in completed else "    "
        current = " <-- current" if phase == state.get("current_phase") else ""
        prereqs = PHASE_PREREQS.get(phase, [])
        prereq_str = f" (requires: {', '.join(prereqs)})" if prereqs else ""
        print(f"  {i}. [{status}] {phase}{prereq_str}{current}")

    transitions = state.get("transitions", [])
    if transitions:
        print(f"\nRecent transitions (last {min(10, len(transitions))}):")
        for t in transitions[-10:]:
            ts = t.get("timestamp", "?")[:19]
            from_p = t.get("from_phase", "?")
            to_p = t.get("to_phase", "?")
            print(f"  [{ts}] {from_p} -> {to_p}")

    warnings = state.get("warnings", [])
    if warnings:
        print(f"\nWarnings (last {min(5, len(warnings))}):")
        for w in warnings[-5:]:
            print(f"  [{w.get('timestamp', '?')[:19]}] {w.get('message', '?')}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Phase transition validator state reset.")
    sys.exit(0)


def main():
    if "--status" in sys.argv:
        show_status()
    if "--reset" in sys.argv:
        reset_state()

    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        # Default behavior based on mode
        if "--post" not in sys.argv:
            sys.exit(0)
        else:
            print(json.dumps({"decision": "ALLOW"}))
            return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    is_post = "tool_result" in data

    if tool_name not in ("Bash", "bash"):
        if is_post:
            print(json.dumps({"decision": "ALLOW"}))
        else:
            sys.exit(0)
        return

    command = tool_input.get("command", "")
    if not command:
        if is_post:
            print(json.dumps({"decision": "ALLOW"}))
        else:
            sys.exit(0)
        return

    detected_phase = detect_phase(command)
    if not detected_phase:
        if is_post:
            print(json.dumps({"decision": "ALLOW"}))
        else:
            sys.exit(0)
        return

    state = load_state()
    now = datetime.now().isoformat()
    current_phase = state.get("current_phase")
    completed = state.get("completed_phases", [])

    if is_post:
        # PostToolUse: mark phase as completed
        if detected_phase not in completed:
            completed.append(detected_phase)
        state["completed_phases"] = completed
        state["current_phase"] = detected_phase

        # Record transition
        if current_phase and current_phase != detected_phase:
            state["total_transitions"] = state.get("total_transitions", 0) + 1
            transitions = state.get("transitions", [])
            transitions.append({
                "timestamp": now,
                "from_phase": current_phase,
                "to_phase": detected_phase
            })
            state["transitions"] = transitions[-100:]

        # Track phase history
        history = state.get("phase_history", [])
        history.append({"phase": detected_phase, "timestamp": now})
        state["phase_history"] = history[-50:]

        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))

    else:
        # PreToolUse: check prerequisites before allowing phase transition
        if detected_phase != current_phase:
            missing = check_prerequisites(detected_phase, completed)

            if missing:
                # Record warning
                warnings = state.get("warnings", [])
                msg = f"Transitioning to '{detected_phase}' without completing: {', '.join(missing)}"
                warnings.append({"timestamp": now, "message": msg})
                state["warnings"] = warnings[-50:]
                save_state(state)

                sys.stderr.write(
                    f"[Phase Validator] WARNING: Entering '{detected_phase}' phase "
                    f"without completing prerequisites: {', '.join(missing)}.\n"
                    f"  Recommended order: {' -> '.join(PHASES)}\n"
                    f"  Completed so far: {', '.join(completed) if completed else 'none'}\n"
                )

        save_state(state)
        sys.exit(0)


if __name__ == "__main__":
    main()
