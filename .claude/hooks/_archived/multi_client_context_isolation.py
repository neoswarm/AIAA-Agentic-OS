#!/usr/bin/env python3
"""
Hook 104: multi_client_context_isolation.py (PreToolUse on Read)
Purpose: Prevent loading multiple client contexts simultaneously.
Logic: Track which client context is currently loaded (clients/*). If trying to
read a different client's files while one is active, warn about potential
cross-contamination. Require explicit context switch.

Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages to user via sys.stderr.write()
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "client_context_isolation.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "active_client": None,
        "active_since": None,
        "files_loaded": [],
        "context_switches": [],
        "warnings_issued": 0,
        "total_checks": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_client_name(file_path):
    """Extract client name from file path."""
    match = re.search(r'clients/([a-zA-Z0-9_-]+)/', file_path)
    if match:
        return match.group(1)
    return None


def is_context_switch_file(file_path):
    """Check if the file being read is a client context file."""
    client_context_patterns = [
        r'clients/[^/]+/profile\.md',
        r'clients/[^/]+/rules\.md',
        r'clients/[^/]+/preferences\.md',
        r'clients/[^/]+/history\.md',
    ]
    for pattern in client_context_patterns:
        if re.search(pattern, file_path):
            return True
    return False


def show_status():
    state = load_state()
    print("=== Multi-Client Context Isolation ===")
    print(f"Total checks: {state.get('total_checks', 0)}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    print(f"Active client: {state.get('active_client', 'None')}")
    print(f"Active since: {state.get('active_since', 'N/A')}")

    files = state.get("files_loaded", [])
    if files:
        print(f"\nFiles loaded for active client ({len(files)}):")
        for f in files[-10:]:
            print(f"  {f.get('file', '?')} ({f.get('timestamp', '?')[:19]})")

    switches = state.get("context_switches", [])
    if switches:
        print(f"\nContext switches (last {min(10, len(switches))}):")
        for s in switches[-10:]:
            print(f"  [{s.get('timestamp', '?')[:19]}] {s.get('from_client', '?')} -> {s.get('to_client', '?')}")

    print("\nTo switch client context, use --reset or read a new client's profile.md")
    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Client context isolation state reset. No active client.")
    sys.exit(0)


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

    if tool_name not in ("Read", "read"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if "clients/" not in file_path:
        sys.exit(0)

    requested_client = extract_client_name(file_path)
    if not requested_client:
        sys.exit(0)

    state = load_state()
    state["total_checks"] = state.get("total_checks", 0) + 1
    now = datetime.now().isoformat()

    active_client = state.get("active_client")

    if active_client is None:
        # First client context load - set as active
        state["active_client"] = requested_client
        state["active_since"] = now
        state["files_loaded"] = [{"file": file_path, "timestamp": now}]
        save_state(state)
        sys.exit(0)

    if requested_client == active_client:
        # Same client - track the file
        files = state.get("files_loaded", [])
        files.append({"file": file_path, "timestamp": now})
        state["files_loaded"] = files[-50:]
        save_state(state)
        sys.exit(0)

    # Different client detected!
    if is_context_switch_file(file_path):
        # Reading a primary context file (profile.md, etc.) - this is an intentional switch
        switches = state.get("context_switches", [])
        switches.append({
            "timestamp": now,
            "from_client": active_client,
            "to_client": requested_client,
            "trigger_file": file_path
        })
        state["context_switches"] = switches[-50:]

        # Perform the switch
        state["active_client"] = requested_client
        state["active_since"] = now
        state["files_loaded"] = [{"file": file_path, "timestamp": now}]

        save_state(state)
        sys.stderr.write(
            f"[Context Isolation] Context switched: {active_client} -> {requested_client}\n"
            f"  Loaded: {Path(file_path).name}\n"
            f"  Previous client data should not carry over.\n"
        )
        sys.exit(0)

    # Non-primary file for a different client - warn about cross-contamination
    state["warnings_issued"] = state.get("warnings_issued", 0) + 1
    save_state(state)

    sys.stderr.write(
        f"[Context Isolation] WARNING: Cross-client access detected!\n"
        f"  Active client: {active_client}\n"
        f"  Attempting to read: {requested_client}'s {Path(file_path).name}\n"
        f"  Risk: Client data cross-contamination.\n"
        f"  To switch context: read clients/{requested_client}/profile.md first.\n"
        f"  To reset: python3 .claude/hooks/multi_client_context_isolation.py --reset\n"
    )
    # Warn but don't block - exit 0 to allow
    sys.exit(0)


if __name__ == "__main__":
    main()
