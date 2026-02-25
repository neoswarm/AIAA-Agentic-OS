#!/usr/bin/env python3
"""
agent_limiter.py - PreToolUse hook on Task tool

Limits the number of concurrent sub-agents to prevent context window exhaustion.
Tracks active agents in .tmp/hooks/active_agents.json with automatic cleanup
of agents older than 30 minutes.

Hook Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages to user via sys.stderr.write()
  - NEVER prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show active agent count and list
  --reset   Clear all tracked agents
"""

import json
import sys
import os
import time
from pathlib import Path
from datetime import datetime

MAX_AGENTS = 15
STALE_SECONDS = 10 * 60  # 10 minutes — agents rarely run longer
BASE_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = BASE_DIR / ".tmp" / "hooks" / "active_agents.json"


def load_state():
    """Load the active agents state file."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"agents": []}
    return {"agents": []}


def save_state(state):
    """Save the active agents state file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def cleanup_stale(state):
    """Remove agents older than STALE_SECONDS."""
    now = time.time()
    state["agents"] = [
        a for a in state["agents"]
        if now - a.get("timestamp", 0) < STALE_SECONDS
    ]
    return state


def handle_status():
    """Print status information and exit."""
    state = load_state()
    state = cleanup_stale(state)
    save_state(state)
    count = len(state["agents"])
    print(f"Agent Limiter Status")
    print(f"  Active agents: {count}/{MAX_AGENTS}")
    if state["agents"]:
        for i, agent in enumerate(state["agents"], 1):
            ts = datetime.fromtimestamp(agent.get("timestamp", 0)).strftime("%H:%M:%S")
            desc = agent.get("description", "unknown")[:60]
            print(f"  [{i}] {ts} - {desc}")
    else:
        print("  No active agents.")
    sys.exit(0)


def handle_reset():
    """Clear all tracked agents and exit."""
    save_state({"agents": []})
    print("Agent Limiter: All agents cleared.")
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
        # Parse failure - allow by default
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only act on Task tool
    if tool_name != "Task":
        sys.exit(0)

    # Load and clean state
    state = load_state()
    state = cleanup_stale(state)

    active_count = len(state["agents"])

    if active_count >= MAX_AGENTS:
        save_state(state)
        sys.stderr.write(
            f"[Agent Limiter] BLOCKED: {active_count}/{MAX_AGENTS} agents already active.\n"
            f"  Wait for existing agents to complete or run: python3 .claude/hooks/agent_limiter.py --reset\n"
            f"  Active agents:\n"
        )
        for agent in state["agents"]:
            ts = datetime.fromtimestamp(agent.get("timestamp", 0)).strftime("%H:%M:%S")
            desc = agent.get("description", "unknown")[:60]
            sys.stderr.write(f"    - [{ts}] {desc}\n")
        sys.exit(2)

    # Register the new agent
    description = tool_input.get("description", tool_input.get("prompt", "unnamed agent"))
    state["agents"].append({
        "description": str(description)[:200],
        "timestamp": time.time(),
    })
    save_state(state)

    sys.stderr.write(
        f"[Agent Limiter] Agent registered ({active_count + 1}/{MAX_AGENTS} active)\n"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
