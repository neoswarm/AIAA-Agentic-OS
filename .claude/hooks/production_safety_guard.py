#!/usr/bin/env python3
"""
Hook 59: production_safety_guard.py (PreToolUse on Bash)
Extra warnings for production-affecting commands.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "production_safety.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": [], "warnings_issued": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def show_status():
    state = load_state()
    print("=== Production Safety Guard ===")
    print(f"Commands checked: {len(state.get('checks', []))}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    checks = state.get("checks", [])
    if checks:
        print("\nRecent warnings:")
        for c in checks[-10:]:
            if c.get("warnings"):
                for w in c["warnings"]:
                    print(f"  [{c.get('timestamp', '?')[:19]}] {w}")
    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("State reset.")
    sys.exit(0)


def check_command(command):
    """Check for production-affecting patterns."""
    warnings = []

    # railway up without --detach
    if "railway up" in command and "--detach" not in command:
        warnings.append("Consider using --detach to avoid blocking the terminal")

    # git push to main/master
    push_match = re.search(r'git\s+push\s+\S+\s+(main|master)', command)
    if push_match:
        warnings.append(f"Pushing to {push_match.group(1)} branch")
    elif "git push" in command and ("main" in command or "master" in command):
        warnings.append("Pushing to main/master branch")

    # rm -rf on project directories
    rm_match = re.search(r'rm\s+-rf?\s+["\']?([^"\';&\s]+)', command)
    if rm_match:
        target = rm_match.group(1)
        dangerous_dirs = [
            "directives", "execution", "skills", "context", "clients",
            "railway_apps", ".claude", ".git"
        ]
        for d in dangerous_dirs:
            if d in target:
                warnings.append(f"Destructive command on project directory: {target}")
                break

    # railway variables set for dashboard
    if "railway variables set" in command and ("dashboard" in command.lower() or "DASHBOARD" in command):
        warnings.append("Modifying dashboard environment variables")

    # Force flags
    if re.search(r'\s--force\b', command) or re.search(r'\s-f\b', command):
        # Exclude common safe uses of -f
        if "rm" not in command and "tail" not in command and "tee" not in command:
            warnings.append("Force flag detected")

    # git push --force
    if "git push" in command and ("--force" in command or "-f" in command):
        warnings.append("Force pushing to remote - this rewrites history!")

    # DROP TABLE / DELETE FROM (SQL)
    if re.search(r'DROP\s+TABLE', command, re.IGNORECASE):
        warnings.append("SQL DROP TABLE detected")
    if re.search(r'DELETE\s+FROM', command, re.IGNORECASE):
        warnings.append("SQL DELETE FROM detected")

    return warnings


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
    warnings = check_command(command)

    if not warnings:
        sys.exit(0)

    state = load_state()
    now = datetime.now().isoformat()

    state["warnings_issued"] = state.get("warnings_issued", 0) + 1
    check_entry = {
        "timestamp": now,
        "command": command[:150],
        "warnings": warnings
    }
    state["checks"].append(check_entry)
    state["checks"] = state["checks"][-100:]

    sys.stderr.write(f"[production-safety] Warnings:\n")
    for w in warnings:
        sys.stderr.write(f"  - {w}\n")

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
