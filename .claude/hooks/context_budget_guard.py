#!/usr/bin/env python3
"""
context_budget_guard.py - PreToolUse hook on Task tool

Estimates context window usage based on active agent count and warns or blocks
when approaching the 200k token budget. Prevents launching new agents when
context is likely to be exhausted.

Thresholds:
  - WARN at 60% (120k tokens)
  - HIGH at 75% (150k tokens)
  - BLOCK at 85% (170k tokens)

Hook Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages to user via sys.stderr.write()
  - NEVER prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show estimated context usage
  --reset   N/A (reads agent_limiter state, no own state)
"""

import json
import sys
import os
import time
from pathlib import Path

BASE_DIR = Path(os.path.expanduser("/Users/lucasnolan/Agentic OS"))
AGENTS_STATE_FILE = BASE_DIR / ".tmp" / "hooks" / "active_agents.json"

# Context budget constants
MAX_CONTEXT = 200000  # Total context window in tokens
BASE_CONTEXT = 50000  # Base usage (system prompt, conversation, etc.)
AGENT_OUTPUT_AVG = 5000  # Estimated tokens per active agent

# Thresholds as fractions
WARN_THRESHOLD = 0.60
HIGH_THRESHOLD = 0.75
BLOCK_THRESHOLD = 0.85

STALE_SECONDS = 30 * 60  # Same as agent_limiter


def load_agents():
    """Load active agents from agent_limiter state."""
    if AGENTS_STATE_FILE.exists():
        try:
            with open(AGENTS_STATE_FILE, "r") as f:
                data = json.load(f)
            # Clean stale agents
            now = time.time()
            agents = [
                a for a in data.get("agents", [])
                if now - a.get("timestamp", 0) < STALE_SECONDS
            ]
            return agents
        except (json.JSONDecodeError, IOError):
            return []
    return []


def estimate_usage(agent_count):
    """Estimate context usage in tokens."""
    return BASE_CONTEXT + (agent_count * AGENT_OUTPUT_AVG)


def usage_pct(tokens):
    """Return usage as a percentage of max context."""
    return (tokens / MAX_CONTEXT) * 100


def handle_status():
    """Print context budget status and exit."""
    agents = load_agents()
    count = len(agents)
    estimated = estimate_usage(count)
    pct = usage_pct(estimated)

    print("Context Budget Guard Status")
    print(f"  Active agents: {count}")
    print(f"  Estimated usage: {estimated:,} / {MAX_CONTEXT:,} tokens ({pct:.1f}%)")
    print(f"  Thresholds: WARN={WARN_THRESHOLD*100:.0f}% | HIGH={HIGH_THRESHOLD*100:.0f}% | BLOCK={BLOCK_THRESHOLD*100:.0f}%")

    if pct >= BLOCK_THRESHOLD * 100:
        print("  Status: WOULD BLOCK new agents")
    elif pct >= HIGH_THRESHOLD * 100:
        print("  Status: HIGH - warning on new agents")
    elif pct >= WARN_THRESHOLD * 100:
        print("  Status: WARN - approaching limit")
    else:
        print("  Status: OK")
    sys.exit(0)


def handle_reset():
    """No own state to reset, but acknowledge the command."""
    print("Context Budget Guard: No own state to reset.")
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

    # Only act on Task tool (not TaskOutput)
    if tool_name != "Task":
        sys.exit(0)

    # Load current agent count
    agents = load_agents()
    # +1 because this new agent hasn't been registered yet
    projected_count = len(agents) + 1
    estimated = estimate_usage(projected_count)
    pct = usage_pct(estimated)

    if pct >= BLOCK_THRESHOLD * 100:
        sys.stderr.write(
            f"[Context Budget] BLOCKED: Estimated context at {pct:.1f}% "
            f"({estimated:,}/{MAX_CONTEXT:,} tokens) with {projected_count} agents.\n"
            f"  Wait for agents to complete before launching new ones.\n"
        )
        sys.exit(2)

    if pct >= HIGH_THRESHOLD * 100:
        sys.stderr.write(
            f"[Context Budget] HIGH WARNING: Estimated context at {pct:.1f}% "
            f"({estimated:,}/{MAX_CONTEXT:,} tokens) with {projected_count} agents.\n"
            f"  Consider waiting for agents to complete.\n"
        )
    elif pct >= WARN_THRESHOLD * 100:
        sys.stderr.write(
            f"[Context Budget] WARNING: Estimated context at {pct:.1f}% "
            f"({estimated:,}/{MAX_CONTEXT:,} tokens) with {projected_count} agents.\n"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
