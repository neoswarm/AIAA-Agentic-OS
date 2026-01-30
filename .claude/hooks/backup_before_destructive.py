#!/usr/bin/env python3
"""
Hook 100: backup_before_destructive.py (PreToolUse on Bash)
Purpose: Ensure backups exist before destructive operations.
Logic: Detect destructive commands (rm, railway down, git reset, database drops).
Check if backup/checkpoint exists. Block if no backup found for destructive
operations on important files.

Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages to user via sys.stderr.write()
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "backup_guard.json"
BACKUP_DIR = Path(".tmp/backups")

# Destructive command patterns
DESTRUCTIVE_PATTERNS = [
    (r'\brm\s+(-[rf]+\s+)?(?!.*\.tmp)', "rm (file deletion)"),
    (r'\brm\s+(-[rf]+\s+)?(directives|execution|skills|clients|context)/', "rm on critical directory"),
    (r'railway\s+down', "railway down (service shutdown)"),
    (r'railway\s+delete', "railway delete (service removal)"),
    (r'git\s+reset\s+--hard', "git reset --hard (discards changes)"),
    (r'git\s+clean\s+-[fd]+', "git clean (removes untracked files)"),
    (r'git\s+checkout\s+\.', "git checkout . (discards all changes)"),
    (r'git\s+restore\s+\.', "git restore . (discards all changes)"),
    (r'DROP\s+(TABLE|DATABASE)', "SQL DROP statement"),
    (r'TRUNCATE\s+TABLE', "SQL TRUNCATE statement"),
    (r'>\s+/dev/null.*2>&1.*&&', "output suppression chain"),
]

# Safe destructive patterns (always allowed)
SAFE_PATTERNS = [
    r'rm\s+(-[rf]+\s+)?\.tmp/',         # .tmp is disposable
    r'rm\s+(-[rf]+\s+)?__pycache__',     # cache cleanup
    r'rm\s+(-[rf]+\s+)?.*\.pyc',         # compiled Python
    r'rm\s+(-[rf]+\s+)?.*\.log',         # log files
    r'rm\s+(-[rf]+\s+)?node_modules',    # node deps
]

# Critical directories that need backup verification
CRITICAL_PATHS = [
    "directives/", "execution/", "skills/", "clients/",
    "context/", "railway_apps/", ".claude/hooks/"
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "blocks": [],
        "allows": [],
        "total_checks": 0,
        "total_blocked": 0,
        "total_allowed": 0,
        "backups_found": []
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_safe_destructive(command):
    """Check if the destructive command targets safe/disposable paths."""
    for pattern in SAFE_PATTERNS:
        if re.search(pattern, command):
            return True
    return False


def detect_destructive(command):
    """Check if a command is destructive. Returns (is_destructive, description)."""
    for pattern, desc in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, desc
    return False, ""


def extract_target_paths(command):
    """Extract file/directory paths from a destructive command."""
    targets = []
    # rm targets
    rm_match = re.search(r'\brm\s+(?:-[rf]+\s+)?(.+)', command)
    if rm_match:
        paths = rm_match.group(1).strip().split()
        targets.extend(p for p in paths if not p.startswith("-"))
    return targets


def check_backup_exists(targets):
    """Check if backups exist for the target paths."""
    if not BACKUP_DIR.exists():
        return False, []

    found_backups = []
    for target in targets:
        target_name = Path(target).name
        # Look for backups matching the target name
        for backup_file in BACKUP_DIR.iterdir():
            if target_name in backup_file.name:
                found_backups.append(str(backup_file))

    return len(found_backups) > 0, found_backups


def targets_critical_path(targets):
    """Check if any target paths are in critical directories."""
    for target in targets:
        for critical in CRITICAL_PATHS:
            if critical in target:
                return True, critical
    return False, ""


def show_status():
    state = load_state()
    print("=== Backup Before Destructive ===")
    print(f"Total checks: {state.get('total_checks', 0)}")
    print(f"Total blocked: {state.get('total_blocked', 0)}")
    print(f"Total allowed: {state.get('total_allowed', 0)}")

    print(f"\nMonitored destructive patterns:")
    for pattern, desc in DESTRUCTIVE_PATTERNS:
        print(f"  - {desc}")

    print(f"\nSafe patterns (always allowed):")
    for pattern in SAFE_PATTERNS:
        print(f"  - {pattern}")

    blocks = state.get("blocks", [])
    if blocks:
        print(f"\nRecent blocks (last {min(5, len(blocks))}):")
        for b in blocks[-5:]:
            print(f"  [{b.get('timestamp', '?')[:19]}] {b.get('description', '?')}")
            print(f"    Command: {b.get('command', '?')[:80]}")

    backups = state.get("backups_found", [])
    if backups:
        print(f"\nBackups found: {len(backups)}")
        for bf in backups[-5:]:
            print(f"  {bf}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Backup before destructive state reset.")
    sys.exit(0)


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
    if not command:
        sys.exit(0)

    state = load_state()
    state["total_checks"] = state.get("total_checks", 0) + 1
    now = datetime.now().isoformat()

    # Check if destructive
    is_destructive, description = detect_destructive(command)
    if not is_destructive:
        save_state(state)
        sys.exit(0)

    # Check if it's a safe destructive operation
    if is_safe_destructive(command):
        state["total_allowed"] = state.get("total_allowed", 0) + 1
        save_state(state)
        sys.exit(0)

    # Extract targets and check criticality
    targets = extract_target_paths(command)
    is_critical, critical_path = targets_critical_path(targets)

    if is_critical:
        # Check for backups
        has_backup, backup_files = check_backup_exists(targets)

        if has_backup:
            state["total_allowed"] = state.get("total_allowed", 0) + 1
            state["backups_found"].extend(backup_files)
            state["backups_found"] = state["backups_found"][-50:]
            save_state(state)
            sys.stderr.write(
                f"[Backup Guard] Backup found for destructive operation on {critical_path}.\n"
                f"  Proceeding with caution.\n"
            )
            sys.exit(0)

        # No backup for critical path - block
        state["total_blocked"] = state.get("total_blocked", 0) + 1
        state["blocks"] = state.get("blocks", [])
        state["blocks"].append({
            "timestamp": now,
            "command": command[:200],
            "description": description,
            "targets": targets,
            "critical_path": critical_path
        })
        state["blocks"] = state["blocks"][-50:]
        save_state(state)

        sys.stderr.write(
            f"[Backup Guard] BLOCKED: {description} on critical path '{critical_path}'.\n"
            f"  No backup found in .tmp/backups/.\n"
            f"  Create a backup first:\n"
            f"    cp -r {critical_path} .tmp/backups/\n"
            f"  Or use git to preserve changes:\n"
            f"    git stash\n"
        )
        sys.exit(2)

    # Non-critical destructive - warn but allow
    state["total_allowed"] = state.get("total_allowed", 0) + 1
    state["allows"] = state.get("allows", [])
    state["allows"].append({
        "timestamp": now,
        "command": command[:200],
        "description": description
    })
    state["allows"] = state["allows"][-50:]
    save_state(state)

    sys.stderr.write(
        f"[Backup Guard] WARNING: Destructive operation detected: {description}.\n"
        f"  Proceeding since target is not in a critical directory.\n"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
