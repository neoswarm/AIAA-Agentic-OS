#!/usr/bin/env python3
"""
Hook 47: git_commit_message_validator.py (PreToolUse on Bash)
Validates git commit messages follow conventions.
Warns but never blocks git operations.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "commit_message_stats.json"

VALID_PREFIXES = [
    "Self-anneal:", "Add:", "Update:", "Fix:", "Deploy:",
    "Refactor:", "Remove:", "Merge:", "Docs:", "Test:",
    "Clean:", "Feat:", "Chore:", "Style:", "Perf:"
]

BAD_PATTERNS = ["WIP", "temp", "asdf", "test123", "xxx", "TODO", "fixme"]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"total_commits": 0, "valid_commits": 0, "warnings": []}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def show_status():
    state = load_state()
    total = state.get("total_commits", 0)
    valid = state.get("valid_commits", 0)
    print("=== Git Commit Message Validation ===")
    print(f"Total commits checked: {total}")
    print(f"Valid commits: {valid}")
    print(f"Invalid commits: {total - valid}")
    if total > 0:
        print(f"Compliance rate: {valid / total * 100:.1f}%")
    warnings = state.get("warnings", [])
    if warnings:
        print("\nRecent warnings:")
        for w in warnings[-5:]:
            print(f"  - [{w.get('timestamp', '?')}] {w.get('issue', '?')}")
    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("State reset.")
    sys.exit(0)


def extract_commit_message(command):
    """Extract commit message from git commit -m '...' or -m \"...\" command."""
    # Match -m followed by quoted string
    patterns = [
        r'-m\s+"([^"]*)"',
        r"-m\s+'([^']*)'",
        r'-m\s+"([^"]*(?:\\"[^"]*)*)"',
        r'-m\s+(\S+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            return match.group(1)

    # Check for heredoc pattern: -m "$(cat <<'EOF' ... EOF)"
    heredoc_match = re.search(r"cat\s+<<['\"]?EOF['\"]?\n(.*?)\nEOF", command, re.DOTALL)
    if heredoc_match:
        return heredoc_match.group(1).strip()

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
    if "git commit" not in command:
        sys.exit(0)

    state = load_state()
    state["total_commits"] = state.get("total_commits", 0) + 1
    now = datetime.now().isoformat()
    issues = []

    message = extract_commit_message(command)

    if message is None:
        # Could be interactive or --amend without -m, skip
        state["valid_commits"] = state.get("valid_commits", 0) + 1
        save_state(state)
        sys.exit(0)

    # Validate message
    if not message.strip():
        issues.append("Commit message is empty")

    if len(message.strip()) < 10:
        issues.append(f"Commit message too short ({len(message.strip())} chars, minimum 10)")

    has_valid_prefix = any(message.strip().startswith(prefix) for prefix in VALID_PREFIXES)
    if not has_valid_prefix and message.strip():
        prefix_list = ", ".join(VALID_PREFIXES[:7])
        issues.append(f"Message should start with a category: {prefix_list}")

    for bad in BAD_PATTERNS:
        if bad.lower() in message.lower():
            issues.append(f"Message contains '{bad}' - use a more descriptive message")
            break

    if issues:
        state["warnings"].append({
            "timestamp": now,
            "message": message[:80],
            "issue": "; ".join(issues)
        })
        state["warnings"] = state["warnings"][-50:]
        sys.stderr.write(f"[commit-validator] Commit message issues:\n")
        for issue in issues:
            sys.stderr.write(f"  - {issue}\n")
        sys.stderr.write(f"  Message: \"{message[:80]}\"\n")
    else:
        state["valid_commits"] = state.get("valid_commits", 0) + 1

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
