#!/usr/bin/env python3
"""
Hook 20: Session Activity Logger
Type: PostToolUse on Bash tool
Tier: Passive (always allows, logs silently)

Logs all significant bash activities to .tmp/hooks/session_activity.json.
Categorizes commands by type (workflow_execution, railway_operation,
git_operation, python_script, api_call) and skips trivial commands.
Tracks session start time and duration. Keeps last 1000 entries.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {...}, "tool_result": "..."}
  - Prints JSON to stdout: {"decision": "ALLOW"}
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


STATE_DIR = Path("/Users/lucasnolan/Agentic OS/.tmp/hooks")
ACTIVITY_FILE = STATE_DIR / "session_activity.json"
MAX_ENTRIES = 1000

# Trivial commands to skip
TRIVIAL_COMMANDS = {
    "ls", "pwd", "echo", "cat", "head", "tail", "wc", "whoami",
    "date", "which", "type", "file", "true", "false", "test",
    "cd", "clear", "history", "env", "printenv", "set",
}


def load_activity():
    """Load session activity data."""
    try:
        if ACTIVITY_FILE.exists():
            with open(ACTIVITY_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "session_start": None,
        "entries": [],
    }


def save_activity(data):
    """Save session activity data, trimming to MAX_ENTRIES."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    entries = data.get("entries", [])
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]
        data["entries"] = entries
    with open(ACTIVITY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def is_trivial(command: str) -> bool:
    """Check if command is trivial and should be skipped."""
    # Get the first word (base command)
    stripped = command.strip()
    if not stripped:
        return True

    # Handle piped/chained commands - check the first command
    first_cmd = stripped.split("|")[0].split("&&")[0].split(";")[0].strip()
    base = first_cmd.split()[0] if first_cmd.split() else ""

    # Strip path prefix
    base = os.path.basename(base)

    return base in TRIVIAL_COMMANDS


def classify_command(command: str) -> tuple:
    """Classify command into type and extract relevant info.
    Returns (type, summary).
    """
    stripped = command.strip()

    # Workflow execution
    if re.search(r'python3?\s+(?:.*?/)?execution/\S+\.py', stripped):
        match = re.search(r'execution/(\S+\.py)', stripped)
        script = match.group(1) if match else "unknown"
        return ("workflow_execution", f"execution/{script}")

    # Railway operations
    if re.match(r'railway\s+', stripped):
        parts = stripped.split()
        subcommand = parts[1] if len(parts) > 1 else "unknown"
        return ("railway_operation", f"railway {subcommand}")

    # Git operations
    if re.match(r'git\s+', stripped):
        parts = stripped.split()
        subcommand = parts[1] if len(parts) > 1 else "unknown"
        return ("git_operation", f"git {subcommand}")

    # Other Python scripts
    if re.search(r'python3?\s+', stripped):
        match = re.search(r'python3?\s+(\S+)', stripped)
        script = match.group(1) if match else "unknown"
        return ("python_script", script)

    # API calls (curl)
    if re.match(r'curl\s+', stripped):
        # Extract URL domain
        url_match = re.search(r'https?://([^\s/]+)', stripped)
        domain = url_match.group(1) if url_match else "unknown"
        return ("api_call", f"curl {domain}")

    # Pip/npm operations
    if re.match(r'(pip|pip3|npm|yarn)\s+', stripped):
        parts = stripped.split()
        return ("package_manager", f"{parts[0]} {parts[1] if len(parts) > 1 else ''}")

    # Docker operations
    if re.match(r'docker\s+', stripped):
        parts = stripped.split()
        subcommand = parts[1] if len(parts) > 1 else "unknown"
        return ("docker_operation", f"docker {subcommand}")

    # Generic significant command
    parts = stripped.split()
    base = parts[0] if parts else "unknown"
    return ("other", base)


def compute_duration(session_start: str) -> str:
    """Compute human-readable session duration."""
    if not session_start:
        return "unknown"
    try:
        start = datetime.fromisoformat(session_start)
        now = datetime.now(timezone.utc)
        delta = now - start
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except (ValueError, TypeError):
        return "unknown"


def check_status():
    """Show session activity summary."""
    print("Session Activity Logger - Status")
    print("=" * 50)
    data = load_activity()
    entries = data.get("entries", [])
    session_start = data.get("session_start")

    # Session duration
    if session_start:
        duration = compute_duration(session_start)
        print(f"\nSession started: {session_start[:19]}")
        print(f"Session duration: {duration}")
    else:
        print("\nNo session activity recorded yet.")
        sys.exit(0)

    # Activity breakdown by type
    type_counts = {}
    for entry in entries:
        t = entry.get("type", "other")
        type_counts[t] = type_counts.get(t, 0) + 1

    print(f"\nTotal activities: {len(entries)}")
    print(f"\nActivity Breakdown:")
    for t, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {t}: {count}")

    # Last 10 activities
    last_10 = entries[-10:] if len(entries) >= 10 else entries
    print(f"\nLast {len(last_10)} Activities:")
    for entry in reversed(last_10):
        ts = entry.get("timestamp", "?")[:19]
        t = entry.get("type", "?")
        summary = entry.get("command_summary", "?")
        print(f"  [{ts}] ({t}) {summary}")

    sys.exit(0)


def check_reset():
    """Clear session data."""
    print("Session Activity Logger - Reset")
    if ACTIVITY_FILE.exists():
        os.remove(ACTIVITY_FILE)
        print("Session activity cleared.")
    else:
        print("No activity file to clear.")
    sys.exit(0)


def main():
    # Handle CLI flags
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            check_status()
        elif sys.argv[1] == "--reset":
            check_reset()

    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not command:
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    # Skip trivial commands
    if is_trivial(command):
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    # Classify and log
    cmd_type, summary = classify_command(command)
    now = datetime.now(timezone.utc).isoformat()

    activity = load_activity()

    # Set session start if not set
    if not activity.get("session_start"):
        activity["session_start"] = now

    # Add entry
    entry = {
        "type": cmd_type,
        "command_summary": command[:100],
        "timestamp": now,
    }
    activity["entries"].append(entry)

    save_activity(activity)

    print(json.dumps({"decision": "ALLOW"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
