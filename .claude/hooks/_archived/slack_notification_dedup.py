#!/usr/bin/env python3
"""
Hook 35: Slack Notification Dedup (PreToolUse on Bash)

Before running send_slack_notification.py:
- Load .tmp/hooks/slack_history.json
- Check if a similar message was sent in the last 5 minutes
- If duplicate detected: WARN via stderr
- Log the notification with timestamp and content hash
- Exit 0 always (warn only).
"""

import json
import sys
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "slack_history.json"

DEDUP_WINDOW_MINUTES = 5


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"notifications": [], "stats": {"total": 0, "duplicates_warned": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_message(command):
    """Extract the message content from the command."""
    patterns = [
        r'--message\s+"([^"]+)"',
        r"--message\s+'([^']+)'",
        r'--message\s+(\S+)',
        r'-m\s+"([^"]+)"',
        r"-m\s+'([^']+)'",
    ]
    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            return match.group(1)

    # Try to extract channel too
    channel_match = re.search(r'--channel\s+"?([^"\s]+)"?', command)
    channel = channel_match.group(1) if channel_match else "unknown"

    return f"slack_command_{channel}"


def compute_message_hash(message):
    """Create a hash of the message for dedup comparison."""
    # Normalize: lowercase, strip whitespace, remove timestamps
    normalized = message.lower().strip()
    # Remove common variable parts (timestamps, dates, numbers)
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', normalized)
    normalized = re.sub(r'\d{2}:\d{2}:\d{2}', 'TIME', normalized)
    return hashlib.md5(normalized.encode()).hexdigest()


def check_for_duplicate(state, message_hash):
    """Check if a similar message was sent recently."""
    now = datetime.now()
    cutoff = now - timedelta(minutes=DEDUP_WINDOW_MINUTES)

    for notification in reversed(state.get("notifications", [])):
        if notification.get("hash") == message_hash:
            sent_time = datetime.fromisoformat(notification["timestamp"])
            if sent_time > cutoff:
                minutes_ago = (now - sent_time).total_seconds() / 60
                return True, minutes_ago

    return False, 0


def is_slack_script(command):
    """Check if this command runs a Slack notification script."""
    return "send_slack" in command or "slack_notification" in command


def handle_status():
    state = load_state()
    print("=== Slack Notification Dedup Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"Total notifications logged: {stats.get('total', 0)}")
    print(f"Duplicate warnings issued: {stats.get('duplicates_warned', 0)}")
    print(f"Dedup window: {DEDUP_WINDOW_MINUTES} minutes")

    notifications = state.get("notifications", [])
    if notifications:
        print(f"\nRecent notifications:")
        for n in notifications[-10:]:
            print(f"  [{n.get('timestamp', '?')}] hash={n.get('hash', '?')[:8]}...")
            if n.get("message_preview"):
                print(f"    Preview: {n['message_preview'][:60]}...")
    else:
        print("\nNo notifications logged yet.")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Slack notification dedup state reset.")
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

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")

    if not is_slack_script(command):
        sys.exit(0)

    state = load_state()
    message = extract_message(command)
    message_hash = compute_message_hash(message)

    # Check for duplicate
    is_dup, minutes_ago = check_for_duplicate(state, message_hash)

    # Log this notification
    notification_record = {
        "hash": message_hash,
        "message_preview": message[:100],
        "timestamp": datetime.now().isoformat(),
    }
    state["notifications"].append(notification_record)
    # Keep last 100 notifications
    state["notifications"] = state["notifications"][-100:]
    state["stats"]["total"] = state["stats"].get("total", 0) + 1

    if is_dup:
        state["stats"]["duplicates_warned"] = state["stats"].get("duplicates_warned", 0) + 1
        save_state(state)
        sys.stderr.write(
            f"[SLACK DEDUP] Similar Slack notification sent {minutes_ago:.1f} minutes ago. "
            f"Possible duplicate.\n"
        )
    else:
        save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
