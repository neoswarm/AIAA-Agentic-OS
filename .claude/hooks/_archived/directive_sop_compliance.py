#!/usr/bin/env python3
"""
Hook 78: directive_sop_compliance.py - Dual-mode (Pre+Post on Bash)

Ensures directive steps are followed in order - warns when steps are skipped.
Tracks which directive is active and which steps have been completed.

Dual Mode Detection:
  - "tool_result" exists -> PostToolUse: track step completions
  - "tool_result" missing -> PreToolUse: warn if steps skipped

CLI Flags:
  --status  Show active directive and step progress
  --reset   Clear state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
DIRECTIVES_DIR = BASE_DIR / "directives"
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "sop_compliance.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "active_directive": None,
        "directive_steps": [],
        "completed_steps": [],
        "step_history": [],
        "warnings_issued": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["step_history"] = state["step_history"][-30:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_script_name(command):
    match = re.search(r'python3?\s+(?:\S*/)?execution/(\S+\.py)', command)
    return match.group(1) if match else None


def extract_steps_from_directive(directive_path):
    """Extract ordered steps from a directive's Process section."""
    try:
        content = directive_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    steps = []
    in_process = False

    for line in content.split("\n"):
        stripped = line.strip()
        # Detect process/steps section
        if re.match(r'^#{1,3}\s*(Process|Steps|Workflow Steps|How to Run)', stripped, re.IGNORECASE):
            in_process = True
            continue

        # End of process section (next major header)
        if in_process and re.match(r'^#{1,2}\s+(?!Step|Phase)', stripped) and not re.match(r'^###', stripped):
            break

        if in_process:
            # Look for numbered steps or ### Step headers
            step_match = re.match(r'(?:###?\s*)?(?:Step\s*)?(\d+)[.:)\s]+(.+)', stripped)
            if step_match:
                step_num = int(step_match.group(1))
                step_name = step_match.group(2).strip()
                # Extract script references in step
                script_refs = re.findall(r'execution/(\S+\.py)', step_name + " " + stripped)
                steps.append({
                    "number": step_num,
                    "name": step_name[:80],
                    "scripts": script_refs,
                })

    return steps


def find_step_for_script(script_name, steps):
    """Find which step a script belongs to."""
    for step in steps:
        if script_name in step.get("scripts", []):
            return step["number"]
        # Also check by keyword matching
        script_base = script_name.replace(".py", "").lower()
        step_name_lower = step.get("name", "").lower()
        script_words = set(script_base.split("_"))
        step_words = set(re.findall(r'\w+', step_name_lower))
        if len(script_words & step_words) >= 2:
            return step["number"]
    return None


def load_active_directive_steps():
    """Try to load steps from the most recently read directive."""
    state = load_state()
    directive_name = state.get("active_directive")
    if not directive_name:
        return []
    directive_path = DIRECTIVES_DIR / directive_name
    if directive_path.exists():
        return extract_steps_from_directive(directive_path)
    return []


def handle_status():
    state = load_state()
    print("Directive SOP Compliance Status")
    print(f"  Active directive: {state.get('active_directive', '(none)')}")
    print(f"  Total steps: {len(state.get('directive_steps', []))}")
    print(f"  Completed steps: {state.get('completed_steps', [])}")
    print(f"  Warnings issued: {state.get('warnings_issued', 0)}")
    if state.get("directive_steps"):
        print("  Steps:")
        for step in state["directive_steps"]:
            completed = step["number"] in state.get("completed_steps", [])
            status = "DONE" if completed else "pending"
            print(f"    Step {step['number']}: {step['name']} [{status}]")
    if state.get("step_history"):
        print("  Recent step activity:")
        for entry in state["step_history"][-5:]:
            print(f"    Step {entry.get('step', '?')} - {entry.get('script', '?')}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "active_directive": None, "directive_steps": [],
        "completed_steps": [], "step_history": [], "warnings_issued": 0,
    }))
    print("Directive SOP Compliance: State reset.")
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
    is_post = "tool_result" in data

    # Handle Read tool to detect active directive
    if tool_name == "Read" and is_post:
        file_path = tool_input.get("file_path", "")
        if "directives/" in str(file_path) and str(file_path).endswith(".md"):
            state = load_state()
            directive_name = Path(file_path).name
            directive_path = Path(file_path)
            steps = extract_steps_from_directive(directive_path)
            state["active_directive"] = directive_name
            state["directive_steps"] = steps
            state["completed_steps"] = []
            save_state(state)
        print(json.dumps({"decision": "ALLOW"}))
        return

    if tool_name != "Bash":
        if is_post:
            print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    command = tool_input.get("command", "")
    script_name = extract_script_name(command)
    if not script_name:
        if is_post:
            print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    state = load_state()
    steps = state.get("directive_steps", [])
    completed = state.get("completed_steps", [])

    if not steps:
        if is_post:
            print(json.dumps({"decision": "ALLOW"}))
        else:
            sys.exit(0)
        return

    step_num = find_step_for_script(script_name, steps)

    if is_post:
        # Track completion
        if step_num and step_num not in completed:
            completed.append(step_num)
            state["completed_steps"] = completed
        state["step_history"].append({
            "script": script_name,
            "step": step_num,
            "timestamp": datetime.now().isoformat(),
        })
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))
    else:
        # Check ordering
        if step_num:
            skipped = [s["number"] for s in steps
                       if s["number"] < step_num and s["number"] not in completed]
            if skipped:
                state["warnings_issued"] = state.get("warnings_issued", 0) + 1
                save_state(state)
                skipped_names = []
                for s in steps:
                    if s["number"] in skipped:
                        skipped_names.append(f"Step {s['number']}: {s['name']}")
                sys.stderr.write(
                    f"[SOP Compliance] WARNING: Running step {step_num} ({script_name}) "
                    f"but earlier steps may be skipped:\n"
                )
                for name in skipped_names:
                    sys.stderr.write(f"  - {name}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
