#!/usr/bin/env python3
"""
Hook 12: Delivery Pipeline Validator
Type: PostToolUse on Write tool
Tier: Advisory (always allows)

After writing any file to .tmp/, checks if the file looks like a final
deliverable (500+ words, 3+ sections, not a numbered intermediate file).
If so, prints a reminder about the delivery pipeline (Google Docs + Slack).
Tracks deliverables in .tmp/hooks/delivery_tracker.json.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Write", "tool_input": {...}, "tool_result": "..."}
  - Prints JSON to stdout: {"decision": "ALLOW"}
  - Info messages written to stderr
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR = Path("/Users/lucasnolan/Agentic OS/.tmp/hooks")
TRACKER_FILE = STATE_DIR / "delivery_tracker.json"
TMP_ROOT = "/Users/lucasnolan/Agentic OS/.tmp/"

INTERMEDIATE_PREFIX_RE = re.compile(r'^\d{2}_')


def load_tracker():
    """Load the delivery tracker state."""
    try:
        if TRACKER_FILE.exists():
            with open(TRACKER_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {"deliverables": [], "delivered": []}


def save_tracker(tracker):
    """Save the delivery tracker state."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f, indent=2)


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def count_sections(text: str) -> int:
    """Count markdown-style sections (lines starting with #)."""
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or (stripped and stripped == stripped.upper() and len(stripped) > 10):
            count += 1
    return count


def is_intermediate_file(filename: str) -> bool:
    """Check if filename looks like an intermediate checkpoint."""
    return bool(INTERMEDIATE_PREFIX_RE.match(filename))


def is_final_deliverable(file_path: str, content: str) -> bool:
    """Determine if a file looks like a final deliverable."""
    filename = os.path.basename(file_path)

    # Intermediate files (01_research.md, etc.) are not final
    if is_intermediate_file(filename):
        return False

    # Must have 500+ words
    if count_words(content) < 500:
        return False

    # Must have 3+ sections
    if count_sections(content) < 3:
        return False

    return True


def check_status():
    """Print status showing undelivered files."""
    print("Delivery Pipeline Validator - Status")
    print("=" * 50)
    tracker = load_tracker()

    delivered_paths = set(d.get("file_path", "") for d in tracker.get("delivered", []))
    undelivered = []
    for d in tracker.get("deliverables", []):
        if d.get("file_path", "") not in delivered_paths:
            undelivered.append(d)

    if undelivered:
        print(f"\nUndelivered files ({len(undelivered)}):")
        for item in undelivered:
            print(f"  - {item.get('file_path', 'unknown')}")
            print(f"    Words: {item.get('word_count', '?')} | Sections: {item.get('section_count', '?')}")
            print(f"    Saved: {item.get('timestamp', '?')}")
    else:
        print("\nNo undelivered files. All deliverables have been processed.")

    total = len(tracker.get("deliverables", []))
    delivered = len(tracker.get("delivered", []))
    print(f"\nTotal tracked: {total} | Delivered: {delivered} | Pending: {total - delivered}")
    sys.exit(0)


def check_reset():
    """Reset delivery tracker."""
    print("Delivery Pipeline Validator - Reset")
    if TRACKER_FILE.exists():
        os.remove(TRACKER_FILE)
        print("Delivery tracker cleared.")
    else:
        print("No tracker file to clear.")
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
    if tool_name != "Write":
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    # Only care about .tmp/ writes
    if TMP_ROOT not in file_path:
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    # Check if this is a final deliverable
    if is_final_deliverable(file_path, content):
        word_count = count_words(content)
        section_count = count_sections(content)

        # Track in delivery tracker
        tracker = load_tracker()
        entry = {
            "file_path": file_path,
            "word_count": word_count,
            "section_count": section_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Avoid duplicates
        existing_paths = [d["file_path"] for d in tracker["deliverables"]]
        if file_path not in existing_paths:
            tracker["deliverables"].append(entry)
            save_tracker(tracker)

        # Build relative path for the reminder
        rel_path = file_path
        if "/Agentic OS/" in file_path:
            rel_path = file_path.split("/Agentic OS/")[-1]

        reminder = (
            f"\n[DELIVERY REMINDER] Deliverable saved locally ({word_count} words, {section_count} sections). Next steps:\n"
            f'1. Create Google Doc: python3 execution/create_google_doc.py --file "{rel_path}" --title "..."\n'
            f'2. Send Slack: python3 execution/send_slack_notification.py --message "Deliverable ready"\n'
        )
        sys.stderr.write(reminder)

    print(json.dumps({"decision": "ALLOW"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
