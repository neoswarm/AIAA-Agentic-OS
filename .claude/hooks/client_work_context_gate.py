#!/usr/bin/env python3
"""
Hook 24: Client Work Context Gate (PreToolUse on Bash)

When a Bash command contains --client or --company arguments, OR references
a path inside clients/:
- Check .tmp/hooks/context_state.json for whether ANY client context files were loaded
- If no client context loaded: WARN via stderr
- Never blocks, only warns. Exit 0 always.
"""

import json
import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
CONTEXT_STATE_FILE = STATE_DIR / "context_state.json"


def load_context_state():
    try:
        if CONTEXT_STATE_FILE.exists():
            return json.loads(CONTEXT_STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def is_client_work(command):
    """Detect if the command involves client-specific work."""
    # Check for --client or --company arguments
    if re.search(r'--(?:client|company)\s+', command):
        return True

    # Check for paths referencing clients/ directory
    if re.search(r'clients/', command):
        return True

    return False


def extract_client_hint(command):
    """Try to extract client name from command."""
    patterns = [
        r'--client\s+"([^"]+)"',
        r"--client\s+'([^']+)'",
        r'--client\s+(\S+)',
        r'--company\s+"([^"]+)"',
        r"--company\s+'([^']+)'",
        r'--company\s+(\S+)',
        r'clients/([^/\s]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            return match.group(1)
    return None


def check_client_context_loaded(context_state):
    """Check if any client context files have been loaded."""
    loaded_files = context_state.get("loaded_files", [])
    loaded_contexts = context_state.get("loaded_contexts", [])

    # Check for client-related file loads
    for f in loaded_files + loaded_contexts:
        if isinstance(f, str) and "clients/" in f:
            return True
        if isinstance(f, dict) and "clients/" in f.get("path", ""):
            return True

    return False


def handle_status():
    print("=== Client Work Context Gate Status ===")
    print(f"Context state file: {CONTEXT_STATE_FILE}")
    print(f"File exists: {CONTEXT_STATE_FILE.exists()}")

    context_state = load_context_state()
    loaded = check_client_context_loaded(context_state)
    print(f"Client context loaded: {loaded}")

    loaded_files = context_state.get("loaded_files", [])
    if loaded_files:
        client_files = [f for f in loaded_files if isinstance(f, str) and "clients/" in f]
        if client_files:
            print(f"Client files loaded: {len(client_files)}")
            for f in client_files[:10]:
                print(f"  - {f}")
        else:
            print("No client-specific files in loaded context.")
    else:
        print("No files tracked in context state.")


def handle_reset():
    print("Client work context gate has no independent state to reset.")
    print("It reads from context_state.json managed by context_loader_enforcer.")


def main():
    if "--status" in sys.argv:
        handle_status()
        return
    if "--reset" in sys.argv:
        handle_reset()
        return

    # PreToolUse mode: read from stdin, exit codes only, messages to stderr
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

    if not is_client_work(command):
        sys.exit(0)

    # This is client-specific work - check if context is loaded
    context_state = load_context_state()
    client_loaded = check_client_context_loaded(context_state)

    if not client_loaded:
        client_hint = extract_client_hint(command)
        if client_hint:
            sys.stderr.write(
                f"[CLIENT CONTEXT GATE] Client-specific work detected for '{client_hint}' "
                f"but no client profile loaded. Consider loading "
                f"clients/{client_hint}/profile.md first.\n"
            )
        else:
            sys.stderr.write(
                "[CLIENT CONTEXT GATE] Client-specific work detected but no client "
                "profile loaded. Load clients/{{name}}/profile.md first.\n"
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
