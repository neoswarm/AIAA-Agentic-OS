#!/usr/bin/env python3
"""
Hook 124: Modal Endpoint Limit Tracker
Type: PreToolUse on Bash tool
Tier: Blocking (exit 2 when at endpoint limit)

When a command contains 'modal deploy', runs 'modal app list' to count
deployed apps. Each deployed app uses ~2 endpoints (webhook + health).
Free tier limit is 8 endpoints. Also reads the target .py file to count
@modal.fastapi_endpoint decorators for the new deploy.

Blocks deployment if current_endpoints + new_endpoints > 8.
Warns if current_endpoints >= 6.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {"command": "..."}}
  - Exit 0 = allow, Exit 2 = block
  - Warnings/info written to stderr
  - NEVER prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show current endpoint usage
  --reset   Clear tracking history
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR = Path("/Users/lucasnolan/Agentic OS/.tmp/hooks")
STATE_FILE = STATE_DIR / "modal_endpoint_tracker.json"
MAX_ENTRIES = 50
FREE_TIER_LIMIT = 8
ENDPOINTS_PER_APP = 2


def load_state():
    """Load endpoint tracking data."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": []}


def save_state(data):
    """Save endpoint tracking data."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    entries = data.get("checks", [])
    if len(entries) > MAX_ENTRIES:
        data["checks"] = entries[-MAX_ENTRIES:]
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def extract_py_file(command):
    """Extract the .py file path from a modal deploy command."""
    match = re.search(r'modal\s+deploy\s+(\S+\.py)', command)
    if match:
        return match.group(1)
    return None


def get_deployed_apps():
    """Run 'modal app list' and count apps with 'deployed' status.
    Returns (deployed_app_names, total_count) or (None, 0) on failure.
    """
    try:
        result = subprocess.run(
            ["modal", "app", "list"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return None, 0

        deployed_apps = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            # Skip empty, header (┃), and border lines
            if not line:
                continue
            if any(c in line for c in "┏┡┗┣┛┓┐└┘━─╇╈"):
                continue
            # Header rows use ┃ as separator
            if "┃" in line:
                continue
            # Data rows use │ as separator; check for "deployed" state
            if "│" in line and "deployed" in line.lower():
                parts = [p.strip() for p in line.split("│") if p.strip()]
                if parts:
                    deployed_apps.append(parts[0])

        return deployed_apps, len(deployed_apps)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None, 0


def count_new_endpoints(content):
    """Count @modal.fastapi_endpoint decorators in file content."""
    return len(re.findall(r'@\w+\.fastapi_endpoint', content))


def check_status():
    """Print current endpoint usage."""
    print("Modal Endpoint Limit Tracker - Status")
    print("=" * 50)
    print()
    print(f"  Free tier limit: {FREE_TIER_LIMIT} endpoints")
    print(f"  Estimated endpoints per app: ~{ENDPOINTS_PER_APP}")
    print()

    deployed_apps, count = get_deployed_apps()
    if deployed_apps is not None:
        current_endpoints = count * ENDPOINTS_PER_APP
        print(f"  Deployed apps: {count}")
        print(f"  Estimated endpoint usage: ~{current_endpoints}/{FREE_TIER_LIMIT}")
        if deployed_apps:
            print(f"  Apps:")
            for app in deployed_apps:
                print(f"    - {app}")
        remaining = FREE_TIER_LIMIT - current_endpoints
        print(f"  Remaining capacity: ~{max(0, remaining)} endpoints")
    else:
        print("  Could not run 'modal app list' - Modal CLI may not be available.")

    # Show recent checks
    data = load_state()
    checks = data.get("checks", [])
    if checks:
        print(f"\n  Recent checks ({len(checks)} total):")
        for entry in checks[-10:]:
            ts = entry.get("timestamp", "?")[:19]
            current = entry.get("current_endpoints", "?")
            new = entry.get("new_endpoints", "?")
            result = entry.get("result", "?")
            print(f"    {ts} - {current} current + {new} new = {result}")
    else:
        print("\n  No checks recorded yet.")

    sys.exit(0)


def check_reset():
    """Clear tracking history."""
    print("Modal Endpoint Limit Tracker - Reset")
    if STATE_FILE.exists():
        os.remove(STATE_FILE)
        print("Tracking history cleared.")
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

    # Get current deployed apps
    deployed_apps, app_count = get_deployed_apps()
    if deployed_apps is None:
        # Cannot check - warn but allow
        sys.stderr.write(
            "\n[MODAL ENDPOINT CHECK] Could not run 'modal app list'.\n"
            "  Ensure Modal CLI is installed and authenticated.\n"
            "  Cannot verify endpoint limit - proceeding with deploy.\n\n"
        )
        sys.exit(0)

    current_endpoints = app_count * ENDPOINTS_PER_APP

    # Count new endpoints from the target file
    new_endpoints = 0
    py_file = extract_py_file(command)
    if py_file:
        base_dir = Path("/Users/lucasnolan/Agentic OS")
        file_path = base_dir / py_file
        if not file_path.exists():
            file_path = Path(py_file)
        if file_path.exists():
            try:
                content = file_path.read_text()
                new_endpoints = count_new_endpoints(content)
            except (OSError, IOError):
                pass
    # Default to 2 if we couldn't read the file
    if new_endpoints == 0:
        new_endpoints = ENDPOINTS_PER_APP

    total = current_endpoints + new_endpoints

    # Track the check
    state = load_state()
    result_str = f"{total}/{FREE_TIER_LIMIT}"
    if total > FREE_TIER_LIMIT:
        result_str += " BLOCKED"
    elif current_endpoints >= 6:
        result_str += " WARNING"
    else:
        result_str += " OK"

    state["checks"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "deployed_apps": deployed_apps,
        "app_count": app_count,
        "current_endpoints": current_endpoints,
        "new_endpoints": new_endpoints,
        "total": total,
        "result": result_str,
    })
    save_state(state)

    # BLOCK if over limit
    if total > FREE_TIER_LIMIT:
        sys.stderr.write(
            f"\n[MODAL ENDPOINT LIMIT] BLOCKED: Would exceed free tier limit!\n"
            f"  Current endpoints: ~{current_endpoints} ({app_count} apps x {ENDPOINTS_PER_APP})\n"
            f"  New endpoints:     +{new_endpoints}\n"
            f"  Total:             {total}/{FREE_TIER_LIMIT}\n"
            f"\n"
            f"  Deployed apps to consider stopping:\n"
        )
        for app in deployed_apps:
            sys.stderr.write(f"    - {app}  (stop: modal app stop {app})\n")
        sys.stderr.write(
            f"\n  Free up endpoints before deploying.\n\n"
        )
        sys.exit(2)

    # WARN if approaching limit
    if current_endpoints >= 6:
        sys.stderr.write(
            f"\n[MODAL ENDPOINT CHECK] WARNING: Approaching endpoint limit.\n"
            f"  Current: ~{current_endpoints}/{FREE_TIER_LIMIT} endpoints ({app_count} apps)\n"
            f"  After deploy: ~{total}/{FREE_TIER_LIMIT}\n"
            f"  Consider consolidating apps if you need more capacity.\n\n"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
