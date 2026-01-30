#!/usr/bin/env python3
"""
tmp_cleanup_monitor.py - PostToolUse hook on Write tool

Monitors the .tmp/ directory size after every write. Warns when file count
exceeds thresholds (50 and 100 files) but never blocks. Excludes the
.tmp/hooks/ directory from counting.

Thresholds:
  - >50 files:  Warning about growing temp directory
  - >100 files: Stronger warning suggesting cleanup

Hook Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Always returns {"decision": "ALLOW"} (monitoring only)

State: .tmp/hooks/tmp_file_count.json

CLI Flags:
  --status  Show current file count in .tmp/
  --reset   Clear the count state file
"""

import json
import sys
import os
from pathlib import Path

BASE_DIR = Path(os.path.expanduser("/Users/lucasnolan/Agentic OS"))
TMP_DIR = BASE_DIR / ".tmp"
HOOKS_DIR = TMP_DIR / "hooks"
STATE_FILE = HOOKS_DIR / "tmp_file_count.json"

WARN_THRESHOLD = 50
HIGH_THRESHOLD = 100


def count_tmp_files():
    """Count files in .tmp/ recursively, excluding .tmp/hooks/."""
    if not TMP_DIR.exists():
        return 0

    count = 0
    for root, dirs, files in os.walk(TMP_DIR):
        root_path = Path(root)
        # Skip the hooks directory
        if root_path == HOOKS_DIR or str(root_path).startswith(str(HOOKS_DIR)):
            continue
        count += len(files)
    return count


def save_count(count):
    """Save the current file count to state file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"file_count": count, "threshold_warn": WARN_THRESHOLD, "threshold_high": HIGH_THRESHOLD}
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_count():
    """Load the last saved file count."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
            return data.get("file_count", 0)
        except (json.JSONDecodeError, IOError):
            pass
    return 0


def handle_status():
    """Print current tmp file count and exit."""
    count = count_tmp_files()
    saved = load_count()
    print("Temp Cleanup Monitor Status")
    print(f"  Current files in .tmp/ (excl. hooks/): {count}")
    print(f"  Last recorded count: {saved}")
    print(f"  Thresholds: WARN={WARN_THRESHOLD}, HIGH={HIGH_THRESHOLD}")
    if count > HIGH_THRESHOLD:
        print(f"  Status: HIGH - Consider running cleanup")
    elif count > WARN_THRESHOLD:
        print(f"  Status: WARN - Growing temp directory")
    else:
        print(f"  Status: OK")

    if TMP_DIR.exists():
        # Show top-level subdirectories
        subdirs = [d for d in TMP_DIR.iterdir() if d.is_dir() and d.name != "hooks"]
        if subdirs:
            print(f"  Subdirectories in .tmp/:")
            for d in sorted(subdirs):
                sub_count = sum(1 for _ in d.rglob("*") if _.is_file())
                print(f"    - {d.name}/ ({sub_count} files)")
    sys.exit(0)


def handle_reset():
    """Clear the count state file and exit."""
    if STATE_FILE.exists():
        os.remove(STATE_FILE)
    print("Temp Cleanup Monitor: State file cleared.")
    sys.exit(0)


def main():
    # CLI flags
    if "--status" in sys.argv:
        handle_status()
    if "--reset" in sys.argv:
        handle_reset()

    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, IOError):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only act on Write tool
    if tool_name != "Write":
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")

    # Only monitor writes to .tmp/ directory
    try:
        if not str(Path(file_path)).startswith(str(TMP_DIR)):
            print(json.dumps({"decision": "ALLOW"}))
            return
    except (TypeError, ValueError):
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Skip writes to .tmp/hooks/ (our own state files)
    try:
        if str(Path(file_path)).startswith(str(HOOKS_DIR)):
            print(json.dumps({"decision": "ALLOW"}))
            return
    except (TypeError, ValueError):
        pass

    # Count current files
    count = count_tmp_files()
    save_count(count)

    # Build response
    response = {"decision": "ALLOW"}

    if count > HIGH_THRESHOLD:
        response["reason"] = (
            f"[Cleanup Monitor] WARNING: {count} files in .tmp/ (threshold: {HIGH_THRESHOLD}). "
            f"Consider cleaning up old workflow outputs. "
            f"Run: find .tmp/ -name '*.md' -mtime +7 -delete (files older than 7 days)"
        )
    elif count > WARN_THRESHOLD:
        response["reason"] = (
            f"[Cleanup Monitor] NOTE: {count} files in .tmp/ (threshold: {WARN_THRESHOLD}). "
            f"Temp directory is growing. Review and clean up old outputs when convenient."
        )

    print(json.dumps(response))


if __name__ == "__main__":
    main()
