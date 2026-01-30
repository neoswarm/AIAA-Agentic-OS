#!/usr/bin/env python3
"""
Hook 101: client_deliverable_tracker.py (PostToolUse on Write)
Purpose: Track all deliverables created for each client.
Logic: When writing files to client directories or .tmp/*client*/, extract client
name and deliverable type. Track in state: client, deliverable, timestamp, file path.

Protocol:
  - PostToolUse: prints JSON to stdout {"decision": "ALLOW"}
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "client_deliverables.json"

# Deliverable type detection patterns
DELIVERABLE_TYPES = {
    r'vsl[_\s]script': "VSL Script",
    r'vsl[_\s]funnel': "VSL Funnel",
    r'sales[_\s]page': "Sales Page",
    r'email[_\s]sequence': "Email Sequence",
    r'cold[_\s]email': "Cold Email Campaign",
    r'blog[_\s]post': "Blog Post",
    r'linkedin[_\s]post': "LinkedIn Post",
    r'newsletter': "Newsletter",
    r'research': "Research Report",
    r'proposal': "Proposal",
    r'funnel[_\s]copy': "Funnel Copy",
    r'landing[_\s]page': "Landing Page",
    r'ad[_\s]copy': "Ad Copy",
    r'social[_\s]media': "Social Media Content",
    r'case[_\s]study': "Case Study",
    r'white[_\s]paper': "White Paper",
    r'meeting[_\s]prep': "Meeting Prep",
    r'sop': "SOP Document",
    r'strategy': "Strategy Document",
    r'audit': "Audit Report",
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "clients": {},
        "total_deliverables": 0,
        "recent_deliverables": []
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_client_name(file_path):
    """Extract client name from file path."""
    # Pattern: clients/{client_name}/...
    match = re.search(r'clients/([a-zA-Z0-9_-]+)/', file_path)
    if match:
        return match.group(1)

    # Pattern: .tmp/*{client_name}*/...
    match = re.search(r'\.tmp/[^/]*?([a-zA-Z0-9_]+(?:_corp|_co|_inc|_llc|_ltd))[^/]*/', file_path, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern: .tmp/vsl_funnel_{client}/ or .tmp/cold_email_{client}/
    match = re.search(r'\.tmp/(?:vsl_funnel|cold_email|research|proposal|deliverable)[_-]([a-zA-Z0-9_-]+)/', file_path)
    if match:
        return match.group(1)

    return None


def detect_deliverable_type(file_path):
    """Detect the type of deliverable from the file path or name."""
    path_lower = file_path.lower()
    for pattern, dtype in DELIVERABLE_TYPES.items():
        if re.search(pattern, path_lower):
            return dtype

    # Fallback: use file extension
    ext = Path(file_path).suffix.lower()
    ext_map = {
        ".md": "Markdown Document",
        ".html": "HTML Document",
        ".json": "Data File",
        ".csv": "Spreadsheet",
        ".txt": "Text Document",
    }
    return ext_map.get(ext, "Unknown Deliverable")


def show_status():
    state = load_state()
    clients = state.get("clients", {})

    print("=== Client Deliverable Tracker ===")
    print(f"Total deliverables tracked: {state.get('total_deliverables', 0)}")
    print(f"Active clients: {len(clients)}")

    if clients:
        print("\nDeliverables by client:")
        for client_name, client_data in sorted(clients.items()):
            deliverables = client_data.get("deliverables", [])
            print(f"\n  {client_name} ({len(deliverables)} deliverables):")
            for d in deliverables[-5:]:
                dtype = d.get("type", "?")
                ts = d.get("timestamp", "?")[:19]
                fname = Path(d.get("file_path", "?")).name
                print(f"    [{ts}] {dtype}: {fname}")

    recent = state.get("recent_deliverables", [])
    if recent:
        print(f"\nRecent deliverables (last {min(10, len(recent))}):")
        for r in recent[-10:]:
            print(f"  [{r.get('timestamp', '?')[:19]}] {r.get('client', '?')}: {r.get('type', '?')} -> {Path(r.get('file_path', '?')).name}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Client deliverable tracker state reset.")
    sys.exit(0)


def main():
    if "--status" in sys.argv:
        show_status()
    if "--reset" in sys.argv:
        reset_state()

    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Write", "write"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    if not file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Only track writes to client dirs or .tmp
    if "clients/" not in file_path and ".tmp/" not in file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    client_name = extract_client_name(file_path)
    if not client_name:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()
    dtype = detect_deliverable_type(file_path)

    # Track by client
    clients = state.get("clients", {})
    if client_name not in clients:
        clients[client_name] = {"deliverables": [], "first_seen": now}

    deliverable_entry = {
        "type": dtype,
        "file_path": file_path,
        "timestamp": now,
        "filename": Path(file_path).name
    }

    clients[client_name]["deliverables"].append(deliverable_entry)
    # Keep last 100 per client
    clients[client_name]["deliverables"] = clients[client_name]["deliverables"][-100:]
    state["clients"] = clients

    # Track overall
    state["total_deliverables"] = state.get("total_deliverables", 0) + 1

    recent_entry = {
        "client": client_name,
        "type": dtype,
        "file_path": file_path,
        "timestamp": now
    }
    state["recent_deliverables"] = state.get("recent_deliverables", [])
    state["recent_deliverables"].append(recent_entry)
    state["recent_deliverables"] = state["recent_deliverables"][-200:]

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
