#!/usr/bin/env python3
"""
context_loader_enforcer.py - DUAL MODE hook (PostToolUse/Read + PreToolUse/Bash)

Enforces the AIAA context-loading pattern: agency context (context/*.md) and
client context (clients/**/*.md) should be loaded before running content
generation scripts.

Dual Mode Detection:
  - If "tool_result" key exists in stdin JSON -> PostToolUse mode
  - If "tool_result" key does NOT exist -> PreToolUse mode

PostToolUse/Read mode:
  - Tracks reads of context/*.md files (agency context)
  - Tracks reads of clients/**/*.md files (client context)
  - Always returns {"decision": "ALLOW"}

PreToolUse/Bash mode:
  - When command contains python3 execution/generate_* or python3 execution/write_*:
    - Warns if agency.md hasn't been loaded
  - NEVER blocks (warning only)

State: .tmp/hooks/context_state.json

CLI Flags:
  --status  Show loaded context files
  --reset   Clear context state
"""

import json
import sys
import os
import re
from pathlib import Path

BASE_DIR = Path(os.path.expanduser("/Users/lucasnolan/Agentic OS"))
STATE_FILE = BASE_DIR / ".tmp" / "hooks" / "context_state.json"


def load_state():
    """Load context state."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"agency_context_loaded": [], "client_context_loaded": {}}


def save_state(state):
    """Save context state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def extract_client_name(file_path):
    """Extract client name from a path like clients/acme_corp/profile.md."""
    match = re.search(r'clients/([^/]+)/', file_path)
    if match:
        return match.group(1)
    return None


def is_content_generation_command(command):
    """Check if the command runs a content generation script."""
    patterns = [
        r'python3?\s+(?:\S*/)?execution/generate_',
        r'python3?\s+(?:\S*/)?execution/write_',
    ]
    for pattern in patterns:
        if re.search(pattern, command):
            return True
    return False


def handle_status():
    """Print context loading status and exit."""
    state = load_state()
    print("Context Loader Enforcer Status")

    agency = state.get("agency_context_loaded", [])
    print(f"  Agency context loaded ({len(agency)}):")
    for f in agency:
        print(f"    - {f}")

    clients = state.get("client_context_loaded", {})
    if clients:
        print(f"  Client context loaded ({len(clients)} clients):")
        for client, files in clients.items():
            print(f"    {client}:")
            for f in files:
                print(f"      - {f}")
    else:
        print("  Client context: none loaded")

    # Check if minimum context is loaded
    if "agency.md" in agency:
        print("  Agency context status: OK (agency.md loaded)")
    else:
        print("  Agency context status: MISSING (agency.md not loaded)")

    sys.exit(0)


def handle_reset():
    """Clear context state and exit."""
    save_state({"agency_context_loaded": [], "client_context_loaded": {}})
    print("Context Loader Enforcer: Context state cleared.")
    sys.exit(0)


def handle_post_tool_use(data):
    """PostToolUse mode: track reads of context and client files."""
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    changed = False

    # Check for agency context files (context/*.md)
    if "context/" in file_path and file_path.endswith(".md"):
        filename = Path(file_path).name
        if filename not in state["agency_context_loaded"]:
            state["agency_context_loaded"].append(filename)
            changed = True

    # Check for client context files (clients/**/*.md)
    client_name = extract_client_name(file_path)
    if client_name and file_path.endswith(".md"):
        filename = Path(file_path).name
        if client_name not in state["client_context_loaded"]:
            state["client_context_loaded"][client_name] = []
        if filename not in state["client_context_loaded"][client_name]:
            state["client_context_loaded"][client_name].append(filename)
            changed = True

    if changed:
        save_state(state)

    print(json.dumps({"decision": "ALLOW"}))


def handle_pre_tool_use(data):
    """PreToolUse mode: warn if agency context not loaded before content generation."""
    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only check content generation commands
    if not is_content_generation_command(command):
        sys.exit(0)

    state = load_state()
    agency_loaded = state.get("agency_context_loaded", [])

    if "agency.md" not in agency_loaded:
        sys.stderr.write(
            f"[Context Loader] WARNING: Agency context not loaded.\n"
            f"  Consider reading context/agency.md first.\n"
            f"  The AIAA system recommends loading agency context before generating content.\n"
            f"  Context files to consider:\n"
            f"    - context/agency.md (agency identity)\n"
            f"    - context/brand_voice.md (tone & style)\n"
            f"    - context/owner.md (owner profile)\n"
            f"    - context/services.md (service offerings)\n"
        )

    # Always allow - this is a warning-only hook
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

    # Detect mode: PostToolUse has "tool_result", PreToolUse does not
    if "tool_result" in data:
        handle_post_tool_use(data)
    else:
        handle_pre_tool_use(data)


if __name__ == "__main__":
    main()
