#!/usr/bin/env python3
"""
Hook 45: File Size Limit Guard (PreToolUse on Write)

Before writing any file:
- Check content length
- If content > 100,000 characters (~100KB): WARN via stderr
- If content > 500,000 characters: BLOCK (exit 2)
- Track large file writes in .tmp/hooks/large_files.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "large_files.json"

WARN_THRESHOLD = 100_000      # 100K chars
BLOCK_THRESHOLD = 500_000     # 500K chars


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"large_writes": [], "stats": {"total_checks": 0, "warnings": 0, "blocks": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def format_size(chars):
    """Format character count as human-readable size."""
    if chars >= 1_000_000:
        return f"{chars / 1_000_000:.1f}M chars (~{chars // 1000}KB)"
    elif chars >= 1_000:
        return f"{chars / 1_000:.1f}K chars (~{chars // 1000}KB)"
    return f"{chars} chars"


def handle_status():
    state = load_state()
    print("=== File Size Limit Guard Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")
    print(f"\nThresholds:")
    print(f"  Warning: {format_size(WARN_THRESHOLD)}")
    print(f"  Block: {format_size(BLOCK_THRESHOLD)}")

    stats = state.get("stats", {})
    print(f"\nTotal checks: {stats.get('total_checks', 0)}")
    print(f"Warnings: {stats.get('warnings', 0)}")
    print(f"Blocks: {stats.get('blocks', 0)}")

    large_writes = state.get("large_writes", [])
    if large_writes:
        print(f"\nLarge file writes:")
        for w in large_writes[-10:]:
            action = w.get("action", "unknown").upper()
            size = format_size(w.get("size", 0))
            print(f"  [{action}] {w.get('filename', '?')}: {size}")
            print(f"    Path: {w.get('filepath', '?')}")
            print(f"    Time: {w.get('timestamp', '?')}")
    else:
        print("\nNo large file writes recorded.")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("File size limit guard state reset.")
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
    content = tool_input.get("content", "")

    if not content:
        sys.exit(0)

    content_size = len(content)

    # Only track and act on large files
    if content_size < WARN_THRESHOLD:
        sys.exit(0)

    state = load_state()
    state["stats"]["total_checks"] = state["stats"].get("total_checks", 0) + 1

    filename = Path(file_path).name
    size_str = format_size(content_size)

    record = {
        "filename": filename,
        "filepath": file_path,
        "size": content_size,
        "size_formatted": size_str,
        "timestamp": datetime.now().isoformat(),
    }

    if content_size > BLOCK_THRESHOLD:
        record["action"] = "block"
        state["stats"]["blocks"] = state["stats"].get("blocks", 0) + 1
        state["large_writes"].append(record)
        state["large_writes"] = state["large_writes"][-50:]
        save_state(state)

        sys.stderr.write(
            f"[FILE SIZE] BLOCKED: File too large: {size_str} to {filename}. "
            f"Maximum: {format_size(BLOCK_THRESHOLD)}. "
            f"Consider splitting into multiple files.\n"
        )
        sys.exit(2)
    else:
        record["action"] = "warn"
        state["stats"]["warnings"] = state["stats"].get("warnings", 0) + 1
        state["large_writes"].append(record)
        state["large_writes"] = state["large_writes"][-50:]
        save_state(state)

        sys.stderr.write(
            f"[FILE SIZE] Large file write: {size_str} to {filename}\n"
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
