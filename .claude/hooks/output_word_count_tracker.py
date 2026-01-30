#!/usr/bin/env python3
"""
Hook 64: output_word_count_tracker.py (PostToolUse on Write)
Tracks word counts across all outputs written to .tmp/.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "word_count_tracker.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "files": [],
        "total_words_generated": 0,
        "total_files": 0,
        "largest_file": {"name": "", "words": 0},
        "smallest_file": {"name": "", "words": float("inf")}
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Handle inf for JSON serialization
    if state.get("smallest_file", {}).get("words") == float("inf"):
        state["smallest_file"]["words"] = 0
    STATE_FILE.write_text(json.dumps(state, indent=2))


def count_words(content):
    """Count words in content string."""
    if not content:
        return 0
    return len(content.split())


def show_status():
    state = load_state()
    total_words = state.get("total_words_generated", 0)
    total_files = state.get("total_files", 0)
    avg = total_words / total_files if total_files > 0 else 0

    print("=== Output Word Count Tracker ===")
    print(f"Total words generated: {total_words:,}")
    print(f"Total files tracked: {total_files}")
    print(f"Average words per file: {avg:,.0f}")

    largest = state.get("largest_file", {})
    if largest.get("name"):
        print(f"Largest file: {largest['name']} ({largest.get('words', 0):,} words)")

    smallest = state.get("smallest_file", {})
    if smallest.get("name") and smallest.get("words", 0) > 0:
        print(f"Smallest file: {smallest['name']} ({smallest.get('words', 0):,} words)")

    files = state.get("files", [])
    if files:
        print("\nRecent files:")
        for f in files[-10:]:
            print(f"  {f.get('filename', '?')}: {f.get('word_count', 0):,} words ({f.get('timestamp', '?')[:10]})")
    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("State reset.")
    sys.exit(0)


def main():
    if "--status" in sys.argv:
        show_status()
    if "--reset" in sys.argv:
        reset_state()

    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Write", "write"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    # Only track .tmp/ output files that are markdown
    if ".tmp/" not in file_path and ".tmp\\" not in file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    if not file_path.endswith(".md"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()

    word_count = count_words(content)
    filename = Path(file_path).name

    # Track file
    file_entry = {
        "filename": filename,
        "path": file_path,
        "word_count": word_count,
        "timestamp": now
    }
    state["files"] = state.get("files", [])
    state["files"].append(file_entry)
    state["files"] = state["files"][-200:]

    # Update aggregates
    state["total_words_generated"] = state.get("total_words_generated", 0) + word_count
    state["total_files"] = state.get("total_files", 0) + 1

    # Update largest
    largest = state.get("largest_file", {"name": "", "words": 0})
    if word_count > largest.get("words", 0):
        state["largest_file"] = {"name": filename, "words": word_count}

    # Update smallest
    smallest = state.get("smallest_file", {"name": "", "words": float("inf")})
    smallest_words = smallest.get("words", float("inf"))
    if isinstance(smallest_words, (int, float)) and word_count < smallest_words and word_count > 0:
        state["smallest_file"] = {"name": filename, "words": word_count}
    elif not smallest.get("name"):
        state["smallest_file"] = {"name": filename, "words": word_count}

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
