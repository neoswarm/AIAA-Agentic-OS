#!/usr/bin/env python3
"""
Hook 94: command_injection_guard.py - PreToolUse on Bash

Blocks shell injection in script arguments. Checks for backticks, $(),
pipe to sh/bash, semicolons in quoted args, and && after variable expansion.

Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages via sys.stderr.write()
  - Never prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show injection guard stats
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
STATE_FILE = STATE_DIR / "command_injection.json"

# Only check commands that run execution scripts with arguments
EXEC_PATTERN = re.compile(r'python3?\s+(?:\S*/)?execution/\S+\.py\s+(.+)', re.DOTALL)

# Injection patterns to check within script arguments
INJECTION_PATTERNS = [
    (r'`[^`]+`', "Backtick command substitution in arguments"),
    (r'\$\([^)]+\)', "Command substitution $() in arguments"),
    (r'\|\s*(?:sh|bash|zsh|ksh|csh|dash|fish)\b', "Pipe to shell interpreter"),
    (r'\|\s*(?:python|perl|ruby|node)\b', "Pipe to script interpreter"),
    (r';\s*(?:rm|del|chmod|chown|sudo|curl|wget|nc|ncat)\b', "Dangerous command after semicolon"),
    (r'&&\s*(?:rm|del|chmod|chown|sudo|curl|wget|nc)\b', "Dangerous command after &&"),
    (r'\$\{[^}]*\}', "Variable expansion ${} in arguments (check if intended)"),
    (r'>\s*/(?:etc|tmp|var|dev)', "Redirect to system directory"),
    (r'\|\s*tee\s+/(?:etc|tmp|var)', "Tee to system directory"),
    (r'eval\s+', "eval command detected"),
    (r'exec\s+\d*[<>]', "exec with redirection"),
    (r'source\s+', "source command in arguments"),
]

# Safe patterns that should not trigger
SAFE_COMMAND_PATTERNS = [
    r'^python3?\s+execution/\S+\.py\s+--\w+\s+"[^"]*"\s*$',  # Simple quoted args
    r'^python3?\s+execution/\S+\.py\s+--\w+\s+\S+\s*$',       # Simple unquoted args
    r'^ls\s+', r'^cat\s+', r'^head\s+', r'^tail\s+',
    r'^git\s+', r'^railway\s+', r'^curl\s+',
    r'^pip\s+', r'^npm\s+',
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


def extract_args(command):
    """Extract the arguments portion of an execution command."""
    match = EXEC_PATTERN.search(command)
    if match:
        return match.group(1)
    return None


def check_injection(args_str):
    """Check arguments for injection patterns."""
    issues = []
    for pattern, description in INJECTION_PATTERNS:
        if re.search(pattern, args_str):
            issues.append(description)
    return issues


def is_known_safe(command):
    """Check if the full command matches a known safe pattern."""
    for pattern in SAFE_COMMAND_PATTERNS:
        if re.match(pattern, command.strip()):
            return True
    return False


def handle_status():
    state = load_state()
    print("Command Injection Guard Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Total blocks: {state['total_blocks']}")
    if state["blocked_attempts"]:
        print("  Blocked attempts:")
        for ba in state["blocked_attempts"][-5:]:
            print(f"    [{ba.get('timestamp', '')[:19]}] {ba.get('reason', 'unknown')}")
            print(f"      Command: {ba.get('command', '')[:80]}")
    else:
        print("  No blocked attempts.")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "blocked_attempts": [], "total_blocks": 0, "total_checks": 0,
    }))
    print("Command Injection Guard: State reset.")
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

    # Only deeply inspect execution script commands with arguments
    args = extract_args(command)
    if not args:
        # Not an execution script command, do basic check
        # Check for really obvious injection in any command
        obvious_patterns = [
            (r';\s*rm\s+-rf\s+/', "Destructive rm -rf on root"),
            (r';\s*dd\s+if=', "dd command after semicolon"),
            (r'\|\s*bash\s*$', "Pipe to bash"),
        ]
        for pattern, description in obvious_patterns:
            if re.search(pattern, command):
                state["total_blocks"] += 1
                state["blocked_attempts"].append({
                    "command": command[:200],
                    "reason": description,
                    "timestamp": datetime.now().isoformat(),
                })
                save_state(state)
                sys.stderr.write(
                    f"[Injection Guard] BLOCKED: {description}\n"
                    f"  Command: {command[:100]}\n"
                )
                sys.exit(2)
        save_state(state)
        sys.exit(0)

    # Check execution script arguments for injection
    issues = check_injection(args)

    if issues:
        state["total_blocks"] += 1
        state["blocked_attempts"].append({
            "command": command[:200],
            "reason": "; ".join(issues[:3]),
            "timestamp": datetime.now().isoformat(),
        })
        save_state(state)

        sys.stderr.write(
            f"[Injection Guard] BLOCKED: Potential command injection in script arguments\n"
            f"  Issues: {'; '.join(issues[:3])}\n"
            f"  Arguments: {args[:100]}\n"
            f"  Script arguments should be simple strings, not shell commands.\n"
        )
        sys.exit(2)

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
