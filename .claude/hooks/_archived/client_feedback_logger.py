#!/usr/bin/env python3
"""
Hook 108: client_feedback_logger.py (PostToolUse on Bash)
Purpose: Log when client feedback is received for learning.
Logic: Detect feedback-related activities (reading feedback files, processing
responses). Log feedback events in state for self-annealing and improvement tracking.

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
STATE_FILE = STATE_DIR / "client_feedback.json"

# Feedback indicators in commands
FEEDBACK_PATTERNS = [
    (r'feedback', "feedback file access"),
    (r'review[_-]?notes?', "review notes"),
    (r'revision[_-]?request', "revision request"),
    (r'client[_-]?response', "client response"),
    (r'approval[_-]?status', "approval status check"),
    (r'change[_-]?request', "change request"),
    (r'comment', "comment processing"),
    (r'satisfaction', "satisfaction survey"),
    (r'nps[_-]?score', "NPS score"),
    (r'testimonial', "testimonial"),
]

# Feedback sentiment indicators
POSITIVE_INDICATORS = [
    "approved", "love", "great", "excellent", "perfect", "amazing",
    "good job", "well done", "thank", "happy", "satisfied", "impressed"
]

NEGATIVE_INDICATORS = [
    "rejected", "redo", "revise", "change", "wrong", "missing",
    "disappointed", "unhappy", "not what", "off brand", "doesn't match"
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "feedback_events": [],
        "by_client": {},
        "sentiment_counts": {"positive": 0, "negative": 0, "neutral": 0},
        "total_events": 0,
        "lessons_learned": []
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def detect_feedback_type(command):
    """Detect if command involves feedback and what type."""
    command_lower = command.lower()
    for pattern, ftype in FEEDBACK_PATTERNS:
        if re.search(pattern, command_lower):
            return ftype
    return None


def analyze_sentiment(text):
    """Simple sentiment analysis on feedback text."""
    text_lower = text.lower()
    pos_count = sum(1 for w in POSITIVE_INDICATORS if w in text_lower)
    neg_count = sum(1 for w in NEGATIVE_INDICATORS if w in text_lower)

    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    return "neutral"


def extract_client_from_command(command):
    """Extract client name from command."""
    match = re.search(r'clients/([a-zA-Z0-9_-]+)/', command)
    if match:
        return match.group(1)
    match = re.search(r'--client[=\s]+["\']?([a-zA-Z0-9_-]+)', command)
    if match:
        return match.group(1)
    return "unknown"


def show_status():
    state = load_state()
    events = state.get("feedback_events", [])
    by_client = state.get("by_client", {})
    sentiments = state.get("sentiment_counts", {})

    print("=== Client Feedback Logger ===")
    print(f"Total feedback events: {state.get('total_events', 0)}")
    print(f"Sentiment breakdown:")
    print(f"  Positive: {sentiments.get('positive', 0)}")
    print(f"  Negative: {sentiments.get('negative', 0)}")
    print(f"  Neutral: {sentiments.get('neutral', 0)}")

    if by_client:
        print("\nFeedback by client:")
        for client, cdata in sorted(by_client.items()):
            total = cdata.get("total", 0)
            pos = cdata.get("positive", 0)
            neg = cdata.get("negative", 0)
            print(f"  {client}: {total} events ({pos} positive, {neg} negative)")

    if events:
        print(f"\nRecent feedback events (last {min(10, len(events))}):")
        for e in events[-10:]:
            ts = e.get("timestamp", "?")[:19]
            client = e.get("client", "?")
            ftype = e.get("feedback_type", "?")
            sentiment = e.get("sentiment", "?")
            print(f"  [{ts}] {client}: {ftype} ({sentiment})")

    lessons = state.get("lessons_learned", [])
    if lessons:
        print(f"\nLessons learned ({len(lessons)}):")
        for lesson in lessons[-5:]:
            print(f"  - {lesson}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Client feedback logger state reset.")
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
    feedback_type = detect_feedback_type(command)

    if not feedback_type:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()
    state["total_events"] = state.get("total_events", 0) + 1

    client = extract_client_from_command(command)

    # Analyze sentiment from result
    result_text = str(tool_result) if tool_result else ""
    sentiment = analyze_sentiment(result_text + " " + command)

    # Create event
    event = {
        "timestamp": now,
        "client": client,
        "feedback_type": feedback_type,
        "sentiment": sentiment,
        "command_summary": command[:150]
    }

    # Update events list
    state["feedback_events"] = state.get("feedback_events", [])
    state["feedback_events"].append(event)
    state["feedback_events"] = state["feedback_events"][-200:]

    # Update sentiment counts
    sentiments = state.get("sentiment_counts", {"positive": 0, "negative": 0, "neutral": 0})
    sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
    state["sentiment_counts"] = sentiments

    # Update by client
    by_client = state.get("by_client", {})
    if client not in by_client:
        by_client[client] = {"total": 0, "positive": 0, "negative": 0, "neutral": 0}
    by_client[client]["total"] = by_client[client].get("total", 0) + 1
    by_client[client][sentiment] = by_client[client].get(sentiment, 0) + 1
    state["by_client"] = by_client

    # Generate lesson from negative feedback
    if sentiment == "negative":
        lessons = state.get("lessons_learned", [])
        lesson = f"[{now[:10]}] {client}: Negative feedback on {feedback_type}. Review and improve workflow."
        lessons.append(lesson)
        state["lessons_learned"] = lessons[-50:]

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
