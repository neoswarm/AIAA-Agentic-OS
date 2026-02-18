#!/usr/bin/env python3
"""
Hook 117: context_load_optimizer.py (PostToolUse on Read)
Purpose: Suggest lighter context loads when context is getting heavy.
Logic: Track total bytes loaded from context/skill/directive files.
If exceeding threshold, suggest which files to skip or summarize.
Score files by relevance to current workflow.

Protocol:
  - PostToolUse: prints JSON to stdout {"decision": "ALLOW"}
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "context_load.json"

# Thresholds in bytes
WARN_THRESHOLD = 500_000      # 500KB
HEAVY_THRESHOLD = 1_000_000   # 1MB
CRITICAL_THRESHOLD = 2_000_000  # 2MB

# File type weights (lower = more essential)
FILE_PRIORITY = {
    "context/agency.md": 1,
    "context/brand_voice.md": 2,
    "context/owner.md": 3,
    "context/services.md": 3,
    "clients/*/profile.md": 2,
    "clients/*/rules.md": 2,
    "clients/*/preferences.md": 4,
    "clients/*/history.md": 5,
    "directives/": 3,
    "skills/SKILL_BIBLE_": 6,
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "session_bytes_loaded": 0,
        "files_loaded": [],
        "file_sizes": {},
        "warnings_issued": 0,
        "total_reads": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_file_priority(file_path):
    """Get priority for a file (lower = more important)."""
    for pattern, priority in FILE_PRIORITY.items():
        if pattern.endswith("/"):
            if pattern in file_path:
                return priority
        elif "*" in pattern:
            parts = pattern.split("*")
            if all(p in file_path for p in parts if p):
                return priority
        elif pattern in file_path:
            return priority
    return 5  # Default priority


def is_context_file(file_path):
    """Check if this is a context/skill/directive file."""
    context_dirs = ["context/", "clients/", "directives/", "skills/"]
    return any(d in file_path for d in context_dirs)


def suggest_optimizations(files_loaded, total_bytes):
    """Suggest files to skip or summarize."""
    suggestions = []

    # Sort by priority (higher priority number = more skippable)
    prioritized = sorted(files_loaded,
                         key=lambda f: (get_file_priority(f.get("path", "")),
                                       -f.get("size", 0)),
                         reverse=True)

    target_reduction = total_bytes - WARN_THRESHOLD
    reduced = 0

    for f in prioritized:
        if reduced >= target_reduction:
            break
        priority = get_file_priority(f.get("path", ""))
        if priority >= 5:  # Low priority files
            suggestions.append({
                "action": "skip",
                "file": Path(f.get("path", "")).name,
                "size": f.get("size", 0),
                "priority": priority
            })
            reduced += f.get("size", 0)
        elif priority >= 4:
            suggestions.append({
                "action": "summarize",
                "file": Path(f.get("path", "")).name,
                "size": f.get("size", 0),
                "priority": priority
            })
            reduced += f.get("size", 0) // 2  # Assume summarizing halves size

    return suggestions


def format_bytes(b):
    """Format bytes to human-readable."""
    if b >= 1_000_000:
        return f"{b / 1_000_000:.1f}MB"
    elif b >= 1_000:
        return f"{b / 1_000:.0f}KB"
    return f"{b}B"


def show_status():
    state = load_state()
    total = state.get("session_bytes_loaded", 0)
    files = state.get("files_loaded", [])
    file_sizes = state.get("file_sizes", {})

    print("=== Context Load Optimizer ===")
    print(f"Total context loaded: {format_bytes(total)}")
    print(f"Files loaded this session: {len(files)}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    print(f"Thresholds: Warn={format_bytes(WARN_THRESHOLD)}, Heavy={format_bytes(HEAVY_THRESHOLD)}, Critical={format_bytes(CRITICAL_THRESHOLD)}")

    # Status indicator
    if total >= CRITICAL_THRESHOLD:
        print(f"Status: CRITICAL - Context is very heavy")
    elif total >= HEAVY_THRESHOLD:
        print(f"Status: HEAVY - Consider reducing context")
    elif total >= WARN_THRESHOLD:
        print(f"Status: WARNING - Approaching threshold")
    else:
        print(f"Status: OK")

    if files:
        print("\nLoaded files (by size):")
        sorted_files = sorted(files, key=lambda f: f.get("size", 0), reverse=True)
        for f in sorted_files[:15]:
            name = Path(f.get("path", "?")).name
            size = f.get("size", 0)
            priority = get_file_priority(f.get("path", ""))
            priority_label = {1: "ESSENTIAL", 2: "HIGH", 3: "MEDIUM", 4: "LOW", 5: "OPTIONAL", 6: "SKIPPABLE"}
            print(f"  {format_bytes(size):>8s}  [{priority_label.get(priority, 'UNKNOWN'):10s}]  {name}")

    if total > WARN_THRESHOLD:
        suggestions = suggest_optimizations(files, total)
        if suggestions:
            print("\nOptimization suggestions:")
            for s in suggestions:
                action = s["action"].upper()
                fname = s["file"]
                size = format_bytes(s["size"])
                print(f"  [{action}] {fname} ({size})")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Context load optimizer state reset.")
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
    tool_result = data.get("tool_result", "")

    if tool_name not in ("Read", "read"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    if not is_context_file(file_path):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()
    state["total_reads"] = state.get("total_reads", 0) + 1

    # Estimate file size from result
    content = str(tool_result) if tool_result else ""
    file_size = len(content.encode("utf-8", errors="replace"))

    # Track file
    files = state.get("files_loaded", [])
    # Don't double-count same file
    existing_paths = [f.get("path") for f in files]
    if file_path not in existing_paths:
        files.append({
            "path": file_path,
            "size": file_size,
            "timestamp": now,
            "priority": get_file_priority(file_path)
        })
        state["session_bytes_loaded"] = state.get("session_bytes_loaded", 0) + file_size
    state["files_loaded"] = files

    # Track sizes
    file_sizes = state.get("file_sizes", {})
    file_sizes[file_path] = file_size
    state["file_sizes"] = file_sizes

    total = state["session_bytes_loaded"]

    # Check thresholds
    if total >= CRITICAL_THRESHOLD:
        state["warnings_issued"] = state.get("warnings_issued", 0) + 1
        suggestions = suggest_optimizations(files, total)
        suggestion_text = ""
        if suggestions:
            suggestion_text = " Suggestions: " + ", ".join(
                f"{s['action']} {s['file']}" for s in suggestions[:3]
            )
        save_state(state)
        output = {
            "decision": "ALLOW",
            "reason": f"[Context Optimizer] CRITICAL: {format_bytes(total)} loaded. Context is very heavy.{suggestion_text}"
        }
        print(json.dumps(output))
        return

    if total >= WARN_THRESHOLD:
        state["warnings_issued"] = state.get("warnings_issued", 0) + 1
        save_state(state)
        output = {
            "decision": "ALLOW",
            "reason": f"[Context Optimizer] WARNING: {format_bytes(total)} of context loaded. Consider lighter loads."
        }
        print(json.dumps(output))
        return

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
