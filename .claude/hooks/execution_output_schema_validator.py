#!/usr/bin/env python3
"""
Hook 72: execution_output_schema_validator.py - PostToolUse on Bash

After running execution scripts, validates the output mentions expected artifacts
(file paths, success messages, etc.) and checks for common failure patterns.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional warnings

CLI Flags:
  --status  Show validation stats
  --reset   Clear state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "execution_output_validation.json"

# Common failure patterns in script output
FAILURE_PATTERNS = [
    (r'Traceback \(most recent call last\)', "Python traceback detected"),
    (r'(?:^|\n)\s*Error:', "Error message detected"),
    (r'(?:^|\n)\s*Exception:', "Exception detected"),
    (r'ModuleNotFoundError', "Missing Python module"),
    (r'FileNotFoundError', "File not found error"),
    (r'PermissionError', "Permission denied error"),
    (r'ConnectionError', "Connection error"),
    (r'TimeoutError', "Timeout error"),
    (r'KeyError:', "Missing key error"),
    (r'TypeError:', "Type error"),
    (r'ValueError:', "Value error"),
    (r'JSONDecodeError', "JSON parsing error"),
    (r'HTTP\s*(?:4\d{2}|5\d{2})', "HTTP error status code"),
    (r'rate.?limit', "Rate limit hit"),
]

# Success indicators
SUCCESS_PATTERNS = [
    r'(?:saved|written|created|generated)\s+(?:to|at|in)\s+',
    r'\.tmp/',
    r'Success',
    r'Complete',
    r'Done',
    r'Output:',
    r'Created:\s*\S+',
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "validations": [],
        "failures_detected": 0,
        "successes_detected": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Keep last 50 validations
    state["validations"] = state["validations"][-50:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_script_name(command):
    """Extract script name from execution command."""
    match = re.search(r'python3?\s+(?:\S*/)?execution/(\S+\.py)', command)
    return match.group(1) if match else None


def check_failures(output):
    """Check output for failure patterns. Returns list of issues found."""
    issues = []
    for pattern, description in FAILURE_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE):
            issues.append(description)
    return issues


def check_success(output):
    """Check output for success indicators. Returns list of indicators found."""
    indicators = []
    for pattern in SUCCESS_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE):
            indicators.append(pattern)
    return indicators


def extract_file_paths(output):
    """Extract file paths mentioned in output."""
    paths = []
    # Match common path patterns
    path_patterns = [
        r'(?:saved|written|created|output)\s+(?:to|at|in)\s+["\']?(\S+\.(?:md|json|txt|html|csv|py))',
        r'(\.tmp/\S+)',
        r'(/\S+\.(?:md|json|txt|html|csv))',
    ]
    for pattern in path_patterns:
        matches = re.findall(pattern, output, re.IGNORECASE)
        paths.extend(matches)
    return list(set(paths))


def handle_status():
    state = load_state()
    print("Execution Output Schema Validator Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Successes detected: {state['successes_detected']}")
    print(f"  Failures detected: {state['failures_detected']}")
    if state["validations"]:
        print("  Recent validations:")
        for v in state["validations"][-5:]:
            status = "FAIL" if v.get("issues") else "OK"
            print(f"    [{status}] {v.get('script', 'unknown')} - {v.get('timestamp', '')[:19]}")
            if v.get("issues"):
                for issue in v["issues"]:
                    print(f"      - {issue}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "validations": [], "failures_detected": 0,
        "successes_detected": 0, "total_checks": 0,
    }))
    print("Execution Output Schema Validator: State reset.")
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
    tool_result = data.get("tool_result", "")

    # PostToolUse only on Bash
    if tool_name != "Bash" or "tool_result" not in data:
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    script_name = extract_script_name(command)
    if not script_name:
        print(json.dumps({"decision": "ALLOW"}))
        return

    output = str(tool_result) if tool_result else ""
    state = load_state()
    state["total_checks"] += 1

    issues = check_failures(output)
    success_indicators = check_success(output)
    file_paths = extract_file_paths(output)

    validation = {
        "script": script_name,
        "timestamp": datetime.now().isoformat(),
        "issues": issues,
        "success_indicators": len(success_indicators),
        "file_paths": file_paths,
    }
    state["validations"].append(validation)

    if issues:
        state["failures_detected"] += 1
        save_state(state)
        reason = f"Script {script_name} output has issues: {'; '.join(issues)}"
        # Warn but allow - the agent should decide how to handle
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        state["successes_detected"] += 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
