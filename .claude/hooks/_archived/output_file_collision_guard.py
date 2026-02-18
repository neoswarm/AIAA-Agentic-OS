#!/usr/bin/env python3
"""
Hook 32: Output File Collision Guard (PreToolUse on Write)

Before writing to .tmp/:
- Check if the target file already exists
- If exists AND has content > 100 chars:
  - WARN via stderr about overwrite
  - Log the overwrite to .tmp/hooks/overwrites.json
- Exit 0 always (warn only, never block writes to .tmp/)
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "overwrites.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"overwrites": [], "stats": {"total": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def handle_status():
    state = load_state()
    print("=== Output File Collision Guard Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"Total overwrites logged: {stats.get('total', 0)}")

    overwrites = state.get("overwrites", [])
    if overwrites:
        print(f"\nRecent overwrites:")
        for o in overwrites[-10:]:
            print(f"  {o.get('filename', '?')}")
            print(f"    Original size: {o.get('original_size', '?')} chars")
            print(f"    New size: {o.get('new_size', '?')} chars")
            print(f"    Time: {o.get('timestamp', '?')}")
    else:
        print("\nNo overwrites logged yet.")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Output file collision guard state reset.")
    else:
        print("No state file to reset.")


def main():
    if "--status" in sys.argv:
        handle_status()
        return
    if "--reset" in sys.argv:
        handle_reset()
        return

    # PreToolUse mode
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Write":
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    new_content = tool_input.get("content", "")

    # Only check .tmp/ writes
    if ".tmp" not in file_path:
        sys.exit(0)

    target = Path(file_path)

    if target.exists() and target.is_file():
        try:
            existing_size = target.stat().st_size
        except OSError:
            existing_size = 0

        if existing_size > 100:
            state = load_state()
            overwrite_record = {
                "filename": target.name,
                "filepath": file_path,
                "original_size": existing_size,
                "new_size": len(new_content) if new_content else 0,
                "timestamp": datetime.now().isoformat(),
            }
            state["overwrites"].append(overwrite_record)
            # Keep last 100
            state["overwrites"] = state["overwrites"][-100:]
            state["stats"]["total"] = state["stats"].get("total", 0) + 1
            save_state(state)

            sys.stderr.write(
                f"[FILE COLLISION] File already exists with {existing_size} chars "
                f"of content. This will overwrite: {target.name}\n"
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
