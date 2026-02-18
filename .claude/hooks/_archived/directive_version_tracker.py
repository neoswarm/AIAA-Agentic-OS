#!/usr/bin/env python3
"""
Hook 29: Directive Version Tracker (PostToolUse on Write)

When any file in directives/ is written or edited:
- Compute hash of the file content
- Log to .tmp/hooks/directive_versions.json: {filename: [{hash, timestamp, size}]}
- Track version history (keep last 10 versions per file)
- When a directive changes, note it as "modified"

ALLOW always. --status shows recently modified directives.
"""

import json
import sys
import hashlib
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "directive_versions.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"directives": {}, "stats": {"total_writes": 0, "modifications": 0, "new_files": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def compute_hash(content):
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()[:16]


def handle_status():
    state = load_state()
    print("=== Directive Version Tracker Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"Total writes tracked: {stats.get('total_writes', 0)}")
    print(f"New files: {stats.get('new_files', 0)}")
    print(f"Modifications: {stats.get('modifications', 0)}")

    directives = state.get("directives", {})
    if directives:
        print(f"\nTracked directives ({len(directives)}):")

        # Sort by most recently modified
        sorted_dirs = sorted(
            directives.items(),
            key=lambda x: x[1][-1]["timestamp"] if x[1] else "",
            reverse=True,
        )

        for name, versions in sorted_dirs[:20]:
            latest = versions[-1]
            version_count = len(versions)
            print(f"  {name}")
            print(f"    Versions: {version_count}")
            print(f"    Latest: {latest['timestamp']}")
            print(f"    Size: {latest['size']} chars")
            print(f"    Hash: {latest['hash']}")
            if version_count > 1:
                print(f"    Previous: {versions[-2]['timestamp']}")
    else:
        print("\nNo directives tracked yet.")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Directive version tracker state reset.")
    else:
        print("No state file to reset.")


def main():
    if "--status" in sys.argv:
        handle_status()
        return
    if "--reset" in sys.argv:
        handle_reset()
        return

    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Write":
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    # Only track directive files
    if "directives/" not in file_path or not file_path.endswith(".md"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    filename = Path(file_path).name
    content_hash = compute_hash(content)
    content_size = len(content)
    now = datetime.now().isoformat()

    version_entry = {
        "hash": content_hash,
        "timestamp": now,
        "size": content_size,
    }

    state["stats"]["total_writes"] = state["stats"].get("total_writes", 0) + 1

    if filename not in state["directives"]:
        state["directives"][filename] = []
        state["stats"]["new_files"] = state["stats"].get("new_files", 0) + 1
        version_entry["type"] = "new"
    else:
        # Check if content actually changed
        versions = state["directives"][filename]
        if versions and versions[-1]["hash"] == content_hash:
            version_entry["type"] = "unchanged"
        else:
            version_entry["type"] = "modified"
            state["stats"]["modifications"] = state["stats"].get("modifications", 0) + 1

    state["directives"][filename].append(version_entry)
    # Keep last 10 versions per file
    state["directives"][filename] = state["directives"][filename][-10:]

    save_state(state)

    if version_entry["type"] == "modified":
        print(json.dumps({
            "decision": "ALLOW",
            "reason": f"Directive '{filename}' modified (version {len(state['directives'][filename])})"
        }))
    else:
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
