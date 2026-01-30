#!/usr/bin/env python3
"""
Hook 77: workflow_checkpoint_validator.py - PostToolUse on Bash

After script execution, validates that checkpoint files in .tmp/ contain valid
data (non-empty, valid JSON/Markdown, expected structure).

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional warnings

CLI Flags:
  --status  Show checkpoint validation stats
  --reset   Clear state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
TMP_DIR = BASE_DIR / ".tmp"
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "checkpoint_validations.json"

MIN_FILE_SIZE_BYTES = 50  # Files smaller than this are likely empty/corrupt


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "validations": [],
        "invalid_checkpoints": [],
        "valid_checkpoints": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["validations"] = state["validations"][-50:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_script_name(command):
    match = re.search(r'python3?\s+(?:\S*/)?execution/(\S+\.py)', command)
    return match.group(1) if match else None


def find_recent_tmp_files(before_time=None, after_time=None):
    """Find files in .tmp/ that were recently modified."""
    if not TMP_DIR.exists():
        return []
    recent = []
    cutoff = datetime.now().timestamp() - 30  # Last 30 seconds
    for f in TMP_DIR.rglob("*"):
        if f.is_file() and "hooks" not in str(f):
            if f.stat().st_mtime > cutoff:
                recent.append(f)
    return recent


def validate_json_file(filepath):
    """Validate a JSON file."""
    issues = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
        if len(content.strip()) == 0:
            issues.append("File is empty")
            return issues
        data = json.loads(content)
        if isinstance(data, dict) and len(data) == 0:
            issues.append("JSON object is empty")
        elif isinstance(data, list) and len(data) == 0:
            issues.append("JSON array is empty")
    except json.JSONDecodeError as e:
        issues.append(f"Invalid JSON: {str(e)[:80]}")
    except OSError as e:
        issues.append(f"Read error: {str(e)[:80]}")
    return issues


def validate_markdown_file(filepath):
    """Validate a Markdown file."""
    issues = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
        if len(content.strip()) == 0:
            issues.append("File is empty")
            return issues
        if filepath.stat().st_size < MIN_FILE_SIZE_BYTES:
            issues.append(f"File very small ({filepath.stat().st_size} bytes)")
        # Check for headers
        headers = re.findall(r'^#+\s+', content, re.MULTILINE)
        if not headers and len(content) > 200:
            issues.append("No markdown headers found in substantial file")
        # Check for truncation indicators
        if content.rstrip().endswith("...") or content.rstrip().endswith("…"):
            issues.append("File may be truncated (ends with ellipsis)")
    except OSError as e:
        issues.append(f"Read error: {str(e)[:80]}")
    return issues


def validate_checkpoint(filepath):
    """Validate a checkpoint file based on its extension."""
    suffix = filepath.suffix.lower()
    if suffix == ".json":
        return validate_json_file(filepath)
    elif suffix in (".md", ".markdown"):
        return validate_markdown_file(filepath)
    elif suffix in (".txt", ".csv", ".html"):
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
            if len(content.strip()) == 0:
                return ["File is empty"]
        except OSError as e:
            return [f"Read error: {str(e)[:80]}"]
    return []


def handle_status():
    state = load_state()
    print("Workflow Checkpoint Validator Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Valid checkpoints: {state['valid_checkpoints']}")
    print(f"  Invalid checkpoints: {len(state['invalid_checkpoints'])}")
    if state["invalid_checkpoints"]:
        print("  Recent invalid checkpoints:")
        for ic in state["invalid_checkpoints"][-5:]:
            print(f"    - {ic}")
    if state["validations"]:
        print("  Recent validations:")
        for v in state["validations"][-5:]:
            status = "INVALID" if v.get("issues") else "VALID"
            print(f"    [{status}] {v.get('file', 'unknown')}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "validations": [], "invalid_checkpoints": [],
        "valid_checkpoints": 0, "total_checks": 0,
    }))
    print("Workflow Checkpoint Validator: State reset.")
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
    tool_input = data.get("tool_input", {})

    if tool_name != "Bash" or "tool_result" not in data:
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    script_name = extract_script_name(command)
    if not script_name:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    recent_files = find_recent_tmp_files()
    all_issues = []

    for filepath in recent_files:
        issues = validate_checkpoint(filepath)
        rel_path = str(filepath.relative_to(BASE_DIR))
        validation = {
            "file": rel_path,
            "script": script_name,
            "issues": issues,
            "timestamp": datetime.now().isoformat(),
        }
        state["validations"].append(validation)

        if issues:
            state["invalid_checkpoints"].append(f"{rel_path}: {'; '.join(issues)}")
            all_issues.extend([f"{rel_path}: {i}" for i in issues])
        else:
            state["valid_checkpoints"] += 1

    save_state(state)

    if all_issues:
        reason = "Checkpoint validation issues:\n" + "\n".join(all_issues[:5])
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
