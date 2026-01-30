#!/usr/bin/env python3
"""
large_file_read_blocker.py - PreToolUse hook on Read tool

When sub-agents are active, blocks reading files larger than 300 lines to
prevent context window bloat. When no agents are active, allows all reads.

Suggests using Grep or Read with offset/limit parameters as alternatives.

Hook Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages to user via sys.stderr.write()
  - NEVER prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show current agent count and line threshold
  --reset   N/A (stateless, reads agent_limiter state)
"""

import json
import sys
import os
import time
from pathlib import Path

BASE_DIR = Path(os.path.expanduser("/Users/lucasnolan/Agentic OS"))
AGENTS_STATE_FILE = BASE_DIR / ".tmp" / "hooks" / "active_agents.json"

MAX_LINES = 300
STALE_SECONDS = 30 * 60


def load_agent_count():
    """Load the count of active (non-stale) agents."""
    if not AGENTS_STATE_FILE.exists():
        return 0
    try:
        with open(AGENTS_STATE_FILE, "r") as f:
            data = json.load(f)
        now = time.time()
        agents = [
            a for a in data.get("agents", [])
            if now - a.get("timestamp", 0) < STALE_SECONDS
        ]
        return len(agents)
    except (json.JSONDecodeError, IOError):
        return 0


def count_file_lines(file_path):
    """Efficiently count lines in a file."""
    try:
        count = 0
        with open(file_path, "rb") as f:
            for _ in f:
                count += 1
        return count
    except (IOError, OSError):
        return -1  # File doesn't exist or can't be read


def handle_status():
    """Print status and exit."""
    agent_count = load_agent_count()
    print("Large File Read Blocker Status")
    print(f"  Active agents: {agent_count}")
    print(f"  Line threshold: {MAX_LINES}")
    if agent_count > 0:
        print(f"  Mode: ACTIVE - blocking reads of files > {MAX_LINES} lines")
    else:
        print("  Mode: PASSIVE - allowing all reads (no active agents)")
    sys.exit(0)


def handle_reset():
    """Stateless hook, nothing to reset."""
    print("Large File Read Blocker: Stateless hook (reads agent_limiter state).")
    print("  To reset agent count, run: python3 .claude/hooks/agent_limiter.py --reset")
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

    # Only act on Read tool
    if tool_name != "Read":
        sys.exit(0)

    # Check if agents are active
    agent_count = load_agent_count()
    if agent_count == 0:
        # No agents active, allow all reads
        sys.exit(0)

    # Get file path
    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    # If user already specified offset/limit, they're being responsible
    if tool_input.get("offset") is not None or tool_input.get("limit") is not None:
        sys.exit(0)

    # Check if file exists - if not, let Read tool handle the error
    if not os.path.exists(file_path):
        sys.exit(0)

    # Check if it's a regular file (not a binary, image, etc.)
    if not os.path.isfile(file_path):
        sys.exit(0)

    # Count lines
    line_count = count_file_lines(file_path)
    if line_count < 0:
        # Couldn't read the file, let Read tool handle it
        sys.exit(0)

    if line_count > MAX_LINES:
        filename = Path(file_path).name
        sys.stderr.write(
            f"[Large File Blocker] BLOCKED: {filename} has {line_count} lines "
            f"(limit: {MAX_LINES} while {agent_count} agent(s) active).\n"
            f"  Alternatives:\n"
            f"    - Use Read with offset/limit: Read(file_path=\"{file_path}\", offset=1, limit=100)\n"
            f"    - Use Grep to search for specific content\n"
            f"    - Wait for agents to complete (agent_limiter --status)\n"
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
