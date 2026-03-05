#!/usr/bin/env python3
"""
Hook 74: directive_script_mapper.py - PostToolUse on Read

When a directive is read, checks that matching execution scripts exist by
parsing the "How to Run" section for script references.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional warnings

CLI Flags:
  --status  Show directive-to-script mappings
  --reset   Clear state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
EXECUTION_DIR = BASE_DIR / "execution"
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "directive_script_mappings.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"mappings": {}, "missing_scripts": [], "total_checks": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_scripts_from_content(content):
    """Extract script references from directive content, especially How to Run section."""
    scripts = []
    # Look for python3 execution/*.py patterns
    matches = re.findall(r'python3?\s+(?:\S*/)?execution/(\S+\.py)', content)
    scripts.extend(matches)
    # Look for execution/*.py references without python3 prefix
    matches = re.findall(r'execution/(\S+\.py)', content)
    scripts.extend(matches)
    return list(set(scripts))


def is_directive_file(file_path):
    """Check if the file path points to a directive."""
    path = str(file_path).lower()
    return "directives/" in path and path.endswith(".md")


def handle_status():
    state = load_state()
    print("Directive-Script Mapper Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Directives mapped: {len(state['mappings'])}")
    print(f"  Missing scripts found: {len(state['missing_scripts'])}")
    if state["mappings"]:
        print("  Mappings:")
        for directive, scripts in list(state["mappings"].items())[-10:]:
            print(f"    {directive}:")
            for s in scripts:
                exists = (EXECUTION_DIR / s).exists()
                status = "EXISTS" if exists else "MISSING"
                print(f"      [{status}] {s}")
    if state["missing_scripts"]:
        print("  Missing scripts:")
        for ms in state["missing_scripts"][-10:]:
            print(f"    - {ms}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"mappings": {}, "missing_scripts": [], "total_checks": 0}))
    print("Directive-Script Mapper: State reset.")
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
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    tool_result = data.get("tool_result", "")

    # Only act on Read tool in PostToolUse mode
    if tool_name != "Read" or "tool_result" not in data:
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    if not is_directive_file(file_path):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    content = str(tool_result) if tool_result else ""
    directive_name = Path(file_path).name
    scripts = extract_scripts_from_content(content)

    if not scripts:
        state["mappings"][directive_name] = []
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))
        return

    state["mappings"][directive_name] = scripts
    missing = []
    for script in scripts:
        script_path = EXECUTION_DIR / script
        if not script_path.exists():
            missing.append(script)
            entry = f"{script} (referenced in {directive_name})"
            if entry not in state["missing_scripts"]:
                state["missing_scripts"].append(entry)

    save_state(state)

    if missing:
        reason = (
            f"Directive {directive_name} references scripts not found in execution/: "
            f"{', '.join(missing)}. These may need to be created."
        )
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
