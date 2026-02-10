#!/usr/bin/env python3
"""
Hook 123: Modal Secret Validator
Type: PreToolUse on Bash tool
Tier: Advisory (never blocks)

When a command contains 'modal deploy', extracts the target .py file path,
reads it, and finds all Secret.from_name("...") references. Then runs
'modal secret list' to check which secrets actually exist. Warns about
any missing secrets, since functions with missing secrets HANG silently
on cold start.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {"command": "..."}}
  - Exit 0 = allow (always, advisory only)
  - Warnings/info written to stderr
  - NEVER prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show recent validation results
  --reset   Clear validation history
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR = Path("/Users/lucasnolan/Agentic OS/.tmp/hooks")
STATE_FILE = STATE_DIR / "modal_secret_checks.json"
MAX_ENTRIES = 50


def load_state():
    """Load validation history data."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": []}


def save_state(data):
    """Save validation history data."""
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


def find_declared_secrets(content):
    """Find all Secret.from_name("...") references in file content."""
    return re.findall(r'Secret\.from_name\(["\']([^"\']+)', content)


def get_existing_secrets():
    """Run 'modal secret list' and parse the output for secret names."""
    try:
        result = subprocess.run(
            ["modal", "secret", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None  # Command failed

        # Parse rich table output from Modal CLI
        # Format uses unicode box-drawing: │ name │ created │ ...
        secrets = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            # Skip empty, header (┃), and border lines (┏┡┗━─┐└┘┤├)
            if not line:
                continue
            if any(c in line for c in "┏┡┗┣┛┓┐└┘━─╇╈"):
                continue
            # Header rows use ┃ as separator
            if "┃" in line:
                continue
            # Data rows use │ as separator
            if "│" in line:
                parts = [p.strip() for p in line.split("│") if p.strip()]
                if parts:
                    name = parts[0]
                    # Skip if it looks like a continuation line (no name)
                    if name and not name.startswith("GMT"):
                        secrets.append(name)

        return secrets
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None  # modal CLI not available or timed out


def check_status():
    """Print recent validation results."""
    print("Modal Secret Validator - Status")
    print("=" * 50)
    print()
    print("Validates that secrets declared in Modal app files exist.")
    print("Missing secrets cause functions to HANG silently on cold start.")
    print()

    data = load_state()
    checks = data.get("checks", [])
    if checks:
        print(f"  Recent checks ({len(checks)} total):")
        for entry in checks[-10:]:
            ts = entry.get("timestamp", "?")[:19]
            f = entry.get("file", "?")
            declared = entry.get("declared_secrets", [])
            missing = entry.get("missing_secrets", [])
            if missing:
                print(f"    {ts} - {f} [MISSING: {', '.join(missing)}]")
            else:
                print(f"    {ts} - {f} [OK: {len(declared)} secrets validated]")
    else:
        print("  No checks recorded yet.")

    sys.exit(0)


def check_reset():
    """Clear validation history."""
    print("Modal Secret Validator - Reset")
    if STATE_FILE.exists():
        os.remove(STATE_FILE)
        print("Validation history cleared.")
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
        file_path = Path(py_file)
        if not file_path.exists():
            sys.exit(0)

    # Read the file and find declared secrets
    try:
        content = file_path.read_text()
    except (OSError, IOError):
        sys.exit(0)

    declared_secrets = find_declared_secrets(content)
    if not declared_secrets:
        # No secrets declared, nothing to validate
        sys.exit(0)

    # Get existing secrets from Modal
    existing_secrets = get_existing_secrets()
    if existing_secrets is None:
        # Could not run modal secret list - warn but don't block
        sys.stderr.write(
            "\n[MODAL SECRET CHECK] Could not run 'modal secret list'.\n"
            "  Ensure Modal CLI is installed and authenticated.\n"
            f"  Declared secrets in {py_file}: {', '.join(declared_secrets)}\n\n"
        )
        sys.exit(0)

    # Find missing secrets
    missing = [s for s in declared_secrets if s not in existing_secrets]

    # Track the check
    state = load_state()
    state["checks"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file": str(py_file),
        "declared_secrets": declared_secrets,
        "existing_secrets": existing_secrets,
        "missing_secrets": missing,
    })
    save_state(state)

    # Warn about missing secrets
    if missing:
        sys.stderr.write(
            f"\n[MODAL SECRET CHECK] Missing secrets for deployment:\n"
        )
        for secret_name in missing:
            sys.stderr.write(
                f"  - {secret_name}  "
                f"(create: modal secret create {secret_name} KEY=<value>)\n"
            )
        sys.stderr.write(
            "  WARNING: Functions with missing secrets HANG silently on cold start\n\n"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
