#!/usr/bin/env python3
"""
Hook 49: dependency_chain_validator.py (PreToolUse on Bash)
Before execution scripts, validates that upstream dependencies (files) exist.
Warns if expected input files are missing.
"""

import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "dependency_checks.json"

# Map scripts to their expected upstream files/patterns
DEPENDENCY_MAP = {
    "generate_sales_page.py": {
        "description": "VSL script or research output",
        "patterns": [".tmp/**/vsl_script*", ".tmp/**/research*", ".tmp/**/*vsl*"],
        "check_dirs": [".tmp/"]
    },
    "generate_email_sequence.py": {
        "description": "research output",
        "patterns": [".tmp/**/research*", ".tmp/**/*research*"],
        "check_dirs": [".tmp/"]
    },
    "upload_leads_instantly.py": {
        "description": "validated email list",
        "patterns": [".tmp/**/*lead*", ".tmp/**/*email*", ".tmp/**/*validated*"],
        "check_dirs": [".tmp/"]
    },
    "instantly_create_campaigns.py": {
        "description": "email copy and lead list",
        "patterns": [".tmp/**/*email*", ".tmp/**/*lead*", ".tmp/**/*campaign*"],
        "check_dirs": [".tmp/"]
    },
    "create_google_doc.py": {
        "description": "source markdown file (--file arg)",
        "arg_flag": "--file",
        "check_arg_file": True
    },
    "generate_funnel_copy.py": {
        "description": "research output",
        "patterns": [".tmp/**/research*"],
        "check_dirs": [".tmp/"]
    },
    "generate_sales_page_copy.py": {
        "description": "research or VSL output",
        "patterns": [".tmp/**/research*", ".tmp/**/*vsl*"],
        "check_dirs": [".tmp/"]
    },
    "generate_complete_vsl_funnel.py": {
        "description": "No upstream deps needed (self-contained)",
        "patterns": [],
        "check_dirs": []
    }
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": [], "warnings_issued": 0, "total_checks": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def show_status():
    state = load_state()
    print("=== Dependency Chain Validator ===")
    print(f"Total checks: {state.get('total_checks', 0)}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    checks = state.get("checks", [])
    if checks:
        print("\nRecent checks:")
        for c in checks[-10:]:
            status = "WARN" if c.get("warning") else "OK"
            print(f"  [{status}] {c.get('script', '?')} - {c.get('message', '')}")
    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("State reset.")
    sys.exit(0)


def check_patterns_exist(patterns):
    """Check if any files matching the patterns exist."""
    import fnmatch
    for pattern in patterns:
        base_dir = pattern.split("*")[0].rstrip("/")
        if not base_dir:
            base_dir = "."
        base_path = Path(base_dir)
        if not base_path.exists():
            continue
        # Walk directory looking for matches
        for root, dirs, files in os.walk(base_path):
            for f in files:
                full_path = os.path.join(root, f)
                # Simple check: does the filename contain the key terms?
                for p in patterns:
                    basename_pattern = p.split("/")[-1].replace("*", "")
                    if basename_pattern and basename_pattern in f.lower():
                        return True
    return False


def extract_arg_value(command, flag):
    """Extract value after a flag like --file."""
    patterns = [
        rf'{flag}\s+"([^"]*)"',
        rf"{flag}\s+'([^']*)'",
        rf'{flag}\s+(\S+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            return match.group(1)
    return None


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

    if tool_name not in ("Bash", "bash"):
        sys.exit(0)

    command = tool_input.get("command", "")
    if "python" not in command and "execution/" not in command:
        sys.exit(0)

    state = load_state()
    now = datetime.now().isoformat()

    for script_name, deps in DEPENDENCY_MAP.items():
        if script_name not in command:
            continue

        state["total_checks"] = state.get("total_checks", 0) + 1
        warnings = []

        # Check if specific arg file exists
        if deps.get("check_arg_file"):
            flag = deps.get("arg_flag", "--file")
            file_val = extract_arg_value(command, flag)
            if file_val and not Path(file_val).exists():
                warnings.append(f"Required file '{file_val}' (from {flag}) does not exist")

        # Check pattern-based dependencies
        patterns = deps.get("patterns", [])
        if patterns:
            found = check_patterns_exist(patterns)
            if not found:
                desc = deps.get("description", "upstream files")
                warnings.append(f"Expected {desc} in .tmp/ but none found")

        # Check required directories
        for d in deps.get("check_dirs", []):
            if not Path(d).exists():
                warnings.append(f"Directory '{d}' does not exist")

        check_entry = {
            "script": script_name,
            "timestamp": now,
            "warning": bool(warnings),
            "message": "; ".join(warnings) if warnings else "Dependencies satisfied"
        }
        state["checks"].append(check_entry)
        state["checks"] = state["checks"][-100:]

        if warnings:
            state["warnings_issued"] = state.get("warnings_issued", 0) + 1
            sys.stderr.write(f"[dependency-validator] {script_name}:\n")
            for w in warnings:
                sys.stderr.write(f"  - {w}\n")

        break

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
