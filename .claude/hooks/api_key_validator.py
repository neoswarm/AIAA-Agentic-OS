#!/usr/bin/env python3
"""
api_key_validator.py - PreToolUse hook on Bash tool

When an execution script is about to run, checks that required API keys are
present in the environment. Reports missing keys as informational messages
but never blocks execution.

Checked keys:
  - OPENROUTER_API_KEY
  - PERPLEXITY_API_KEY
  - SLACK_WEBHOOK_URL

Also attempts to load from .env file via dotenv if available.

Hook Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow always)
  - Messages to user via sys.stderr.write()
  - NEVER prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show which keys are set vs missing
  --reset   N/A (stateless hook)
"""

import json
import sys
import os
import re
from pathlib import Path

BASE_DIR = Path(os.path.expanduser("/Users/lucasnolan/Agentic OS"))

REQUIRED_KEYS = [
    "OPENROUTER_API_KEY",
    "PERPLEXITY_API_KEY",
    "SLACK_WEBHOOK_URL",
]


def try_load_dotenv():
    """Attempt to load .env file using dotenv if available."""
    try:
        from dotenv import load_dotenv
        env_path = BASE_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            return True
    except ImportError:
        pass
    return False


def check_keys():
    """Check which keys are set and which are missing.
    Returns (set_keys, missing_keys).
    """
    set_keys = []
    missing_keys = []
    for key in REQUIRED_KEYS:
        value = os.environ.get(key)
        if value and len(value.strip()) > 0:
            set_keys.append(key)
        else:
            missing_keys.append(key)
    return set_keys, missing_keys


def is_execution_command(command):
    """Check if the command runs an execution script."""
    return bool(re.search(r'python3?\s+(?:\S*/)?execution/\S+\.py', command))


def handle_status():
    """Print API key status and exit."""
    try_load_dotenv()
    set_keys, missing_keys = check_keys()

    print("API Key Validator Status")
    print(f"  Keys set ({len(set_keys)}/{len(REQUIRED_KEYS)}):")
    for key in set_keys:
        # Show first 4 and last 4 chars for verification
        val = os.environ.get(key, "")
        if len(val) > 12:
            masked = f"{val[:4]}...{val[-4:]}"
        elif len(val) > 0:
            masked = f"{val[:2]}***"
        else:
            masked = "(empty)"
        print(f"    + {key} = {masked}")

    if missing_keys:
        print(f"  Keys missing ({len(missing_keys)}):")
        for key in missing_keys:
            print(f"    - {key}")
    else:
        print("  All required keys are set!")

    # Check .env file
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        print(f"  .env file: found at {env_path}")
    else:
        print(f"  .env file: not found at {env_path}")

    sys.exit(0)


def handle_reset():
    """Stateless hook, nothing to reset."""
    print("API Key Validator: Stateless hook, nothing to reset.")
    sys.exit(0)


def main():
    # CLI flags
    if "--status" in sys.argv:
        handle_status()
    if "--reset" in sys.argv:
        handle_reset()

    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, IOError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only act on Bash tool
    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")

    # Only check execution script commands
    if not is_execution_command(command):
        sys.exit(0)

    # Try loading .env
    try_load_dotenv()

    # Check keys
    set_keys, missing_keys = check_keys()

    if missing_keys:
        sys.stderr.write(
            f"[API Key Validator] INFO: Missing environment variables:\n"
        )
        for key in missing_keys:
            sys.stderr.write(f"    - {key}\n")
        sys.stderr.write(
            f"  The script may fail if it requires these keys.\n"
            f"  Set them via: export {missing_keys[0]}=\"your-key\"\n"
            f"  Or add them to .env file in the project root.\n"
        )

    # Never block - info only
    sys.exit(0)


if __name__ == "__main__":
    main()
