#!/usr/bin/env python3
"""
Hook 76: context_pollution_preventer.py - PreToolUse on Read

Prevents loading too many context/skill/directive files at once to avoid
context window flooding. Warns at 8 files, blocks at 12.

Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages via sys.stderr.write()
  - Never prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show context loading stats
  --reset   Clear tracking state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "context_pollution.json"

WARN_THRESHOLD = 8
BLOCK_THRESHOLD = 12

# Directories that count as context files
CONTEXT_DIRS = ["context/", "skills/", "directives/", "clients/"]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "context_files_loaded": [],
        "warnings_issued": 0,
        "blocks_issued": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_context_file(file_path):
    """Check if the file is a context/skill/directive/client file."""
    path_str = str(file_path).replace("\\", "/")
    for ctx_dir in CONTEXT_DIRS:
        if ctx_dir in path_str:
            return True
    return False


def get_context_category(file_path):
    """Determine which category a context file belongs to."""
    path_str = str(file_path).replace("\\", "/")
    if "context/" in path_str:
        return "agency_context"
    elif "skills/" in path_str:
        return "skill_bible"
    elif "directives/" in path_str:
        return "directive"
    elif "clients/" in path_str:
        return "client_context"
    return "other"


def handle_status():
    state = load_state()
    files = state.get("context_files_loaded", [])
    print("Context Pollution Preventer Status")
    print(f"  Context files loaded this session: {len(files)}")
    print(f"  Warn threshold: {WARN_THRESHOLD}")
    print(f"  Block threshold: {BLOCK_THRESHOLD}")
    print(f"  Warnings issued: {state.get('warnings_issued', 0)}")
    print(f"  Blocks issued: {state.get('blocks_issued', 0)}")

    # Group by category
    categories = {}
    for entry in files:
        cat = entry.get("category", "other")
        categories.setdefault(cat, []).append(entry.get("file", "unknown"))

    if categories:
        print("  By category:")
        for cat, cat_files in categories.items():
            print(f"    {cat}: {len(cat_files)}")
            for f in cat_files[-3:]:
                print(f"      - {f}")

    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "context_files_loaded": [],
        "warnings_issued": 0,
        "blocks_issued": 0,
    }))
    print("Context Pollution Preventer: State reset.")
    sys.exit(0)


def main():
    if "--status" in sys.argv:
        handle_status()
    if "--reset" in sys.argv:
        handle_reset()

    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, IOError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Read":
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if not is_context_file(file_path):
        sys.exit(0)

    state = load_state()
    files_loaded = state.get("context_files_loaded", [])
    count = len(files_loaded)
    file_name = Path(file_path).name
    category = get_context_category(file_path)

    # Check if already loaded (don't double-count re-reads)
    already_loaded = any(e.get("file") == file_name for e in files_loaded)
    if already_loaded:
        sys.exit(0)

    if count >= BLOCK_THRESHOLD:
        state["blocks_issued"] = state.get("blocks_issued", 0) + 1
        save_state(state)
        sys.stderr.write(
            f"[Context Pollution] BLOCKED: Already loaded {count} context files "
            f"(limit: {BLOCK_THRESHOLD})\n"
            f"  Attempted to load: {file_name} ({category})\n"
            f"  Too many context files causes context window flooding.\n"
            f"  Use --reset to clear or be more selective about context loading.\n"
        )
        sys.exit(2)

    # Track the new file
    files_loaded.append({
        "file": file_name,
        "category": category,
        "path": file_path,
        "timestamp": datetime.now().isoformat(),
    })
    state["context_files_loaded"] = files_loaded

    if count + 1 >= WARN_THRESHOLD:
        state["warnings_issued"] = state.get("warnings_issued", 0) + 1
        save_state(state)
        sys.stderr.write(
            f"[Context Pollution] WARNING: Now loading context file #{count + 1} "
            f"({file_name})\n"
            f"  {count + 1}/{BLOCK_THRESHOLD} context files loaded. "
            f"Approaching limit.\n"
            f"  Consider whether all loaded context is necessary.\n"
        )
        sys.exit(0)

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
