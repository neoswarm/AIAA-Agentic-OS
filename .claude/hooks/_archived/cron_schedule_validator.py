#!/usr/bin/env python3
"""
Hook 52: cron_schedule_validator.py (PreToolUse on Bash)
Validates cron expressions in commands for correct format and reasonable frequency.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "cron_validation.json"

RANGES = {
    "minute": (0, 59),
    "hour": (0, 23),
    "day": (1, 31),
    "month": (1, 12),
    "weekday": (0, 7),
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": [], "warnings_issued": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def show_status():
    state = load_state()
    print("=== Cron Schedule Validator ===")
    print(f"Cron expressions validated: {len(state.get('checks', []))}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    checks = state.get("checks", [])
    if checks:
        print("\nRecent validations:")
        for c in checks[-10:]:
            status = "WARN" if c.get("issues") else "OK"
            expr = c.get("expression", "?")
            print(f"  [{status}] '{expr}' - {c.get('message', '')}")
    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("State reset.")
    sys.exit(0)


def validate_field(value, field_name, min_val, max_val):
    """Validate a single cron field."""
    issues = []
    if value == "*":
        return issues
    # Handle step values: */5, 1-5/2
    if "/" in value:
        parts = value.split("/")
        if len(parts) != 2:
            issues.append(f"{field_name}: invalid step syntax '{value}'")
            return issues
        value = parts[0]
        try:
            step = int(parts[1])
            if step < 1:
                issues.append(f"{field_name}: step must be >= 1, got {step}")
        except ValueError:
            issues.append(f"{field_name}: invalid step value '{parts[1]}'")

    if value == "*":
        return issues

    # Handle ranges: 1-5
    if "-" in value:
        range_parts = value.split("-")
        if len(range_parts) != 2:
            issues.append(f"{field_name}: invalid range '{value}'")
            return issues
        try:
            low, high = int(range_parts[0]), int(range_parts[1])
            if low < min_val or low > max_val:
                issues.append(f"{field_name}: {low} out of range {min_val}-{max_val}")
            if high < min_val or high > max_val:
                issues.append(f"{field_name}: {high} out of range {min_val}-{max_val}")
            if low > high:
                issues.append(f"{field_name}: range start ({low}) > end ({high})")
        except ValueError:
            issues.append(f"{field_name}: non-numeric range '{value}'")
        return issues

    # Handle lists: 1,3,5
    if "," in value:
        for item in value.split(","):
            issues.extend(validate_field(item.strip(), field_name, min_val, max_val))
        return issues

    # Plain number
    try:
        num = int(value)
        if num < min_val or num > max_val:
            issues.append(f"{field_name}: {num} out of range {min_val}-{max_val}")
    except ValueError:
        # Could be a name like MON, JAN etc - allow
        pass

    return issues


def extract_cron(command):
    """Try to extract a cron expression from the command."""
    # Look for quoted cron expressions
    patterns = [
        r'cronSchedule["\s:=]+["\']([^"\']+)["\']',
        r'cron["\s:=]+["\']([^"\']+)["\']',
        r'"schedule"\s*:\s*"([^"]+)"',
        r"'schedule'\s*:\s*'([^']+)'",
        r'--cron\s+["\']([^"\']+)["\']',
        r'--schedule\s+["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            return match.group(1)
    return None


def main():
    if "--status" in sys.argv:
        show_status()
    if "--reset" in sys.argv:
        reset_state()

    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Bash", "bash"):
        sys.exit(0)

    command = tool_input.get("command", "")
    if "cron" not in command.lower() and "schedule" not in command.lower():
        sys.exit(0)

    cron_expr = extract_cron(command)
    if not cron_expr:
        sys.exit(0)

    state = load_state()
    now = datetime.now().isoformat()
    issues = []

    fields = cron_expr.strip().split()
    if len(fields) != 5:
        issues.append(f"Expected 5 fields, got {len(fields)}")
    else:
        field_names = ["minute", "hour", "day", "month", "weekday"]
        for i, (fname, fval) in enumerate(zip(field_names, fields)):
            min_val, max_val = RANGES[fname]
            issues.extend(validate_field(fval, fname, min_val, max_val))

        # Check for overly frequent schedules
        if fields[0] == "*" and fields[1] == "*":
            issues.append("Schedule runs every minute (very frequent!) - is this intentional?")
        elif fields[0] == "*":
            issues.append("Schedule runs every minute within the specified hours - consider a less frequent interval")
        elif fields[0].startswith("*/"):
            try:
                interval = int(fields[0].split("/")[1])
                if interval < 5 and fields[1] == "*":
                    issues.append(f"Schedule runs every {interval} minutes - very frequent")
            except ValueError:
                pass

    check_entry = {
        "timestamp": now,
        "expression": cron_expr,
        "issues": issues,
        "message": "; ".join(issues) if issues else "Valid cron expression"
    }
    state["checks"].append(check_entry)
    state["checks"] = state["checks"][-50:]

    if issues:
        state["warnings_issued"] = state.get("warnings_issued", 0) + 1
        sys.stderr.write(f"[cron-validator] Issues with cron '{cron_expr}':\n")
        for issue in issues:
            sys.stderr.write(f"  - {issue}\n")

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
