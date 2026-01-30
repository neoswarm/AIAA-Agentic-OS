#!/usr/bin/env python3
"""
Hook 16: Self-Anneal Reminder
Type: PostToolUse on Bash tool
Tier: Advisory (always allows)

After execution scripts that fail (non-zero exit code, Traceback, Error, etc.),
writes the self-annealing protocol to stderr as a reminder and tracks failed
scripts in .tmp/hooks/anneal_queue.json.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {...}, "tool_result": "..."}
  - Prints JSON to stdout: {"decision": "ALLOW"}
  - Reminders written to stderr
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR = Path("/Users/lucasnolan/Agentic OS/.tmp/hooks")
ANNEAL_FILE = STATE_DIR / "anneal_queue.json"

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
    "PermissionError:",
    "ConnectionError:",
    "TimeoutError:",
]


def load_anneal_queue():
    """Load the anneal queue."""
    try:
        if ANNEAL_FILE.exists():
            with open(ANNEAL_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {"queue": []}


def save_anneal_queue(data):
    """Save the anneal queue."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(ANNEAL_FILE, "w") as f:
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

    # Check for error text indicators
    for indicator in ERROR_INDICATORS:
        if indicator in result_str:
            return True

    return False


def extract_error_message(tool_result: str) -> str:
    """Extract a concise error message from tool_result."""
    result_str = str(tool_result)
    lines = result_str.splitlines()

    # Look for the last error-like line
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
    """Show scripts in anneal queue."""
    print("Self-Anneal Reminder - Status")
    print("=" * 50)
    data = load_anneal_queue()
    queue = data.get("queue", [])

    if not queue:
        print("\nAnneal queue is empty. No scripts need attention.")
        sys.exit(0)

    print(f"\nScripts needing annealing ({len(queue)}):")
    for entry in queue:
        script = entry.get("script_name", "?")
        error = entry.get("error_message", "?")
        ts = entry.get("timestamp", "?")[:19]
        print(f"\n  Script: {script}")
        print(f"  Error: {error}")
        print(f"  When: {ts}")

    sys.exit(0)


def check_reset():
    """Clear anneal queue."""
    print("Self-Anneal Reminder - Reset")
    if ANNEAL_FILE.exists():
        os.remove(ANNEAL_FILE)
        print("Anneal queue cleared.")
    else:
        print("No anneal queue to clear.")
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

    # Check for errors
    if not has_error(str(tool_result)):
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    script_name = extract_script_name(command)
    error_message = extract_error_message(str(tool_result))

    # Add to anneal queue
    anneal_data = load_anneal_queue()
    entry = {
        "script_name": script_name,
        "command": command[:300],
        "error_message": error_message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    anneal_data["queue"].append(entry)
    save_anneal_queue(anneal_data)

    # Write self-annealing reminder
    reminder = (
        f"\n[SELF-ANNEAL] Script execution failed. Self-annealing protocol:\n"
        f"1. Fix the script: execution/{script_name}\n"
        f"2. Update the directive: directives/<related>.md\n"
        f"3. Add edge case to relevant skill bible\n"
        f'4. Commit: git add directives/ execution/ skills/ && git commit -m "Self-anneal: <lesson>"\n\n'
    )
    sys.stderr.write(reminder)

    print(json.dumps({"decision": "ALLOW"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
