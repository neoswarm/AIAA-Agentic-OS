#!/usr/bin/env python3
"""
Hook 37: JSON Output Validator (PostToolUse on Write)

After writing .json files to .tmp/:
- Attempt to parse the content as JSON
- If invalid JSON: return BLOCK with reason
- If valid: check for common issues:
  - Empty objects/arrays
  - Null values in important fields
  - Truncated content (ends with ... or mid-word)
- ALLOW if valid JSON or not a .json file. BLOCK only for invalid JSON writes to .tmp/.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "json_validation_log.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"validations": [], "stats": {"total": 0, "blocked": 0, "warnings": 0, "passed": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def validate_json_content(content, filename):
    """Validate JSON content and check for issues."""
    # Try to parse
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        return "invalid", f"Invalid JSON in {filename}: {str(e)[:200]}", {}

    issues = []
    metrics = {"type": type(parsed).__name__}

    # Check for empty structures
    if isinstance(parsed, dict) and len(parsed) == 0:
        issues.append("JSON object is empty")
    elif isinstance(parsed, list) and len(parsed) == 0:
        issues.append("JSON array is empty")

    # Check for null values in top-level fields
    if isinstance(parsed, dict):
        null_fields = [k for k, v in parsed.items() if v is None]
        if null_fields:
            issues.append(f"Null values in fields: {', '.join(null_fields[:5])}")

        # Count fields
        metrics["field_count"] = len(parsed)

    elif isinstance(parsed, list):
        metrics["item_count"] = len(parsed)

    # Check for truncation indicators
    content_str = content.strip()
    if content_str.endswith("..."):
        issues.append("Content appears truncated (ends with '...')")
    if content_str.endswith(","):
        issues.append("Content appears truncated (ends with trailing comma)")

    # Check for very small output (potentially incomplete)
    if len(content) < 10:
        issues.append("JSON content is suspiciously small")

    if issues:
        return "warning", "; ".join(issues), metrics
    return "valid", "", metrics


def handle_status():
    state = load_state()
    print("=== JSON Output Validator Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"Total validations: {stats.get('total', 0)}")
    print(f"Passed: {stats.get('passed', 0)}")
    print(f"Warnings: {stats.get('warnings', 0)}")
    print(f"Blocked: {stats.get('blocked', 0)}")

    validations = state.get("validations", [])
    if validations:
        print(f"\nRecent validations:")
        for v in validations[-10:]:
            print(f"  [{v.get('result', '?').upper()}] {v.get('filename', '?')}")
            if v.get("message"):
                print(f"    {v['message'][:100]}")
    else:
        print("\nNo JSON files validated yet.")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("JSON output validator state reset.")
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

    # Only validate .json files in .tmp/
    if not file_path.endswith(".json") or ".tmp" not in file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    filename = Path(file_path).name
    state = load_state()
    state["stats"]["total"] = state["stats"].get("total", 0) + 1

    result, message, metrics = validate_json_content(content, filename)

    validation_record = {
        "filename": filename,
        "filepath": file_path,
        "result": result,
        "message": message,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
    }
    state["validations"].append(validation_record)
    state["validations"] = state["validations"][-50:]

    if result == "invalid":
        state["stats"]["blocked"] = state["stats"].get("blocked", 0) + 1
        save_state(state)
        print(json.dumps({"decision": "BLOCK", "reason": message}))
    elif result == "warning":
        state["stats"]["warnings"] = state["stats"].get("warnings", 0) + 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW", "reason": f"JSON warnings: {message}"}))
    else:
        state["stats"]["passed"] = state["stats"].get("passed", 0) + 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
