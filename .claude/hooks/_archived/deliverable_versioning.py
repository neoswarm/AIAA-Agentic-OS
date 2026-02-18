#!/usr/bin/env python3
"""
Hook 106: deliverable_versioning.py (PostToolUse on Write)
Purpose: Track versions of client deliverables.
Logic: When writing to same output path, increment version counter. Track all
versions with timestamps. Enable rollback by keeping version history in state.

Protocol:
  - PostToolUse: prints JSON to stdout {"decision": "ALLOW"}
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
import hashlib
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "deliverable_versions.json"

# Tracked directories for versioning
TRACKED_DIRS = [".tmp/", "clients/"]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "files": {},
        "total_versions": 0,
        "total_files_tracked": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_tracked_path(file_path):
    """Check if the path should be version-tracked."""
    for d in TRACKED_DIRS:
        if d in file_path:
            return True
    return False


def compute_content_hash(content):
    """Generate a short hash of the content for change detection."""
    if not content:
        return "empty"
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def show_status():
    state = load_state()
    files = state.get("files", {})

    print("=== Deliverable Versioning ===")
    print(f"Total files tracked: {state.get('total_files_tracked', 0)}")
    print(f"Total versions: {state.get('total_versions', 0)}")

    if files:
        # Sort by most versions
        sorted_files = sorted(files.items(),
                              key=lambda x: x[1].get("current_version", 0),
                              reverse=True)

        print(f"\nVersioned files (top {min(15, len(sorted_files))}):")
        for fpath, fdata in sorted_files[:15]:
            version = fdata.get("current_version", 1)
            last_modified = fdata.get("last_modified", "?")[:19]
            fname = Path(fpath).name
            print(f"\n  {fname} (v{version}, modified: {last_modified})")
            print(f"    Path: {fpath}")

            history = fdata.get("version_history", [])
            if history:
                print(f"    History (last {min(5, len(history))}):")
                for h in history[-5:]:
                    v = h.get("version", "?")
                    ts = h.get("timestamp", "?")[:19]
                    ch = h.get("content_hash", "?")
                    size = h.get("content_length", 0)
                    print(f"      v{v}: {ts} ({size} chars, hash: {ch})")

    # Suggest files with most rewrites
    multi_version = [(f, d) for f, d in files.items() if d.get("current_version", 1) > 2]
    if multi_version:
        print(f"\nFiles with 3+ versions (consider review):")
        for fpath, fdata in sorted(multi_version, key=lambda x: x[1]["current_version"], reverse=True)[:5]:
            print(f"  {Path(fpath).name}: v{fdata['current_version']}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Deliverable versioning state reset.")
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
    if not file_path or not is_tracked_path(file_path):
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Skip hook state files
    if ".tmp/hooks/" in file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()
    content = tool_input.get("content", "")
    content_hash = compute_content_hash(content)
    content_length = len(content) if content else 0

    files = state.get("files", {})

    if file_path in files:
        # Existing file - check if content actually changed
        file_data = files[file_path]
        last_hash = file_data.get("last_content_hash", "")

        if content_hash == last_hash:
            # Same content, no version bump
            save_state(state)
            print(json.dumps({"decision": "ALLOW"}))
            return

        # Content changed - increment version
        new_version = file_data.get("current_version", 1) + 1
        file_data["current_version"] = new_version
        file_data["last_modified"] = now
        file_data["last_content_hash"] = content_hash

        # Add to history
        history = file_data.get("version_history", [])
        history.append({
            "version": new_version,
            "timestamp": now,
            "content_hash": content_hash,
            "content_length": content_length
        })
        file_data["version_history"] = history[-20:]  # Keep last 20 versions

        state["total_versions"] = state.get("total_versions", 0) + 1

        output = {
            "decision": "ALLOW",
            "reason": f"[Versioning] {Path(file_path).name} updated to v{new_version}"
        }
    else:
        # New file - start at v1
        files[file_path] = {
            "current_version": 1,
            "created_at": now,
            "last_modified": now,
            "last_content_hash": content_hash,
            "version_history": [{
                "version": 1,
                "timestamp": now,
                "content_hash": content_hash,
                "content_length": content_length
            }]
        }
        state["total_files_tracked"] = state.get("total_files_tracked", 0) + 1
        state["total_versions"] = state.get("total_versions", 0) + 1
        output = {"decision": "ALLOW"}

    state["files"] = files
    save_state(state)
    print(json.dumps(output))


if __name__ == "__main__":
    main()
