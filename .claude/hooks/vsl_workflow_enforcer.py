#!/usr/bin/env python3
"""
Hook 21: VSL Workflow Enforcer (PostToolUse on Bash)

Enforces VSL funnel workflow ordering. When a VSL-related execution script runs,
checks that prerequisite steps were completed:
- generate_vsl_script.py requires: research step done first
- generate_sales_page.py requires: VSL script exists in .tmp/
- generate_email_sequence.py requires: research exists in .tmp/

Tracks state in .tmp/hooks/vsl_workflow_state.json
Warns if prerequisites missing. Never blocks.
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "vsl_workflow_state.json"

VSL_SCRIPTS = {
    "research_company_offer.py": {
        "step": "research",
        "requires": [],
        "description": "Company/offer research"
    },
    "generate_vsl_script.py": {
        "step": "vsl_script",
        "requires": ["research"],
        "description": "VSL script generation"
    },
    "generate_sales_page.py": {
        "step": "sales_page",
        "requires": ["vsl_script"],
        "description": "Sales page generation"
    },
    "generate_email_sequence.py": {
        "step": "email_sequence",
        "requires": ["research"],
        "description": "Email sequence generation"
    },
    "generate_complete_vsl_funnel.py": {
        "step": "complete_funnel",
        "requires": [],
        "description": "Complete VSL funnel (all-in-one)"
    }
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"projects": {}, "global_steps": [], "warnings": []}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_project_name(command):
    """Try to extract project/company name from command arguments."""
    patterns = [
        r'--company\s+"([^"]+)"',
        r"--company\s+'([^']+)'",
        r'--company\s+(\S+)',
        r'--project\s+"([^"]+)"',
        r"--project\s+'([^']+)'",
    ]
    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            return match.group(1).lower().replace(" ", "_")
    return "default"


def check_tmp_for_research():
    """Check if research output exists in .tmp/."""
    tmp_dir = PROJECT_ROOT / ".tmp"
    if not tmp_dir.exists():
        return False
    for f in tmp_dir.rglob("*"):
        if "research" in f.name.lower() and f.is_file():
            return True
    return False


def check_tmp_for_vsl_script():
    """Check if VSL script exists in .tmp/."""
    tmp_dir = PROJECT_ROOT / ".tmp"
    if not tmp_dir.exists():
        return False
    for f in tmp_dir.rglob("*"):
        if ("vsl" in f.name.lower() or "script" in f.name.lower()) and f.is_file():
            if f.suffix in [".md", ".txt", ".json"]:
                return True
    return False


def check_prerequisites(script_name, project_name, state):
    """Check if prerequisites for a script are met."""
    if script_name not in VSL_SCRIPTS:
        return []

    config = VSL_SCRIPTS[script_name]
    missing = []
    completed = state.get("projects", {}).get(project_name, {}).get("completed_steps", [])
    global_steps = state.get("global_steps", [])
    all_completed = set(completed + global_steps)

    for req in config["requires"]:
        if req not in all_completed:
            # Also check .tmp/ directory for artifacts
            if req == "research" and check_tmp_for_research():
                continue
            if req == "vsl_script" and check_tmp_for_vsl_script():
                continue
            missing.append(req)

    return missing


def record_step(script_name, project_name, state):
    """Record a completed workflow step."""
    if script_name not in VSL_SCRIPTS:
        return state

    config = VSL_SCRIPTS[script_name]
    step = config["step"]

    if project_name not in state.get("projects", {}):
        state.setdefault("projects", {})[project_name] = {
            "completed_steps": [],
            "history": []
        }

    project = state["projects"][project_name]
    if step not in project["completed_steps"]:
        project["completed_steps"].append(step)

    if step not in state.get("global_steps", []):
        state.setdefault("global_steps", []).append(step)

    project.setdefault("history", []).append({
        "step": step,
        "script": script_name,
        "timestamp": datetime.now().isoformat()
    })

    return state


def handle_status():
    state = load_state()
    print("=== VSL Workflow Enforcer Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    projects = state.get("projects", {})
    if not projects:
        print("No VSL projects tracked yet.")
    else:
        for name, data in projects.items():
            print(f"\nProject: {name}")
            print(f"  Completed steps: {', '.join(data.get('completed_steps', []))}")
            history = data.get("history", [])
            if history:
                print(f"  Last activity: {history[-1].get('timestamp', 'unknown')}")

    global_steps = state.get("global_steps", [])
    if global_steps:
        print(f"\nGlobal completed steps: {', '.join(global_steps)}")

    warnings = state.get("warnings", [])
    if warnings:
        print(f"\nRecent warnings: {len(warnings)}")
        for w in warnings[-5:]:
            print(f"  - {w}")

    print(f"\nResearch in .tmp/: {check_tmp_for_research()}")
    print(f"VSL script in .tmp/: {check_tmp_for_vsl_script()}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("VSL workflow state reset.")
    else:
        print("No state file to reset.")


def main():
    if "--status" in sys.argv:
        handle_status()
        return
    if "--reset" in sys.argv:
        handle_reset()
        return

    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # PostToolUse mode - must output JSON
    if tool_name != "Bash":
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")

    # Check if this is a VSL-related script
    detected_script = None
    for script_name in VSL_SCRIPTS:
        if script_name in command:
            detected_script = script_name
            break

    if not detected_script:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    project_name = extract_project_name(command)

    # Check prerequisites
    missing = check_prerequisites(detected_script, project_name, state)

    # Record the step
    state = record_step(detected_script, project_name, state)

    if missing:
        warning = (
            f"VSL workflow order: '{detected_script}' ran but prerequisite steps "
            f"not detected: {', '.join(missing)}. Recommended order: research -> "
            f"vsl_script -> sales_page + email_sequence"
        )
        state.setdefault("warnings", []).append(warning)
        save_state(state)
        print(json.dumps({"decision": "ALLOW", "reason": warning}))
    else:
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
