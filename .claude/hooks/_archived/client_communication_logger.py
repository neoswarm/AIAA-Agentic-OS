#!/usr/bin/env python3
"""
Hook 110: client_communication_logger.py (PostToolUse on Bash)
Purpose: Log all client-facing communications.
Logic: After Slack notifications, email sends, or Google Doc shares, log the
communication in state: recipient, channel, content summary, timestamp.

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
STATE_FILE = STATE_DIR / "client_communications.json"

# Communication channel detection patterns
COMM_PATTERNS = {
    "send_slack_notification": "slack",
    "send_slack": "slack",
    "slack_webhook": "slack",
    "send_email": "email",
    "send_notification": "notification",
    "create_google_doc": "google_docs",
    "upload_to_drive": "google_drive",
    "share_doc": "google_docs_share",
    "publish_to_wordpress": "wordpress",
    "calendly": "calendly",
    "instantly": "cold_email_platform",
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "communications": [],
        "by_channel": {},
        "by_client": {},
        "total_comms": 0,
        "daily_counts": {}
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def detect_channel(command):
    """Detect communication channel from command."""
    command_lower = command.lower()
    for pattern, channel in COMM_PATTERNS.items():
        if pattern in command_lower:
            return channel
    return None


def extract_comm_details(command):
    """Extract communication details from command."""
    details = {}

    # Recipient
    for arg in ["--to", "--email", "--recipient"]:
        match = re.search(rf'{arg}[=\s]+["\']?([^"\']+)["\']?', command)
        if match:
            details["recipient"] = match.group(1).strip()
            break

    # Channel/destination
    match = re.search(r'--channel[=\s]+["\']?([^"\']+)["\']?', command)
    if match:
        details["destination"] = match.group(1).strip()

    # Subject
    match = re.search(r'--subject[=\s]+["\']?([^"\']+)["\']?', command)
    if match:
        details["subject"] = match.group(1).strip()

    # Message summary
    match = re.search(r'--message[=\s]+["\']?([^"\']+)["\']?', command)
    if match:
        details["message_summary"] = match.group(1).strip()[:100]

    # Title
    match = re.search(r'--title[=\s]+["\']?([^"\']+)["\']?', command)
    if match:
        details["title"] = match.group(1).strip()

    # File
    match = re.search(r'--file[=\s]+["\']?([^"\']+)["\']?', command)
    if match:
        details["file"] = match.group(1).strip()

    # Client
    match = re.search(r'--client[=\s]+["\']?([a-zA-Z0-9_-]+)', command)
    if match:
        details["client"] = match.group(1)
    else:
        match = re.search(r'clients/([a-zA-Z0-9_-]+)/', command)
        if match:
            details["client"] = match.group(1)

    return details


def show_status():
    state = load_state()
    comms = state.get("communications", [])
    by_channel = state.get("by_channel", {})
    by_client = state.get("by_client", {})

    print("=== Client Communication Logger ===")
    print(f"Total communications: {state.get('total_comms', 0)}")

    if by_channel:
        print("\nBy channel:")
        for channel, count in sorted(by_channel.items(), key=lambda x: x[1], reverse=True):
            print(f"  {channel}: {count}")

    if by_client:
        print("\nBy client:")
        for client, count in sorted(by_client.items(), key=lambda x: x[1], reverse=True):
            print(f"  {client}: {count}")

    daily = state.get("daily_counts", {})
    if daily:
        print("\nDaily counts (last 7 days):")
        for date in sorted(daily.keys())[-7:]:
            print(f"  {date}: {daily[date]}")

    if comms:
        print(f"\nRecent communications (last {min(10, len(comms))}):")
        for c in comms[-10:]:
            ts = c.get("timestamp", "?")[:19]
            channel = c.get("channel", "?")
            client = c.get("details", {}).get("client", "unknown")
            subject = c.get("details", {}).get("subject",
                       c.get("details", {}).get("title",
                       c.get("details", {}).get("message_summary", "N/A")))
            print(f"  [{ts}] {channel} -> {client}: {subject[:60]}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Client communication logger state reset.")
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
    tool_result = data.get("tool_result", "")

    if tool_name not in ("Bash", "bash"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    channel = detect_channel(command)

    if not channel:
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Check for errors in result
    result_str = str(tool_result).lower() if tool_result else ""
    if any(err in result_str for err in ["error", "traceback", "failed"]):
        # Failed communication - still log it
        pass

    state = load_state()
    now = datetime.now().isoformat()
    today = now[:10]
    state["total_comms"] = state.get("total_comms", 0) + 1

    details = extract_comm_details(command)

    comm_entry = {
        "timestamp": now,
        "channel": channel,
        "details": details,
        "success": not any(err in result_str for err in ["error", "traceback", "failed"]),
        "command_summary": command[:200]
    }

    state["communications"] = state.get("communications", [])
    state["communications"].append(comm_entry)
    state["communications"] = state["communications"][-200:]

    # By channel
    by_channel = state.get("by_channel", {})
    by_channel[channel] = by_channel.get(channel, 0) + 1
    state["by_channel"] = by_channel

    # By client
    client = details.get("client", "unattributed")
    by_client = state.get("by_client", {})
    by_client[client] = by_client.get(client, 0) + 1
    state["by_client"] = by_client

    # Daily
    daily = state.get("daily_counts", {})
    daily[today] = daily.get(today, 0) + 1
    state["daily_counts"] = daily

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
