#!/usr/bin/env python3
"""
Hook 97: dead_directive_detector.py (PostToolUse on Read)
Purpose: When browsing directives, flag ones with no matching execution scripts.
Logic: When reading a directive, parse "How to Run" section for script references.
Check if those scripts exist. Track dead directives (no scripts found) in state.

Protocol:
  - PostToolUse: prints JSON to stdout {"decision": "ALLOW"} or {"decision": "BLOCK", "reason": "..."}
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "dead_directives.json"
EXECUTION_DIR = Path("execution")


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "dead_directives": {},
        "healthy_directives": {},
        "total_scanned": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_script_references(content):
    """Parse directive content for execution script references."""
    scripts = []
    if not content:
        return scripts

    # Match execution/script_name.py patterns
    for match in re.finditer(r'execution/([a-zA-Z0-9_-]+\.py)', content):
        script = match.group(1)
        if script not in scripts:
            scripts.append(script)

    # Match python3 execution/script patterns
    for match in re.finditer(r'python3?\s+execution/([a-zA-Z0-9_-]+\.py)', content):
        script = match.group(1)
        if script not in scripts:
            scripts.append(script)

    return scripts


def check_scripts_exist(scripts):
    """Check which referenced scripts actually exist."""
    existing = []
    missing = []
    for script in scripts:
        script_path = EXECUTION_DIR / script
        if script_path.exists():
            existing.append(script)
        else:
            missing.append(script)
    return existing, missing


def extract_directive_name(file_path):
    """Extract directive name from file path."""
    match = re.search(r'directives/(.+?)\.md', file_path)
    if match:
        return match.group(1)
    return None


def show_status():
    state = load_state()
    dead = state.get("dead_directives", {})
    healthy = state.get("healthy_directives", {})

    print("=== Dead Directive Detector ===")
    print(f"Total directives scanned: {state.get('total_scanned', 0)}")
    print(f"Healthy directives: {len(healthy)}")
    print(f"Dead directives: {len(dead)}")

    if dead:
        print("\nDead directives (no matching scripts):")
        for name, info in sorted(dead.items()):
            missing = info.get("missing_scripts", [])
            referenced = info.get("referenced_scripts", [])
            last_seen = info.get("last_scanned", "?")[:19]
            print(f"\n  {name} (scanned: {last_seen})")
            if referenced:
                print(f"    Referenced scripts: {', '.join(referenced)}")
            if missing:
                print(f"    Missing scripts: {', '.join(missing)}")
            if not referenced:
                print(f"    No script references found in directive")

    if healthy:
        print(f"\nHealthy directives (last {min(10, len(healthy))}):")
        sorted_healthy = sorted(healthy.items(), key=lambda x: x[1].get("last_scanned", ""), reverse=True)
        for name, info in sorted_healthy[:10]:
            scripts = info.get("existing_scripts", [])
            print(f"  {name}: {', '.join(scripts)}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Dead directive detector state reset.")
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

    # Only act on Read tool
    if tool_name not in ("Read", "read"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    if "directives/" not in file_path or not file_path.endswith(".md"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    directive_name = extract_directive_name(file_path)
    if not directive_name:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_scanned"] = state.get("total_scanned", 0) + 1
    now = datetime.now().isoformat()

    # Parse content for script references
    content = str(tool_result) if tool_result else ""
    referenced_scripts = extract_script_references(content)

    if not referenced_scripts:
        # No script references found - this is a dead directive
        state["dead_directives"][directive_name] = {
            "referenced_scripts": [],
            "missing_scripts": [],
            "last_scanned": now,
            "reason": "no_script_references"
        }
        # Remove from healthy if it was there
        state.get("healthy_directives", {}).pop(directive_name, None)
        save_state(state)

        output = {
            "decision": "ALLOW",
            "reason": f"[Dead Directive] '{directive_name}' has no execution script references. Consider adding a 'How to Run' section."
        }
        print(json.dumps(output))
        return

    # Check which scripts exist
    existing, missing = check_scripts_exist(referenced_scripts)

    if missing and not existing:
        # All referenced scripts are missing - dead directive
        state["dead_directives"][directive_name] = {
            "referenced_scripts": referenced_scripts,
            "missing_scripts": missing,
            "last_scanned": now,
            "reason": "all_scripts_missing"
        }
        state.get("healthy_directives", {}).pop(directive_name, None)
        save_state(state)

        output = {
            "decision": "ALLOW",
            "reason": f"[Dead Directive] '{directive_name}' references scripts that don't exist: {', '.join(missing)}"
        }
        print(json.dumps(output))
        return

    if missing:
        # Some scripts missing - partially dead
        state["dead_directives"][directive_name] = {
            "referenced_scripts": referenced_scripts,
            "missing_scripts": missing,
            "existing_scripts": existing,
            "last_scanned": now,
            "reason": "partial_scripts_missing"
        }
        state.get("healthy_directives", {}).pop(directive_name, None)
        save_state(state)

        output = {
            "decision": "ALLOW",
            "reason": f"[Dead Directive] '{directive_name}' has missing scripts: {', '.join(missing)} (existing: {', '.join(existing)})"
        }
        print(json.dumps(output))
        return

    # All scripts exist - healthy
    healthy = state.get("healthy_directives", {})
    healthy[directive_name] = {
        "existing_scripts": existing,
        "last_scanned": now
    }
    state["healthy_directives"] = healthy
    # Remove from dead if it was there
    state.get("dead_directives", {}).pop(directive_name, None)

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
