#!/usr/bin/env python3
"""
script_exists_guard.py - PreToolUse hook on Bash tool

Blocks execution of non-existent Python scripts in the execution/ directory.
Prevents confusing errors by catching missing scripts before they run.

Hook Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages to user via sys.stderr.write()
  - NEVER prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show count of scripts in execution/ directory
  --reset   N/A (stateless hook)
"""

import json
import sys
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
EXECUTION_DIR = BASE_DIR / "execution"
SKILLS_DIR = BASE_DIR / ".claude" / "skills"


def extract_script_path(command):
    """Extract the script path from a command like 'python3 execution/foo.py --args'.

    Returns the resolved absolute path to the script, or None if not an execution/skills command.
    """
    # Match python3 execution/script.py or .claude/skills/name/script.py
    # Also handle absolute paths
    match = re.search(r'python3?\s+((?:\S*/)?(?:execution|\.claude/skills/\S+)/\S+\.py)', command)
    if not match:
        return None

    script_ref = match.group(1)

    # If it's already an absolute path, use it directly
    if os.path.isabs(script_ref):
        return script_ref

    # Otherwise, resolve relative to BASE_DIR
    return str(BASE_DIR / script_ref)


def handle_status():
    """Print script directory status and exit."""
    print("Script Exists Guard Status")
    if EXECUTION_DIR.exists():
        scripts = list(EXECUTION_DIR.glob("*.py"))
        print(f"  Scripts in execution/: {len(scripts)}")
        for s in sorted(scripts)[:10]:
            print(f"    - {s.name}")
        if len(scripts) > 10:
            print(f"    ... and {len(scripts) - 10} more")
    else:
        print("  execution/ directory not found!")
    if SKILLS_DIR.exists():
        skill_scripts = list(SKILLS_DIR.glob("*/*.py"))
        print(f"  Scripts in .claude/skills/: {len(skill_scripts)}")
        for s in sorted(skill_scripts)[:10]:
            print(f"    - {s.parent.name}/{s.name}")
        if len(skill_scripts) > 10:
            print(f"    ... and {len(skill_scripts) - 10} more")
    else:
        print("  .claude/skills/ directory not found!")
    sys.exit(0)


def handle_reset():
    """Stateless hook, nothing to reset."""
    print("Script Exists Guard: Stateless hook, nothing to reset.")
    sys.exit(0)


def main():
    # CLI flags
    if "--status" in sys.argv:
        handle_status()
    if "--reset" in sys.argv:
        handle_reset()

    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, IOError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only act on Bash tool
    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")

    # Extract script path
    script_path = extract_script_path(command)
    if not script_path:
        # Not an execution script command, allow
        sys.exit(0)

    # Check if script exists
    if not os.path.isfile(script_path):
        # Derive a helpful relative path for the message
        try:
            rel_path = os.path.relpath(script_path, BASE_DIR)
        except ValueError:
            rel_path = script_path

        sys.stderr.write(
            f"[Script Guard] BLOCKED: Script not found: {rel_path}\n"
            f"  Full path: {script_path}\n"
            f"  Check available scripts:\n"
            f"    ls execution/ | grep -i '<keyword>'\n"
            f"    ls .claude/skills/ | grep -i '<keyword>'\n"
            f"  Or create the script using the Leader Manufacturing process.\n"
        )
        sys.exit(2)

    # Script exists, allow
    sys.exit(0)


if __name__ == "__main__":
    main()
