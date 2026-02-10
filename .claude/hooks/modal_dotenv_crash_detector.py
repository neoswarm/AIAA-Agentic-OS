#!/usr/bin/env python3
"""
Hook 122: Modal Dotenv Crash Detector
Type: PreToolUse on Bash tool
Tier: Advisory (never blocks)

When a command contains 'modal deploy', extracts the target .py file path
and scans it for the dangerous import pattern where 'import requests' and
'from dotenv import load_dotenv' are combined in the same try/except block
with sys.exit in the except clause. This pattern causes Modal containers
to crash on cold start.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {"command": "..."}}
  - Exit 0 = allow (always, advisory only)
  - Warnings/info written to stderr
  - NEVER prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show recent scan results
  --reset   Clear scan history
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR = Path("/Users/lucasnolan/Agentic OS/.tmp/hooks")
STATE_FILE = STATE_DIR / "modal_dotenv_checks.json"
MAX_ENTRIES = 50

# Regex to detect the dangerous pattern: requests and dotenv in same try block
# with sys.exit in the except clause
BAD_PATTERN = re.compile(
    r'try\s*:'
    r'(?:(?!except).)*?'      # everything inside try (non-greedy, not crossing except)
    r'import\s+requests'
    r'(?:(?!except).)*?'      # more content in try
    r'from\s+dotenv\s+import'
    r'(?:(?!except).)*?'      # rest of try block
    r'except.*?'
    r'sys\.exit',
    re.DOTALL
)

# Also check the reverse order (dotenv first, then requests)
BAD_PATTERN_REVERSE = re.compile(
    r'try\s*:'
    r'(?:(?!except).)*?'
    r'from\s+dotenv\s+import'
    r'(?:(?!except).)*?'
    r'import\s+requests'
    r'(?:(?!except).)*?'
    r'except.*?'
    r'sys\.exit',
    re.DOTALL
)


def load_state():
    """Load scan history data."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {"scans": []}


def save_state(data):
    """Save scan history data."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    entries = data.get("scans", [])
    if len(entries) > MAX_ENTRIES:
        data["scans"] = entries[-MAX_ENTRIES:]
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def extract_py_file(command):
    """Extract the .py file path from a modal deploy command."""
    # Match: modal deploy execution/foo.py or modal deploy ./execution/foo.py
    match = re.search(r'modal\s+deploy\s+(\S+\.py)', command)
    if match:
        return match.group(1)
    return None


def has_bad_pattern(content):
    """Check if file content has the dangerous dotenv+requests import pattern."""
    if BAD_PATTERN.search(content):
        return True
    if BAD_PATTERN_REVERSE.search(content):
        return True
    return False


def check_status():
    """Print recent scan results."""
    print("Modal Dotenv Crash Detector - Status")
    print("=" * 50)
    print()
    print("Detects dangerous import pattern in Modal deploy targets:")
    print("  try:")
    print("      import requests")
    print("      from dotenv import load_dotenv")
    print("  except:")
    print("      sys.exit(1)  # <-- crashes Modal container")
    print()

    data = load_state()
    scans = data.get("scans", [])
    if scans:
        print(f"  Recent scans ({len(scans)} total):")
        for entry in scans[-10:]:
            ts = entry.get("timestamp", "?")[:19]
            f = entry.get("file", "?")
            result = "BAD PATTERN" if entry.get("has_bad_pattern") else "clean"
            print(f"    {ts} - {f} [{result}]")
    else:
        print("  No scans recorded yet.")

    sys.exit(0)


def check_reset():
    """Clear scan history."""
    print("Modal Dotenv Crash Detector - Reset")
    if STATE_FILE.exists():
        os.remove(STATE_FILE)
        print("Scan history cleared.")
    else:
        print("No state file to clear.")
    sys.exit(0)


def main():
    # Handle CLI flags first
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
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not command:
        sys.exit(0)

    # Only trigger on modal deploy commands
    if "modal deploy" not in command:
        sys.exit(0)

    # Extract the target .py file
    py_file = extract_py_file(command)
    if not py_file:
        sys.exit(0)

    # Resolve the file path relative to project root
    base_dir = Path("/Users/lucasnolan/Agentic OS")
    file_path = base_dir / py_file
    if not file_path.exists():
        # Try as absolute path
        file_path = Path(py_file)
        if not file_path.exists():
            sys.exit(0)

    # Read and scan the file
    try:
        content = file_path.read_text()
    except (OSError, IOError):
        sys.exit(0)

    found_bad = has_bad_pattern(content)

    # Track the scan
    state = load_state()
    state["scans"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file": str(py_file),
        "has_bad_pattern": found_bad,
    })
    save_state(state)

    # Warn if bad pattern found
    if found_bad:
        sys.stderr.write(
            f"\n[MODAL DOTENV WARNING] Script has the crash-causing import pattern!\n"
            f"  File: {py_file}\n"
            f"  Fix: Separate requests and dotenv into independent try/except blocks\n"
            f"  See: directives/deploy_to_modal.md for the correct pattern\n\n"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
