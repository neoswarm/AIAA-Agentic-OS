#!/usr/bin/env python3
"""
Hook 14: Railway Deploy Guard
Type: PreToolUse on Bash tool
Tier: Advisory (never blocks)

When a command contains 'railway up' or 'railway deploy', prints a deployment
checklist to stderr as a reminder. When 'railway link' is used without the
'-p' flag, warns about the correct syntax.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {"command": "..."}}
  - Exit 0 = allow (always)
  - Warnings/info written to stderr
  - Never prints to stdout in PreToolUse mode
"""

import json
import sys


DEPLOY_CHECKLIST = """[DEPLOY CHECKLIST]
- Linked to correct project? (railway link -p <PROJECT_ID>)
- All env vars set? (OPENROUTER_API_KEY, SLACK_WEBHOOK_URL, etc.)
- Using --service flag? (required with multiple services)
- RAILWAY_API_TOKEN set on dashboard? (needed for cron management)
- Google OAuth token uploaded? (if using Google APIs)"""

LINK_WARNING = (
    "[RAILWAY WARNING] Use `railway link -p <PROJECT_ID>` -- "
    "positional arg fails on Railway CLI."
)


def check_status():
    """Print the deploy checklist."""
    print("Railway Deploy Guard - Status")
    print("=" * 50)
    print()
    print(DEPLOY_CHECKLIST)
    print()
    print("Link command reminder:")
    print(f"  {LINK_WARNING}")
    sys.exit(0)


def check_reset():
    """No persistent state to reset."""
    print("Railway Deploy Guard - Reset")
    print("No persistent state to clear.")
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
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not command:
        sys.exit(0)

    # Check for railway deploy commands
    if "railway up" in command or "railway deploy" in command:
        sys.stderr.write(f"\n{DEPLOY_CHECKLIST}\n\n")
        sys.exit(0)

    # Check for railway link without -p flag
    if "railway link" in command and " -p " not in command and " -p\t" not in command:
        # Make sure it's actually 'railway link' and not something else
        # Also allow if it's railway link -p<something> (no space)
        parts = command.split()
        try:
            link_idx = parts.index("link")
            # Check if the previous token is 'railway'
            if link_idx > 0 and parts[link_idx - 1].endswith("railway"):
                # Check if -p appears anywhere after 'link'
                after_link = parts[link_idx + 1:] if link_idx + 1 < len(parts) else []
                has_p_flag = any(arg.startswith("-p") for arg in after_link)
                if not has_p_flag:
                    sys.stderr.write(f"\n{LINK_WARNING}\n\n")
        except (ValueError, IndexError):
            pass

    sys.exit(0)


if __name__ == "__main__":
    main()
