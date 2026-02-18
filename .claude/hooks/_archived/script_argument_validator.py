#!/usr/bin/env python3
"""
Hook 40: Script Argument Validator (PreToolUse on Bash)

Validate common argument patterns in execution script commands:
- --email should look like an email (contains @)
- --website or --url should start with http
- --price should be a number or dollar amount
- --company should not be empty
- --topic should be at least 3 words
- --length should be a number

Parse the command, check each argument. WARN via stderr if patterns don't match.
Exit 0 always.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "argument_validation_log.json"

# Argument validation rules
ARGUMENT_RULES = {
    "--email": {
        "pattern": r'[^@]+@[^@]+\.[^@]+',
        "description": "should be a valid email address (contains @)",
    },
    "--website": {
        "pattern": r'https?://',
        "description": "should start with http:// or https://",
    },
    "--url": {
        "pattern": r'https?://',
        "description": "should start with http:// or https://",
    },
    "--price": {
        "pattern": r'^[\$]?[\d,]+(?:\.\d{0,2})?$',
        "description": "should be a number or dollar amount (e.g., $99, 149.99)",
    },
    "--company": {
        "min_length": 1,
        "description": "should not be empty",
    },
    "--name": {
        "min_length": 2,
        "description": "should not be empty",
    },
    "--topic": {
        "min_words": 3,
        "description": "should be at least 3 words",
    },
    "--length": {
        "pattern": r'^\d+$',
        "description": "should be a number",
    },
    "--count": {
        "pattern": r'^\d+$',
        "description": "should be a number",
    },
    "--limit": {
        "pattern": r'^\d+$',
        "description": "should be a number",
    },
    "--file": {
        "min_length": 3,
        "description": "should be a file path",
    },
    "--output": {
        "min_length": 3,
        "description": "should be a file path",
    },
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"validations": [], "stats": {"total": 0, "warnings": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_arguments(command):
    """Extract argument name-value pairs from command."""
    args = {}

    # Match --arg "value" or --arg 'value' or --arg value
    patterns = [
        r'(--\w+)\s+"([^"]*)"',
        r"(--\w+)\s+'([^']*)'",
        r'(--\w+)\s+([^\s\-][^\s]*)',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, command):
            arg_name = match.group(1)
            arg_value = match.group(2)
            if arg_name not in args:
                args[arg_name] = arg_value

    return args


def validate_argument(arg_name, arg_value, rule):
    """Validate a single argument against its rule."""
    issues = []

    if "pattern" in rule:
        if not re.match(rule["pattern"], arg_value):
            issues.append(f"{arg_name} value '{arg_value[:50]}' {rule['description']}")

    if "min_length" in rule:
        if len(arg_value.strip()) < rule["min_length"]:
            issues.append(f"{arg_name} {rule['description']}")

    if "min_words" in rule:
        word_count = len(arg_value.split())
        if word_count < rule["min_words"]:
            issues.append(
                f"{arg_name} has {word_count} words but {rule['description']}"
            )

    return issues


def handle_status():
    state = load_state()
    print("=== Script Argument Validator Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"Total checks: {stats.get('total', 0)}")
    print(f"Warnings: {stats.get('warnings', 0)}")

    print(f"\nValidation rules:")
    for arg, rule in sorted(ARGUMENT_RULES.items()):
        print(f"  {arg}: {rule['description']}")

    validations = state.get("validations", [])
    if validations:
        print(f"\nRecent validations:")
        for v in validations[-10:]:
            status = "WARN" if v.get("issues") else "OK"
            print(f"  [{status}] {v.get('command_preview', '?')[:60]}")
            for issue in v.get("issues", []):
                print(f"    - {issue}")
    else:
        print("\nNo arguments validated yet.")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Script argument validator state reset.")
    else:
        print("No state file to reset.")


def main():
    if "--status" in sys.argv:
        handle_status()
        return
    if "--reset" in sys.argv:
        handle_reset()
        return

    # PreToolUse mode
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")

    # Only check execution scripts
    if "execution/" not in command and ".py" not in command:
        sys.exit(0)

    args = extract_arguments(command)
    if not args:
        sys.exit(0)

    all_issues = []
    for arg_name, arg_value in args.items():
        if arg_name in ARGUMENT_RULES:
            issues = validate_argument(arg_name, arg_value, ARGUMENT_RULES[arg_name])
            all_issues.extend(issues)

    state = load_state()
    state["stats"]["total"] = state["stats"].get("total", 0) + 1

    validation_record = {
        "command_preview": command[:100],
        "args_checked": list(args.keys()),
        "issues": all_issues,
        "timestamp": datetime.now().isoformat(),
    }
    state["validations"].append(validation_record)
    state["validations"] = state["validations"][-50:]

    if all_issues:
        state["stats"]["warnings"] = state["stats"].get("warnings", 0) + 1
        save_state(state)
        sys.stderr.write(
            "[ARGUMENT VALIDATOR] " + "; ".join(all_issues) + "\n"
        )
    else:
        save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
