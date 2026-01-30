#!/usr/bin/env python3
"""
Hook 116: error_categorizer.py (PostToolUse on Bash)
Purpose: Classify errors by type for better debugging.
Logic: When execution errors occur, categorize: API_ERROR, AUTH_ERROR, INPUT_ERROR,
NETWORK_ERROR, TIMEOUT_ERROR, SCRIPT_BUG, CONFIG_ERROR.
Track error distribution in state.

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
STATE_FILE = STATE_DIR / "error_categories.json"

# Error category patterns (checked in order - first match wins)
ERROR_CATEGORIES = {
    "AUTH_ERROR": [
        r'401\s', r'403\s', r'unauthorized', r'forbidden',
        r'invalid.*api.*key', r'authentication.*fail', r'access.*denied',
        r'InvalidApiKey', r'AuthenticationError', r'permission.*denied',
    ],
    "NETWORK_ERROR": [
        r'ConnectionError', r'ConnectionRefused', r'connection.*refused',
        r'ECONNREFUSED', r'ENOTFOUND', r'dns.*resolution',
        r'network.*unreachable', r'socket.*timeout', r'SSLError',
        r'RemoteDisconnected', r'ConnectionReset',
    ],
    "TIMEOUT_ERROR": [
        r'TimeoutError', r'timed?\s*out', r'timeout',
        r'504\s', r'408\s', r'deadline.*exceeded',
        r'ReadTimeout', r'ConnectTimeout',
    ],
    "API_ERROR": [
        r'429\s', r'500\s', r'502\s', r'503\s',
        r'rate.*limit', r'quota.*exceeded', r'too.*many.*requests',
        r'APIError', r'ServiceUnavailable', r'InternalServerError',
        r'api.*error', r'openrouter.*error', r'perplexity.*error',
    ],
    "INPUT_ERROR": [
        r'ValueError', r'TypeError', r'KeyError',
        r'missing.*argument', r'required.*argument', r'invalid.*input',
        r'no.*such.*file', r'FileNotFoundError', r'not.*found',
        r'ArgumentError', r'invalid.*option', r'unrecognized.*argument',
    ],
    "CONFIG_ERROR": [
        r'ModuleNotFoundError', r'ImportError', r'No module named',
        r'env.*not.*set', r'missing.*config', r'configuration.*error',
        r'GOOGLE_APPLICATION_CREDENTIALS', r'\.env.*not found',
        r'RequiredConfigMissing',
    ],
    "SCRIPT_BUG": [
        r'Traceback.*most recent', r'SyntaxError', r'IndentationError',
        r'NameError', r'AttributeError', r'IndexError',
        r'ZeroDivisionError', r'RecursionError', r'RuntimeError',
        r'AssertionError', r'NotImplementedError',
    ],
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "errors": [],
        "category_counts": {},
        "by_script": {},
        "total_errors": 0,
        "total_checked": 0,
        "error_free_runs": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def categorize_error(result_text):
    """Categorize an error by matching patterns."""
    for category, patterns in ERROR_CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern, result_text, re.IGNORECASE):
                return category
    return "UNKNOWN_ERROR"


def extract_error_message(result_text):
    """Extract the most relevant error message."""
    lines = result_text.strip().split("\n")
    # Look for common error patterns
    for line in reversed(lines):
        line = line.strip()
        if any(keyword in line for keyword in ["Error:", "Exception:", "error:", "failed"]):
            return line[:200]
    # Fallback: last non-empty line
    for line in reversed(lines):
        if line.strip():
            return line.strip()[:200]
    return "Unknown error"


def has_error(result_text):
    """Check if the result contains an error."""
    error_indicators = [
        r'Traceback', r'Error:', r'Exception:', r'FAILED',
        r'error:', r'fatal:', r'CRITICAL', r'panic:',
        r'errno', r'exit\s+code\s+[1-9]', r'return\s+code\s+[1-9]',
    ]
    for pattern in error_indicators:
        if re.search(pattern, result_text, re.IGNORECASE):
            return True
    return False


def extract_script_name(command):
    """Extract script name from command."""
    match = re.search(r'execution/([a-zA-Z0-9_-]+\.py)', command)
    if match:
        return match.group(1)
    return None


def show_status():
    state = load_state()
    errors = state.get("errors", [])
    category_counts = state.get("category_counts", {})
    by_script = state.get("by_script", {})
    total_checked = state.get("total_checked", 0)
    total_errors = state.get("total_errors", 0)
    error_free = state.get("error_free_runs", 0)

    print("=== Error Categorizer ===")
    print(f"Total commands checked: {total_checked}")
    print(f"Total errors: {total_errors}")
    print(f"Error-free runs: {error_free}")

    if total_checked > 0:
        error_rate = (total_errors / total_checked) * 100
        print(f"Error rate: {error_rate:.1f}%")

    if category_counts:
        print("\nError distribution:")
        total = sum(category_counts.values())
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total) * 100 if total > 0 else 0
            bar = "#" * int(pct / 5)
            print(f"  {category:20s} {count:3d} ({pct:5.1f}%) {bar}")

    if by_script:
        print("\nErrors by script:")
        sorted_scripts = sorted(by_script.items(),
                                key=lambda x: x[1].get("error_count", 0),
                                reverse=True)
        for name, data in sorted_scripts[:10]:
            err_count = data.get("error_count", 0)
            categories = data.get("categories", {})
            cat_str = ", ".join(f"{c}:{n}" for c, n in categories.items())
            print(f"  {name}: {err_count} errors ({cat_str})")

    if errors:
        print(f"\nRecent errors (last {min(5, len(errors))}):")
        for e in errors[-5:]:
            ts = e.get("timestamp", "?")[:19]
            cat = e.get("category", "?")
            script = e.get("script", "?")
            msg = e.get("message", "?")[:80]
            print(f"  [{ts}] [{cat}] {script}: {msg}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Error categorizer state reset.")
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

    if tool_name not in ("Bash", "bash"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    if "execution/" not in command:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checked"] = state.get("total_checked", 0) + 1
    now = datetime.now().isoformat()

    result_text = str(tool_result) if tool_result else ""
    script_name = extract_script_name(command) or "unknown"

    if not has_error(result_text):
        state["error_free_runs"] = state.get("error_free_runs", 0) + 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Error detected - categorize it
    category = categorize_error(result_text)
    message = extract_error_message(result_text)

    state["total_errors"] = state.get("total_errors", 0) + 1

    # Update category counts
    counts = state.get("category_counts", {})
    counts[category] = counts.get(category, 0) + 1
    state["category_counts"] = counts

    # Update by script
    by_script = state.get("by_script", {})
    if script_name not in by_script:
        by_script[script_name] = {"error_count": 0, "categories": {}}
    by_script[script_name]["error_count"] += 1
    script_cats = by_script[script_name].get("categories", {})
    script_cats[category] = script_cats.get(category, 0) + 1
    by_script[script_name]["categories"] = script_cats
    state["by_script"] = by_script

    # Log error
    error_entry = {
        "timestamp": now,
        "script": script_name,
        "category": category,
        "message": message,
        "command": command[:200]
    }
    state["errors"] = state.get("errors", [])
    state["errors"].append(error_entry)
    state["errors"] = state["errors"][-200:]

    save_state(state)

    output = {
        "decision": "ALLOW",
        "reason": f"[Error Categorizer] {category}: {message[:100]}"
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
