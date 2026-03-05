#!/usr/bin/env python3
"""
Hook 93: file_path_traversal_guard.py - PreToolUse on Bash

Blocks path traversal attacks in script arguments. Checks for ../../,
URL-encoded traversal, and attempts to access files outside the project.

Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages via sys.stderr.write()
  - Never prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show traversal guard stats
  --reset   Clear state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "path_traversal.json"

# Path traversal patterns
TRAVERSAL_PATTERNS = [
    (r'\.\./\.\./\.\.', "Triple parent directory traversal (../../..)"),
    (r'\.\./\.\./', "Double parent directory traversal (../../)"),
    (r'%2e%2e%2f', "URL-encoded traversal (%2e%2e%2f)"),
    (r'%2e%2e/', "Partially encoded traversal (%2e%2e/)"),
    (r'%252e%252e', "Double-encoded traversal"),
    (r'\.\.%2f', "Mixed-encoded traversal (..%2f)"),
    (r'%2e%2e\\', "Windows-encoded traversal"),
    (r'\.\.[/\\]', "Basic traversal pattern"),
]

# Sensitive directories outside project
SENSITIVE_PATHS = [
    "/etc/", "/root/", "/var/", "/usr/",
    "/System/", "/Library/", "/private/",
    "~/.ssh", "~/.aws", "~/.config",
    "/home/", "/opt/",
]

# Safe command patterns (these often contain .. but are safe)
SAFE_PATTERNS = [
    r'cd\s+\.\.',       # cd .. is normal navigation
    r'git\s+',          # git commands may reference parent
    r'pip\s+install',   # pip install paths
    r'npm\s+',          # npm commands
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "blocked_attempts": [],
        "total_blocks": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["blocked_attempts"] = state["blocked_attempts"][-20:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_safe_command(command):
    """Check if the command is known safe despite containing traversal-like patterns."""
    for pattern in SAFE_PATTERNS:
        if re.match(pattern, command.strip()):
            return True
    return False


def check_traversal(command):
    """Check command for path traversal patterns."""
    issues = []
    command_lower = command.lower()

    for pattern, description in TRAVERSAL_PATTERNS:
        if re.search(pattern, command_lower):
            issues.append(description)

    return issues


def check_sensitive_paths(command):
    """Check if command tries to access sensitive paths outside the project."""
    issues = []

    for sensitive in SENSITIVE_PATHS:
        if sensitive in command:
            issues.append(f"Access to sensitive path: {sensitive}")

    # Check for absolute paths outside project
    abs_paths = re.findall(r'(?:^|\s)(/[^\s]+)', command)
    for path in abs_paths:
        try:
            resolved = os.path.realpath(path)
            project_resolved = os.path.realpath(str(BASE_DIR))
            if not resolved.startswith(project_resolved) and os.path.exists(resolved):
                # Only flag if the path actually exists and is outside project
                issues.append(f"Path outside project: {path}")
        except (OSError, ValueError):
            pass

    return issues


def handle_status():
    state = load_state()
    print("File Path Traversal Guard Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Total blocks: {state['total_blocks']}")
    if state["blocked_attempts"]:
        print("  Blocked attempts:")
        for ba in state["blocked_attempts"][-5:]:
            print(f"    [{ba.get('timestamp', '')[:19]}] {ba.get('reason', 'unknown')}")
            print(f"      Command: {ba.get('command', '')[:80]}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "blocked_attempts": [], "total_blocks": 0, "total_checks": 0,
    }))
    print("File Path Traversal Guard: State reset.")
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
        sys.exit(0)

    command = tool_input.get("command", "")
    if not command:
        sys.exit(0)

    state = load_state()
    state["total_checks"] += 1

    # Skip safe commands
    if is_safe_command(command):
        save_state(state)
        sys.exit(0)

    all_issues = []

    traversal_issues = check_traversal(command)
    all_issues.extend(traversal_issues)

    sensitive_issues = check_sensitive_paths(command)
    all_issues.extend(sensitive_issues)

    if all_issues:
        state["total_blocks"] += 1
        state["blocked_attempts"].append({
            "command": command[:200],
            "reason": "; ".join(all_issues[:3]),
            "timestamp": datetime.now().isoformat(),
        })
        save_state(state)

        sys.stderr.write(
            f"[Path Traversal Guard] BLOCKED: This file path was blocked for safety.\n"
            f"  The system can only access files within the project directory.\n"
        )
        sys.exit(2)

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
