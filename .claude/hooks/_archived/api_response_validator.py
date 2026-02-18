#!/usr/bin/env python3
"""
Hook 91: api_response_validator.py - PostToolUse on Bash

Validates API responses from execution scripts are valid before further processing.
Checks for well-formed JSON, HTTP errors (4xx, 5xx), timeout indicators,
and rate limit responses.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional API error warnings

CLI Flags:
  --status  Show API response validation stats
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
STATE_FILE = STATE_DIR / "api_response_validation.json"

# HTTP error patterns
HTTP_ERROR_PATTERNS = [
    (r'HTTP[/ ]?\s*4[0-9]{2}', "Client error (4xx)"),
    (r'HTTP[/ ]?\s*5[0-9]{2}', "Server error (5xx)"),
    (r'status[_\s]*code[:\s]*4\d{2}', "Client error status code"),
    (r'status[_\s]*code[:\s]*5\d{2}', "Server error status code"),
    (r'"status"\s*:\s*4\d{2}', "JSON status 4xx"),
    (r'"status"\s*:\s*5\d{2}', "JSON status 5xx"),
]

# Timeout patterns
TIMEOUT_PATTERNS = [
    (r'timeout', "Timeout detected"),
    (r'timed?\s*out', "Timed out"),
    (r'connection\s*reset', "Connection reset"),
    (r'ETIMEDOUT', "TCP timeout"),
    (r'deadline\s*exceeded', "Deadline exceeded"),
]

# Rate limit patterns
RATE_LIMIT_PATTERNS = [
    (r'rate.?limit', "Rate limit hit"),
    (r'429', "HTTP 429 Too Many Requests"),
    (r'too.?many.?requests', "Too many requests"),
    (r'quota.?exceeded', "Quota exceeded"),
    (r'throttl', "Throttled"),
]

# JSON response detection
JSON_RESPONSE_PATTERN = re.compile(r'\{[\s\S]*\}')


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "validations": [],
        "http_errors": 0,
        "timeouts": 0,
        "rate_limits": 0,
        "json_errors": 0,
        "clean": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["validations"] = state["validations"][-50:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_script_name(command):
    match = re.search(r'python3?\s+(?:\S*/)?execution/(\S+\.py)', command)
    return match.group(1) if match else None


def check_http_errors(output):
    issues = []
    for pattern, desc in HTTP_ERROR_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE):
            issues.append(desc)
    return list(set(issues))


def check_timeouts(output):
    issues = []
    for pattern, desc in TIMEOUT_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE):
            issues.append(desc)
    return list(set(issues))


def check_rate_limits(output):
    issues = []
    for pattern, desc in RATE_LIMIT_PATTERNS:
        if re.search(pattern, output, re.IGNORECASE):
            issues.append(desc)
    return list(set(issues))


def check_json_validity(output):
    """Check if JSON responses in output are well-formed."""
    issues = []
    # Find potential JSON blocks
    json_blocks = JSON_RESPONSE_PATTERN.findall(output)
    for block in json_blocks[:5]:
        try:
            json.loads(block)
        except json.JSONDecodeError:
            # Only flag if it looks like it was meant to be JSON
            if '"error"' in block or '"status"' in block or '"data"' in block:
                issues.append("Malformed JSON response detected")
                break
    return issues


def handle_status():
    state = load_state()
    print("API Response Validator Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Clean responses: {state['clean']}")
    print(f"  HTTP errors: {state['http_errors']}")
    print(f"  Timeouts: {state['timeouts']}")
    print(f"  Rate limits: {state['rate_limits']}")
    print(f"  JSON errors: {state['json_errors']}")
    if state["validations"]:
        print("  Recent validations:")
        for v in state["validations"][-5:]:
            issues = v.get("issues", [])
            status = "ERROR" if issues else "OK"
            print(f"    [{status}] {v.get('script', 'unknown')}")
            for i in issues[:3]:
                print(f"      - {i}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "validations": [], "http_errors": 0, "timeouts": 0,
        "rate_limits": 0, "json_errors": 0, "clean": 0, "total_checks": 0,
    }))
    print("API Response Validator: State reset.")
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

    if tool_name != "Bash" or "tool_result" not in data:
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    script_name = extract_script_name(command)
    if not script_name:
        print(json.dumps({"decision": "ALLOW"}))
        return

    output = str(tool_result) if tool_result else ""
    if not output:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    all_issues = []

    http_issues = check_http_errors(output)
    if http_issues:
        state["http_errors"] += 1
        all_issues.extend(http_issues)

    timeout_issues = check_timeouts(output)
    if timeout_issues:
        state["timeouts"] += 1
        all_issues.extend(timeout_issues)

    rate_issues = check_rate_limits(output)
    if rate_issues:
        state["rate_limits"] += 1
        all_issues.extend(rate_issues)

    json_issues = check_json_validity(output)
    if json_issues:
        state["json_errors"] += 1
        all_issues.extend(json_issues)

    validation = {
        "script": script_name,
        "issues": all_issues,
        "timestamp": datetime.now().isoformat(),
    }
    state["validations"].append(validation)

    if all_issues:
        save_state(state)
        reason = f"API response issues from {script_name}: " + "; ".join(all_issues[:5])
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        state["clean"] += 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
