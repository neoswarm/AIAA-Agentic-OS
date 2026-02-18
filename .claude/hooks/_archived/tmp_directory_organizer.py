#!/usr/bin/env python3
"""
Hook 46: tmp_directory_organizer.py (PostToolUse on Write)
After writes to .tmp/, checks if files are being written flat vs organized into subdirectories.
Warns when project-type files should be in subdirectories.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "tmp_structure.json"

PROJECT_KEYWORDS = [
    "vsl", "funnel", "email", "research", "campaign", "sales", "blog",
    "newsletter", "linkedin", "cold_email", "outreach", "proposal",
    "sequence", "landing_page", "lead", "prospect"
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"flat_files": [], "subdirectory_files": [], "warnings_issued": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def show_status():
    state = load_state()
    print("=== .tmp/ Directory Organization ===")
    print(f"Flat files (in .tmp/ root): {len(state.get('flat_files', []))}")
    print(f"Organized files (in subdirs): {len(state.get('subdirectory_files', []))}")
    print(f"Organization warnings issued: {state.get('warnings_issued', 0)}")
    if state.get("flat_files"):
        print("\nFlat files:")
        for f in state["flat_files"][-10:]:
            print(f"  - {f.get('path', 'unknown')}")
    if state.get("subdirectory_files"):
        print("\nOrganized files (recent):")
        for f in state["subdirectory_files"][-10:]:
            print(f"  - {f.get('path', 'unknown')}")
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
    if ".tmp/" not in file_path and ".tmp\\" not in file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()

    # Determine if file is flat (directly in .tmp/) or in a subdirectory
    try:
        tmp_idx = file_path.find(".tmp/")
        if tmp_idx == -1:
            tmp_idx = file_path.find(".tmp\\")
        if tmp_idx == -1:
            print(json.dumps({"decision": "ALLOW"}))
            return

        relative = file_path[tmp_idx + 5:]  # after ".tmp/"
        parts = relative.split("/")
        if len(parts) == 0:
            print(json.dumps({"decision": "ALLOW"}))
            return

        is_flat = len(parts) == 1
        filename_lower = os.path.basename(file_path).lower()

        entry = {"path": file_path, "timestamp": now}

        if is_flat:
            state["flat_files"].append(entry)
            # Keep only last 100
            state["flat_files"] = state["flat_files"][-100:]

            # Check if it's a project-type file
            is_project_file = any(kw in filename_lower for kw in PROJECT_KEYWORDS)
            if is_project_file:
                state["warnings_issued"] = state.get("warnings_issued", 0) + 1
                save_state(state)
                reason = (
                    f"Consider organizing into a subdirectory: "
                    f".tmp/{{project_name}}/{os.path.basename(file_path)} "
                    f"instead of writing flat to .tmp/"
                )
                print(json.dumps({"decision": "ALLOW", "reason": reason}))
                return
        else:
            state["subdirectory_files"].append(entry)
            state["subdirectory_files"] = state["subdirectory_files"][-100:]

        save_state(state)

    except Exception:
        pass

    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
