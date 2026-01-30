#!/usr/bin/env python3
"""
Hook 95: state_file_corruption_detector.py - PostToolUse on Bash

Detects corrupted .tmp/hooks/*.json state files. Validates each is valid JSON,
checks for truncation, encoding issues, or unexpected size changes.
Auto-repairs if possible.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional corruption warnings

CLI Flags:
  --status  Show state file health
  --reset   Clear corruption tracking state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "state_corruption.json"

MAX_REASONABLE_SIZE = 1024 * 1024  # 1MB - state files shouldn't be this big
MIN_REASONABLE_SIZE = 2            # {} is minimum valid JSON


def load_own_state():
    """Load this hook's own state (separate from files being checked)."""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "scans": [],
        "corrupted_files": [],
        "repaired_files": [],
        "total_scans": 0,
        "last_scan": None,
    }


def save_own_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["scans"] = state["scans"][-20:]
    state["corrupted_files"] = state["corrupted_files"][-20:]
    state["repaired_files"] = state["repaired_files"][-20:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def scan_state_files():
    """Scan all state files in .tmp/hooks/ for corruption."""
    if not STATE_DIR.exists():
        return [], []

    issues = []
    repaired = []

    for filepath in STATE_DIR.glob("*.json"):
        # Skip our own state file
        if filepath.name == "state_corruption.json":
            continue

        file_issues = validate_state_file(filepath)
        if file_issues:
            issues.append({
                "file": filepath.name,
                "issues": file_issues,
                "size": filepath.stat().st_size if filepath.exists() else 0,
            })

            # Attempt auto-repair
            repair_result = attempt_repair(filepath, file_issues)
            if repair_result:
                repaired.append({
                    "file": filepath.name,
                    "repair": repair_result,
                })

    return issues, repaired


def validate_state_file(filepath):
    """Validate a single state file. Returns list of issues."""
    issues = []

    try:
        stat = filepath.stat()
    except OSError as e:
        return [f"Cannot stat file: {e}"]

    # Size checks
    if stat.st_size > MAX_REASONABLE_SIZE:
        issues.append(f"File too large: {stat.st_size} bytes (max: {MAX_REASONABLE_SIZE})")

    if stat.st_size < MIN_REASONABLE_SIZE:
        issues.append(f"File too small: {stat.st_size} bytes (likely empty/corrupt)")
        return issues

    # Content validation
    try:
        content = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        issues.append("Encoding error: not valid UTF-8")
        return issues
    except OSError as e:
        issues.append(f"Read error: {e}")
        return issues

    # JSON validation
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        issues.append(f"Invalid JSON: {str(e)[:80]}")

        # Check for common corruption patterns
        if content.endswith('\x00'):
            issues.append("File contains null bytes (truncated write)")
        if content.count('{') != content.count('}'):
            issues.append(f"Unbalanced braces: {content.count('{')} open, {content.count('}')} close")
        if content.count('[') != content.count(']'):
            issues.append(f"Unbalanced brackets: {content.count('[')} open, {content.count(']')} close")

        return issues

    # Structure validation
    if not isinstance(data, dict):
        issues.append(f"Expected JSON object, got {type(data).__name__}")

    return issues


def attempt_repair(filepath, file_issues):
    """Attempt to repair a corrupted state file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    # Remove null bytes
    if '\x00' in content:
        content = content.replace('\x00', '')

    # Try to parse the cleaned content
    try:
        json.loads(content)
        filepath.write_text(content)
        return "Removed null bytes"
    except json.JSONDecodeError:
        pass

    # Try truncating to last complete JSON object
    for i in range(len(content) - 1, 0, -1):
        if content[i] == '}':
            try:
                data = json.loads(content[:i+1])
                filepath.write_text(json.dumps(data, indent=2))
                return "Truncated to last valid JSON"
            except json.JSONDecodeError:
                continue

    # Last resort: reset to empty object
    filepath.write_text('{}')
    return "Reset to empty object"


def handle_status():
    own_state = load_own_state()
    print("State File Corruption Detector Status")
    print(f"  Total scans: {own_state['total_scans']}")
    print(f"  Last scan: {own_state.get('last_scan', 'never')}")

    # Run a fresh scan
    if STATE_DIR.exists():
        state_files = list(STATE_DIR.glob("*.json"))
        print(f"  State files in .tmp/hooks/: {len(state_files)}")

        issues, repaired = scan_state_files()
        if issues:
            print(f"  Currently corrupted: {len(issues)}")
            for i in issues:
                print(f"    - {i['file']}: {'; '.join(i['issues'][:2])}")
        else:
            print("  All state files healthy")

        if repaired:
            print(f"  Auto-repaired: {len(repaired)}")
            for r in repaired:
                print(f"    - {r['file']}: {r['repair']}")
    else:
        print("  State directory does not exist yet")

    if own_state["corrupted_files"]:
        print("  Previously corrupted files:")
        for cf in own_state["corrupted_files"][-5:]:
            print(f"    - {cf}")

    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "scans": [], "corrupted_files": [],
        "repaired_files": [], "total_scans": 0, "last_scan": None,
    }))
    print("State File Corruption Detector: State reset.")
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
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")

    if tool_name != "Bash" or "tool_result" not in data:
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Run scan periodically (every invocation when triggered)
    own_state = load_own_state()
    own_state["total_scans"] += 1
    own_state["last_scan"] = datetime.now().isoformat()

    issues, repaired = scan_state_files()

    scan_entry = {
        "timestamp": datetime.now().isoformat(),
        "corrupted": len(issues),
        "repaired": len(repaired),
    }
    own_state["scans"].append(scan_entry)

    if issues:
        for i in issues:
            entry = f"{i['file']}: {'; '.join(i['issues'][:2])}"
            if entry not in own_state["corrupted_files"]:
                own_state["corrupted_files"].append(entry)

    if repaired:
        for r in repaired:
            entry = f"{r['file']}: {r['repair']}"
            if entry not in own_state["repaired_files"]:
                own_state["repaired_files"].append(entry)

    save_own_state(own_state)

    if issues:
        corrupted_names = [i["file"] for i in issues]
        reason = f"State file corruption detected in: {', '.join(corrupted_names)}"
        if repaired:
            reason += f". Auto-repaired: {', '.join(r['file'] for r in repaired)}"
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
