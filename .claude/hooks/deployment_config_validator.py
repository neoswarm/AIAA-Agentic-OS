#!/usr/bin/env python3
"""
Hook 58: deployment_config_validator.py (PreToolUse on Bash)
Before railway up, checks for required deployment files (Procfile, requirements.txt, etc.).
"""

import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "deployment_config_checks.json"

REQUIRED_FILES = {
    "Procfile": "Your startup configuration is missing — the server won't know how to start your app",
    "requirements.txt": "Required software packages are missing — your app's dependencies won't be installed",
}

RECOMMENDED_FILES = {
    "railway.json": "Consider adding railway.json for build configuration",
}

ENTRY_POINTS = ["app.py", "main.py", "server.py", "wsgi.py"]


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
    print("=== Deployment Config Validator ===")
    print(f"Checks performed: {len(state.get('checks', []))}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    print(f"\nRequired files: {', '.join(REQUIRED_FILES.keys())}")
    print(f"Recommended files: {', '.join(RECOMMENDED_FILES.keys())}")
    print(f"Expected entry points: {', '.join(ENTRY_POINTS)}")
    checks = state.get("checks", [])
    if checks:
        print("\nRecent checks:")
        for c in checks[-5:]:
            status = "WARN" if c.get("missing") else "OK"
            print(f"  [{status}] {c.get('directory', '?')} - {c.get('message', '')}")
    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("State reset.")
    sys.exit(0)


def detect_deploy_directory(command):
    """Determine which directory the deployment is from."""
    # Check for cd command
    cd_match = re.search(r'cd\s+["\']?([^"\';&]+)', command)
    if cd_match:
        return cd_match.group(1).strip()
    # Default to current directory
    return "."


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
    if "railway up" not in command:
        sys.exit(0)

    state = load_state()
    now = datetime.now().isoformat()

    deploy_dir = detect_deploy_directory(command)
    deploy_path = Path(deploy_dir)

    missing = []
    warnings = []

    # Check required files
    for filename, reason in REQUIRED_FILES.items():
        if not (deploy_path / filename).exists():
            missing.append(filename)
            warnings.append(f"No {filename} found. {reason}.")

    # Check recommended files
    for filename, reason in RECOMMENDED_FILES.items():
        if not (deploy_path / filename).exists():
            warnings.append(reason)

    # Check for entry point
    has_entry = any((deploy_path / ep).exists() for ep in ENTRY_POINTS)
    if not has_entry:
        warnings.append(f"No entry point found ({', '.join(ENTRY_POINTS)})")

    check_entry = {
        "timestamp": now,
        "directory": str(deploy_dir),
        "missing": missing,
        "message": "; ".join(warnings) if warnings else "All deployment files present"
    }
    state["checks"].append(check_entry)
    state["checks"] = state["checks"][-50:]

    if warnings:
        state["warnings_issued"] = state.get("warnings_issued", 0) + 1
        sys.stderr.write(f"[deploy-config-check] Deployment directory: {deploy_dir}\n")
        for w in warnings:
            sys.stderr.write(f"  - {w}\n")
        sys.stderr.write(f"  These files are usually created automatically. If they're missing, ask Claude to set up your deployment.\n")

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
