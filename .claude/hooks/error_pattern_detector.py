#!/usr/bin/env python3
"""
Hook 19: Error Pattern Detector
Type: PostToolUse on Bash tool
Tier: Advisory (always allows)

After execution scripts that fail, tracks error patterns per script.
When the same script fails 3+ times, writes a recurring failure warning
to stderr with recent error messages.

Tracks: error counts, last 5 error messages, first/last seen timestamps,
and recurring failures (3+ errors).

Protocol:
  - Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {...}, "tool_result": "..."}
  - Prints JSON to stdout: {"decision": "ALLOW"}
  - Warnings written to stderr
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR = Path("/Users/lucasnolan/Agentic OS/.tmp/hooks")
ERROR_FILE = STATE_DIR / "error_patterns.json"

RECURRING_THRESHOLD = 3
MAX_RECENT_ERRORS = 5

ERROR_INDICATORS = [
    "Traceback",
    "Error:",
    "Exception:",
    "FAILED",
    "error:",
    "fatal:",
    "ModuleNotFoundError",
    "FileNotFoundError",
    "KeyError:",
    "ValueError:",
    "TypeError:",
    "ImportError:",
]


def load_errors():
    """Load error pattern data."""
    try:
        if ERROR_FILE.exists():
            with open(ERROR_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {"scripts": {}}


def save_errors(data):
    """Save error pattern data."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(ERROR_FILE, "w") as f:
        json.dump(data, f, indent=2)


def extract_script_name(command: str) -> str:
    """Extract script filename from command."""
    match = re.search(r'python3?\s+(?:.*?/)?execution/(\S+\.py)', command)
    if match:
        return match.group(1)
    return "unknown.py"


def is_execution_script(command: str) -> bool:
    """Check if command runs an execution script."""
    return "python3 execution/" in command or "python execution/" in command


def has_error(tool_result: str) -> bool:
    """Check if tool_result contains error indicators."""
    if not tool_result:
        return False

    result_str = str(tool_result)

    # Check for non-zero exit code
    exit_match = re.search(r'exit\s+code[:\s]+(\d+)', result_str, re.IGNORECASE)
    if exit_match and int(exit_match.group(1)) != 0:
        return True

    for indicator in ERROR_INDICATORS:
        if indicator in result_str:
            return True

    return False


def extract_error_message(tool_result: str) -> str:
    """Extract a concise error message from tool_result."""
    result_str = str(tool_result)
    lines = result_str.splitlines()

    # Look for the most descriptive error line
    for line in reversed(lines):
        stripped = line.strip()
        for indicator in ERROR_INDICATORS:
            if indicator in stripped:
                return stripped[:200]

    # Fallback: last non-empty line
    for line in reversed(lines):
        if line.strip():
            return line.strip()[:200]

    return "Unknown error"


def check_status():
    """Show all tracked error patterns."""
    print("Error Pattern Detector - Status")
    print("=" * 50)
    data = load_errors()
    scripts = data.get("scripts", {})

    if not scripts:
        print("\nNo error patterns tracked.")
        sys.exit(0)

    recurring = {k: v for k, v in scripts.items()
                 if v.get("error_count", 0) >= RECURRING_THRESHOLD}
    other = {k: v for k, v in scripts.items()
             if v.get("error_count", 0) < RECURRING_THRESHOLD}

    if recurring:
        print(f"\n*** RECURRING FAILURES ({len(recurring)} scripts) ***")
        for name, info in sorted(recurring.items(), key=lambda x: x[1].get("error_count", 0), reverse=True):
            count = info.get("error_count", 0)
            first = info.get("first_seen", "?")[:19]
            last = info.get("last_seen", "?")[:19]
            print(f"\n  {name}: {count} failures")
            print(f"    First seen: {first}")
            print(f"    Last seen: {last}")
            print(f"    Recent errors:")
            for err in info.get("last_errors", []):
                print(f"      - {err}")

    if other:
        print(f"\n--- Other Errors ({len(other)} scripts) ---")
        for name, info in sorted(other.items()):
            count = info.get("error_count", 0)
            last = info.get("last_seen", "?")[:19]
            print(f"  {name}: {count} failure(s), last: {last}")

    total_errors = sum(v.get("error_count", 0) for v in scripts.values())
    print(f"\nTotal tracked errors: {total_errors}")
    print(f"Scripts with errors: {len(scripts)}")
    print(f"Recurring failures (3+): {len(recurring)}")

    sys.exit(0)


def check_reset():
    """Clear error history."""
    print("Error Pattern Detector - Reset")
    if ERROR_FILE.exists():
        os.remove(ERROR_FILE)
        print("Error history cleared.")
    else:
        print("No error file to clear.")
    sys.exit(0)


def main():
    # Handle CLI flags
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            check_status()
        elif sys.argv[1] == "--reset":
            check_reset()

    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")
    tool_result = data.get("tool_result", "")

    # Only care about execution scripts
    if not is_execution_script(command):
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    # Only track errors
    if not has_error(str(tool_result)):
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    script_name = extract_script_name(command)
    error_message = extract_error_message(str(tool_result))
    now = datetime.now(timezone.utc).isoformat()

    # Load and update error data
    error_data = load_errors()
    scripts = error_data.setdefault("scripts", {})

    if script_name not in scripts:
        scripts[script_name] = {
            "error_count": 0,
            "last_errors": [],
            "first_seen": now,
            "last_seen": now,
        }

    entry = scripts[script_name]
    entry["error_count"] += 1
    entry["last_seen"] = now

    # Keep last N error messages
    last_errors = entry.get("last_errors", [])
    last_errors.append(error_message)
    if len(last_errors) > MAX_RECENT_ERRORS:
        last_errors = last_errors[-MAX_RECENT_ERRORS:]
    entry["last_errors"] = last_errors

    save_errors(error_data)

    # If recurring failure, emit warning
    error_count = entry["error_count"]
    if error_count >= RECURRING_THRESHOLD:
        recent = entry["last_errors"][-3:]
        error_list = "\n".join(f"  - {e}" for e in recent)
        warning = (
            f"\n[ERROR PATTERN] {script_name} has failed {error_count} times.\n"
            f"Recent errors:\n"
            f"{error_list}\n"
            f"Consider investigating root cause or updating the directive.\n\n"
        )
        sys.stderr.write(warning)

    print(json.dumps({"decision": "ALLOW"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
