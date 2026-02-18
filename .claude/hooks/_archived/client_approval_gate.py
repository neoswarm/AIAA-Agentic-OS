#!/usr/bin/env python3
"""
Hook 105: client_approval_gate.py (PostToolUse on Write)
Purpose: Flag client deliverables that need approval before delivery.
Logic: When writing final deliverables (not drafts/checkpoints), flag for approval.
Track which deliverables are pending approval. Require explicit approval marker
before delivery scripts run.

Protocol:
  - PostToolUse: prints JSON to stdout {"decision": "ALLOW"}
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "client_approvals.json"

# Final deliverable patterns (these need approval)
FINAL_DELIVERABLE_PATTERNS = [
    r'\.tmp/[^/]+/\d+_[^/]+\.md$',           # Numbered deliverables
    r'\.tmp/[^/]+/final_[^/]+',               # Files prefixed with final_
    r'\.tmp/[^/]+/deliverable[^/]*',           # Deliverable files
    r'clients/[^/]+/deliverables?/',           # Client deliverable dirs
]

# Draft/checkpoint patterns (these do NOT need approval)
DRAFT_PATTERNS = [
    r'\.tmp/hooks/',           # Hook state files
    r'draft[_-]',             # Draft prefixed
    r'_draft\.',              # Draft suffixed
    r'checkpoint',            # Checkpoints
    r'\.tmp/[^/]+/scratch',   # Scratch files
    r'_wip\.',                # Work in progress
    r'_temp\.',               # Temporary files
]

# Delivery scripts that require approval
DELIVERY_SCRIPTS = [
    "create_google_doc.py",
    "send_slack_notification.py",
    "send_email.py",
    "upload_to_drive.py",
    "publish_to_wordpress.py",
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "pending_approval": {},
        "approved": {},
        "delivered": {},
        "total_flagged": 0,
        "total_approved": 0,
        "total_delivered": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_final_deliverable(file_path):
    """Check if file is a final deliverable that needs approval."""
    for pattern in DRAFT_PATTERNS:
        if re.search(pattern, file_path, re.IGNORECASE):
            return False

    for pattern in FINAL_DELIVERABLE_PATTERNS:
        if re.search(pattern, file_path):
            return True

    return False


def extract_client_from_path(file_path):
    """Try to extract client name from path."""
    match = re.search(r'clients/([a-zA-Z0-9_-]+)/', file_path)
    if match:
        return match.group(1)
    match = re.search(r'\.tmp/(?:vsl_funnel|cold_email|research|proposal|deliverable)[_-]([a-zA-Z0-9_-]+)/', file_path)
    if match:
        return match.group(1)
    return "unknown"


def generate_approval_id(file_path):
    """Generate a unique approval ID for a deliverable."""
    import hashlib
    return hashlib.md5(file_path.encode()).hexdigest()[:8]


def show_status():
    state = load_state()
    pending = state.get("pending_approval", {})
    approved = state.get("approved", {})
    delivered = state.get("delivered", {})

    print("=== Client Approval Gate ===")
    print(f"Total flagged: {state.get('total_flagged', 0)}")
    print(f"Total approved: {state.get('total_approved', 0)}")
    print(f"Total delivered: {state.get('total_delivered', 0)}")
    print(f"Pending approval: {len(pending)}")

    if pending:
        print("\nPending Approval:")
        for aid, info in sorted(pending.items()):
            client = info.get("client", "unknown")
            file_name = Path(info.get("file_path", "?")).name
            ts = info.get("flagged_at", "?")[:19]
            print(f"  [{aid}] {client}: {file_name} (flagged: {ts})")

    if approved:
        print(f"\nRecently Approved (last {min(5, len(approved))}):")
        sorted_approved = sorted(approved.items(), key=lambda x: x[1].get("approved_at", ""), reverse=True)
        for aid, info in sorted_approved[:5]:
            file_name = Path(info.get("file_path", "?")).name
            print(f"  [{aid}] {file_name} ({info.get('approved_at', '?')[:19]})")

    if delivered:
        print(f"\nRecently Delivered (last {min(5, len(delivered))}):")
        sorted_delivered = sorted(delivered.items(), key=lambda x: x[1].get("delivered_at", ""), reverse=True)
        for aid, info in sorted_delivered[:5]:
            file_name = Path(info.get("file_path", "?")).name
            print(f"  [{aid}] {file_name} ({info.get('delivered_at', '?')[:19]})")

    print("\nTo approve a deliverable: add 'APPROVED' to the file content")
    print("To approve all: python3 .claude/hooks/client_approval_gate.py --approve-all")
    sys.exit(0)


def approve_all():
    state = load_state()
    pending = state.get("pending_approval", {})
    now = datetime.now().isoformat()
    approved = state.get("approved", {})

    count = 0
    for aid, info in list(pending.items()):
        info["approved_at"] = now
        approved[aid] = info
        count += 1

    state["pending_approval"] = {}
    state["approved"] = approved
    state["total_approved"] = state.get("total_approved", 0) + count
    save_state(state)
    print(f"Approved {count} deliverables.")
    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Client approval gate state reset.")
    sys.exit(0)


def main():
    if "--status" in sys.argv:
        show_status()
    if "--reset" in sys.argv:
        reset_state()
    if "--approve-all" in sys.argv:
        approve_all()

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

    if not is_final_deliverable(file_path):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()

    approval_id = generate_approval_id(file_path)
    client = extract_client_from_path(file_path)

    # Check if content contains APPROVED marker
    content = tool_input.get("content", "")
    if "APPROVED" in content.upper():
        # Mark as approved
        approved = state.get("approved", {})
        approved[approval_id] = {
            "file_path": file_path,
            "client": client,
            "approved_at": now
        }
        state["approved"] = approved
        state["pending_approval"].pop(approval_id, None)
        state["total_approved"] = state.get("total_approved", 0) + 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Flag for approval
    pending = state.get("pending_approval", {})
    if approval_id not in pending:
        state["total_flagged"] = state.get("total_flagged", 0) + 1

    pending[approval_id] = {
        "file_path": file_path,
        "client": client,
        "flagged_at": now,
        "filename": Path(file_path).name
    }
    state["pending_approval"] = pending

    save_state(state)

    output = {
        "decision": "ALLOW",
        "reason": f"[Approval Gate] Deliverable flagged for approval: {Path(file_path).name} (ID: {approval_id}). Run --status to see pending approvals."
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
