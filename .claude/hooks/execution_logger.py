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

ERROR_INDICATORS = ["Traceback", "Error:", "Exception:", "FAILED", "error:", "fatal:"]


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


def _extract_exit_code(text: str):
    """Try to extract an exit code from output text."""
    exit_match = re.search(r'exit\s+code[:\s]+(-?\d+)', text, re.IGNORECASE)
    if not exit_match:
        return None
    try:
        return int(exit_match.group(1))
    except ValueError:
        return None


def _has_error_signal(text: str) -> bool:
    """Check if output includes known error markers."""
    for indicator in ERROR_INDICATORS:
        if indicator in text:
            return True
    return False


def parse_terminal_status(tool_result):
    """Parse tool_result into structured terminal status metadata."""
    if isinstance(tool_result, dict):
        exit_code = tool_result.get("exit_code")
        stdout = str(tool_result.get("stdout", "") or "")
        stderr = str(tool_result.get("stderr", "") or "")
        combined = f"{stdout}\n{stderr}".strip()
    else:
        exit_code = None
        combined = str(tool_result or "")

    if isinstance(exit_code, int):
        status = "success" if exit_code == 0 else "error"
    elif not combined:
        status = "unknown"
    else:
        inferred_exit = _extract_exit_code(combined)
        if inferred_exit is not None:
            exit_code = inferred_exit
            status = "success" if inferred_exit == 0 else "error"
        else:
            status = "error" if _has_error_signal(combined) else "success"

    return {
        "status": status,
        "exit_code": exit_code,
        "error_detected": status == "error",
    }


def build_tool_event(tool_name: str, command: str, script_name: str):
    """Build structured tool event metadata for the execution command."""
    return {
        "name": tool_name,
        "category": "workflow_execution",
        "script_name": script_name,
        "command": command.strip()[:500],
    }


def build_log_entry(command: str, tool_result, tool_name: str = "Bash", timestamp: str = None):
    """Build a structured execution log entry."""
    script_name = extract_script_name(command)
    terminal_status = parse_terminal_status(tool_result)
    exit_code = terminal_status.get("exit_code")
    success = terminal_status.get("status") != "error"

    return {
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "script_name": script_name,
        "full_command": command[:500],
        "exit_code": exit_code if exit_code is not None else "unknown",
        "success": success,
        "event_type": "tool_event",
        "tool_event": build_tool_event(tool_name, command, script_name),
        "terminal_status": terminal_status,
    }


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

    # Log the structured entry
    log_data = load_log()
    entry = build_log_entry(command, tool_result, tool_name=tool_name)
    log_data["entries"].append(entry)
    save_log(log_data)

    print(json.dumps({"decision": "ALLOW"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
