#!/usr/bin/env python3
"""
Hook 17: Skill Bible Reminder
Type: PreToolUse on Bash tool
Tier: Advisory (never blocks)

When content generation scripts are invoked (generate_*.py, write_*.py),
maps script keywords to relevant skill bibles and suggests loading them
if they haven't been read in the current session.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {"command": "..."}}
  - Exit 0 = allow (always)
  - Suggestions written to stderr
  - Never prints to stdout in PreToolUse mode
"""

import json
import os
import re
import sys
from pathlib import Path


STATE_DIR = Path("/Users/lucasnolan/Agentic OS/.tmp/hooks")
SESSION_READS_FILE = STATE_DIR / "session_reads.json"

# Script keyword → suggested skill bibles
SKILL_BIBLE_MAP = {
    "vsl": [
        "SKILL_BIBLE_vsl_writing_production.md",
        "SKILL_BIBLE_vsl_script_mastery_fazio.md",
    ],
    "funnel": [
        "SKILL_BIBLE_funnel_copywriting_mastery.md",
        "SKILL_BIBLE_agency_funnel_building.md",
    ],
    "email": [
        "SKILL_BIBLE_cold_email_mastery.md",
        "SKILL_BIBLE_email_deliverability.md",
    ],
    "cold": [
        "SKILL_BIBLE_cold_email_mastery.md",
        "SKILL_BIBLE_cold_dm_email_conversion.md",
    ],
    "sales": [
        "SKILL_BIBLE_agency_sales_system.md",
        "SKILL_BIBLE_offer_positioning.md",
    ],
    "blog": [
        "SKILL_BIBLE_content_marketing.md",
    ],
    "content": [
        "SKILL_BIBLE_content_marketing.md",
    ],
    "linkedin": [
        "SKILL_BIBLE_content_marketing.md",
    ],
    "research": [
        "SKILL_BIBLE_market_research.md",
    ],
}


def load_session_reads():
    """Load the session reads tracking file."""
    try:
        if SESSION_READS_FILE.exists():
            with open(SESSION_READS_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {"files_read": []}


def is_content_gen_script(command: str) -> bool:
    """Check if command runs a content generation or writing script."""
    patterns = [
        r'python3?\s+(?:.*?/)?execution/generate_\S+\.py',
        r'python3?\s+(?:.*?/)?execution/write_\S+\.py',
    ]
    for pattern in patterns:
        if re.search(pattern, command):
            return True
    return False


def extract_keywords(command: str) -> list:
    """Extract relevant keywords from the command."""
    # Get the script name
    match = re.search(r'execution/(generate_|write_)(\S+)\.py', command)
    if not match:
        return []

    script_part = match.group(2).lower()
    # Split on underscores and check each part
    parts = script_part.split("_")

    found_keywords = []
    for part in parts:
        if part in SKILL_BIBLE_MAP:
            found_keywords.append(part)

    # Also check the full script name for partial matches
    for keyword in SKILL_BIBLE_MAP:
        if keyword in script_part and keyword not in found_keywords:
            found_keywords.append(keyword)

    return found_keywords


def get_suggested_bibles(keywords: list) -> list:
    """Get unique list of suggested skill bibles from keywords."""
    suggestions = []
    seen = set()
    for kw in keywords:
        for bible in SKILL_BIBLE_MAP.get(kw, []):
            if bible not in seen:
                suggestions.append(bible)
                seen.add(bible)
    return suggestions


def filter_already_loaded(suggestions: list) -> list:
    """Remove skill bibles that have already been read in this session."""
    session = load_session_reads()
    loaded_files = set()
    for f in session.get("files_read", []):
        # Normalize: just the basename
        loaded_files.add(os.path.basename(f))

    return [s for s in suggestions if s not in loaded_files]


def check_status():
    """Show the skill bible mapping."""
    print("Skill Bible Reminder - Status")
    print("=" * 50)
    print("\nKeyword -> Skill Bible Mapping:")
    for keyword, bibles in sorted(SKILL_BIBLE_MAP.items()):
        print(f"\n  {keyword}:")
        for bible in bibles:
            print(f"    - skills/{bible}")

    session = load_session_reads()
    files = session.get("files_read", [])
    if files:
        print(f"\n\nSession reads tracked ({len(files)}):")
        for f in files[-10:]:
            print(f"  - {f}")
    else:
        print("\n\nNo session reads tracked yet.")

    sys.exit(0)


def check_reset():
    """No persistent state to reset (session reads managed elsewhere)."""
    print("Skill Bible Reminder - Reset")
    print("Session reads are managed by the session tracker.")
    print("This hook has no independent state to clear.")
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

    # Only check content generation scripts
    if not is_content_gen_script(command):
        sys.exit(0)

    # Extract keywords and find relevant skill bibles
    keywords = extract_keywords(command)
    if not keywords:
        sys.exit(0)

    suggestions = get_suggested_bibles(keywords)
    if not suggestions:
        sys.exit(0)

    # Filter out already-loaded bibles
    unloaded = filter_already_loaded(suggestions)
    if not unloaded:
        sys.exit(0)

    # Write suggestion to stderr
    bible_list = "\n".join(f"  - skills/{bible}" for bible in unloaded)
    message = (
        f"\n[SKILL BIBLE] Suggested for this workflow:\n"
        f"{bible_list}\n"
        f"Consider loading these for better output quality.\n\n"
    )
    sys.stderr.write(message)

    sys.exit(0)


if __name__ == "__main__":
    main()
