#!/usr/bin/env python3
"""
Hook 13: Execution Logger
Type: PostToolUse on Bash tool
Tier: Passive (always allows, logs silently)

After any bash command containing 'python3 execution/' or 'python execution/',
logs the execution details (timestamp, script name, command, exit code, success)
to .tmp/hooks/execution_log.json. Keeps the last 500 entries.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {...}, "tool_result": "..."}
  - Prints JSON to stdout: {"decision": "ALLOW"}
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR = Path("/Users/lucasnolan/Agentic OS/.tmp/hooks")
LOG_FILE = STATE_DIR / "execution_log.json"
MAX_ENTRIES = 500


def load_log():
    """Load the execution log."""
    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {"entries": []}


def save_log(log_data):
    """Save the execution log, trimming to MAX_ENTRIES."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    entries = log_data.get("entries", [])
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]
        log_data["entries"] = entries
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=2)


def extract_script_name(command: str) -> str:
    """Extract the script filename from a command."""
    # Match python3 execution/something.py or python execution/something.py
    match = re.search(r'python3?\s+(?:.*?/)?execution/(\S+\.py)', command)
    if match:
        return match.group(1)
    return "unknown"


def detect_exit_code(tool_result: str) -> tuple:
    """Try to detect exit code from tool_result. Returns (exit_code, success)."""
    if not tool_result:
        return ("unknown", True)

    # Check for explicit exit code patterns
    exit_match = re.search(r'exit\s+code[:\s]+(\d+)', tool_result, re.IGNORECASE)
    if exit_match:
        code = int(exit_match.group(1))
        return (code, code == 0)

    # Check for error indicators
    error_indicators = ["Traceback", "Error:", "Exception:", "FAILED", "error:", "fatal:"]
    for indicator in error_indicators:
        if indicator in tool_result:
            return (1, False)

    return (0, True)


def check_status():
    """Print last 10 executions with success/fail counts."""
    print("Execution Logger - Status")
    print("=" * 50)
    log_data = load_log()
    entries = log_data.get("entries", [])

    total = len(entries)
    successes = sum(1 for e in entries if e.get("success", False))
    failures = total - successes

    print(f"\nTotal logged executions: {total}")
    print(f"Successes: {successes} | Failures: {failures}")
    if total > 0:
        print(f"Success rate: {successes / total * 100:.1f}%")

    print(f"\nLast 10 executions:")
    last_10 = entries[-10:] if len(entries) >= 10 else entries
    for entry in reversed(last_10):
        status = "OK" if entry.get("success") else "FAIL"
        ts = entry.get("timestamp", "?")[:19]
        script = entry.get("script_name", "?")
        print(f"  [{status}] {ts} - {script}")

    sys.exit(0)


def check_reset():
    """Clear the execution log."""
    print("Execution Logger - Reset")
    if LOG_FILE.exists():
        os.remove(LOG_FILE)
        print("Execution log cleared.")
    else:
        print("No log file to clear.")
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

    # Only log execution script commands
    if "python3 execution/" not in command and "python execution/" not in command:
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    # Extract details
    script_name = extract_script_name(command)
    exit_code, success = detect_exit_code(str(tool_result))

    # Log the entry
    log_data = load_log()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "script_name": script_name,
        "full_command": command[:500],  # Truncate very long commands
        "exit_code": exit_code,
        "success": success,
    }
    log_data["entries"].append(entry)
    save_log(log_data)

    print(json.dumps({"decision": "ALLOW"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
