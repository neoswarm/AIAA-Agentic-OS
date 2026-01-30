#!/usr/bin/env python3
"""
Hook 41: Client Data Isolation Guard (PreToolUse on Write)

When writing to clients/ directory:
- Parse the target path to extract client name
- Check if the content references a DIFFERENT client's data
- If cross-client data detected: WARN via stderr
- Exit 0 always (warn only).
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "client_isolation_log.json"
CLIENTS_DIR = PROJECT_ROOT / "clients"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"violations": [], "stats": {"total_checks": 0, "warnings": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_all_client_names():
    """Get all client folder names."""
    if not CLIENTS_DIR.exists():
        return set()
    return {
        d.name for d in CLIENTS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    }


def extract_target_client(file_path):
    """Extract the target client name from the file path."""
    # Path format: .../clients/{client_name}/...
    match = re.search(r'clients/([^/]+)/', file_path)
    if match:
        return match.group(1)
    return None


def check_cross_client_references(content, target_client, all_clients):
    """Check if content references other clients."""
    other_clients = all_clients - {target_client}
    found_references = []

    for client_name in other_clients:
        # Check for various forms of the client name
        patterns = [
            # Direct folder reference
            rf'clients/{re.escape(client_name)}',
            # Client name as a word (case-insensitive)
            rf'\b{re.escape(client_name)}\b',
        ]

        # Also check with underscores replaced by spaces
        readable_name = client_name.replace("_", " ")
        if readable_name != client_name:
            patterns.append(rf'\b{re.escape(readable_name)}\b')

        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                found_references.append(client_name)
                break

    return list(set(found_references))


def handle_status():
    state = load_state()
    print("=== Client Data Isolation Guard Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"Clients directory: {CLIENTS_DIR}")
    print(f"Clients directory exists: {CLIENTS_DIR.exists()}")

    all_clients = get_all_client_names()
    if all_clients:
        print(f"\nKnown clients ({len(all_clients)}):")
        for client in sorted(all_clients):
            print(f"  - {client}")
    else:
        print("\nNo client folders found.")

    stats = state.get("stats", {})
    print(f"\nTotal checks: {stats.get('total_checks', 0)}")
    print(f"Warnings: {stats.get('warnings', 0)}")

    violations = state.get("violations", [])
    if violations:
        print(f"\nRecent violations:")
        for v in violations[-5:]:
            print(f"  Target: {v.get('target_client', '?')}")
            print(f"  Referenced: {', '.join(v.get('referenced_clients', []))}")
            print(f"  File: {v.get('filename', '?')}")
            print(f"  Time: {v.get('timestamp', '?')}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Client data isolation guard state reset.")
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

    if tool_name != "Write":
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    # Only check writes to clients/ directory
    if "clients/" not in file_path:
        sys.exit(0)

    target_client = extract_target_client(file_path)
    if not target_client:
        sys.exit(0)

    all_clients = get_all_client_names()
    if len(all_clients) < 2:
        sys.exit(0)

    state = load_state()
    state["stats"]["total_checks"] = state["stats"].get("total_checks", 0) + 1

    cross_refs = check_cross_client_references(content, target_client, all_clients)

    if cross_refs:
        violation = {
            "target_client": target_client,
            "referenced_clients": cross_refs,
            "filename": Path(file_path).name,
            "filepath": file_path,
            "timestamp": datetime.now().isoformat(),
        }
        state["violations"].append(violation)
        state["violations"] = state["violations"][-50:]
        state["stats"]["warnings"] = state["stats"].get("warnings", 0) + 1
        save_state(state)

        sys.stderr.write(
            f"[CLIENT ISOLATION] Content may reference client(s) "
            f"'{', '.join(cross_refs)}' but is being written to "
            f"'{target_client}' folder. Verify no cross-client data leakage.\n"
        )
    else:
        save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
