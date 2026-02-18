#!/usr/bin/env python3
"""
Hook 11: Google Docs Format Guard
Type: PreToolUse on Bash tool
Tier: Advisory (never blocks)

Detects when Google Doc creation scripts are invoked with raw markdown
patterns in the arguments, and warns that Google Docs require native
formatting instead of raw markdown.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {"command": "..."}}
  - Exit 0 = allow (always)
  - Warnings written to stderr
  - Never prints to stdout in PreToolUse mode
"""

import json
import re
import sys


STATE_DIR = "/Users/lucasnolan/Agentic OS/.tmp/hooks"

GOOGLE_DOC_PATTERNS = [
    "execution/create_google_doc",
    "create_google_doc.py",
]

MARKDOWN_PATTERNS = [
    r'(?:^|\s)#{1,6}\s',       # Headings: # , ## , etc.
    r'\*\*[^*]+\*\*',          # Bold: **text**
    r'^---\s*$',               # Horizontal rules
    r'```',                    # Code fences
]

REMINDER_TEXT = (
    "[GOOGLE DOCS FORMAT] Reminder: Google Docs require native formatting, "
    "not raw markdown. See AGENTS.md Rule 5."
)


def check_status():
    """Print status information and exit."""
    print("Google Docs Format Guard - Status")
    print("=" * 40)
    print(f"Reminder text: {REMINDER_TEXT}")
    print()
    print("Monitored script patterns:")
    for p in GOOGLE_DOC_PATTERNS:
        print(f"  - {p}")
    print()
    print("Detected markdown patterns:")
    print("  - Headings (# , ## , etc.)")
    print("  - Bold (**text**)")
    print("  - Horizontal rules (---)")
    print("  - Code fences (```)")
    sys.exit(0)


def check_reset():
    """No persistent state to reset."""
    print("Google Docs Format Guard - Reset")
    print("No persistent state to clear.")
    sys.exit(0)


def has_google_doc_script(command: str) -> bool:
    """Check if command invokes a Google Doc creation script."""
    for pattern in GOOGLE_DOC_PATTERNS:
        if pattern in command:
            return True
    return False


def has_raw_markdown(command: str) -> bool:
    """Check if command arguments contain raw markdown patterns."""
    for pattern in MARKDOWN_PATTERNS:
        if re.search(pattern, command, re.MULTILINE):
            return True
    return False


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

    # Only check commands that invoke Google Doc creation
    if not has_google_doc_script(command):
        sys.exit(0)

    # Check for raw markdown in arguments
    if has_raw_markdown(command):
        sys.stderr.write(f"\n{REMINDER_TEXT}\n\n")

    # Always allow
    sys.exit(0)


if __name__ == "__main__":
    main()
