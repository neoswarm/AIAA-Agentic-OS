#!/usr/bin/env python3
"""
Hook 82: cta_validation.py - PostToolUse on Write

Ensures marketing content has calls-to-action. Checks for CTA patterns
(action verbs + urgency words) in VSL, email, sales, and landing page content.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional CTA warnings

CLI Flags:
  --status  Show CTA validation stats
  --reset   Clear state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime
from fnmatch import fnmatch

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "cta_validation.json"

# File patterns that should contain CTAs
CTA_REQUIRED_PATTERNS = [
    "*vsl*", "*email*", "*sales*", "*landing*",
    "*funnel*", "*offer*", "*pitch*", "*outreach*",
]

# CTA action verbs
ACTION_VERBS = [
    "click", "sign up", "register", "subscribe", "download",
    "get started", "join", "buy", "order", "book", "schedule",
    "claim", "grab", "start", "try", "discover", "learn more",
    "call now", "contact", "reserve", "enroll", "apply",
    "unlock", "access", "activate", "upgrade",
]

# Urgency words
URGENCY_WORDS = [
    "now", "today", "limited", "exclusive", "hurry", "fast",
    "immediately", "don't miss", "don't wait", "act now",
    "before it's gone", "last chance", "only", "deadline",
    "expires", "while supplies last", "spots left",
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "checks": [],
        "missing_cta": 0,
        "has_cta": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["checks"] = state["checks"][-30:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def requires_cta(file_path):
    """Check if the file type requires a CTA."""
    filename_lower = Path(file_path).name.lower()
    return any(fnmatch(filename_lower, pat) for pat in CTA_REQUIRED_PATTERNS)


def find_cta_elements(content):
    """Find CTA elements in content."""
    content_lower = content.lower()
    found_actions = []
    found_urgency = []

    for verb in ACTION_VERBS:
        if verb.lower() in content_lower:
            found_actions.append(verb)

    for word in URGENCY_WORDS:
        if word.lower() in content_lower:
            found_urgency.append(word)

    # Also check for CTA-like patterns (buttons, links with action text)
    cta_patterns = [
        r'\[.*?(?:click|sign|get|start|join|book|buy).*?\]\(.*?\)',  # Markdown links
        r'(?:button|cta|call.to.action)\s*[:=]',  # Explicit CTA markers
        r'<a\s+.*?href.*?>.*?(?:click|sign|get|start).*?</a>',  # HTML links
    ]
    pattern_matches = 0
    for pattern in cta_patterns:
        if re.search(pattern, content_lower):
            pattern_matches += 1

    return found_actions, found_urgency, pattern_matches


def compute_cta_score(actions, urgency, patterns):
    """Compute a CTA effectiveness score (0-100)."""
    score = 0
    score += min(len(actions) * 15, 45)  # Up to 45 for action verbs
    score += min(len(urgency) * 10, 30)  # Up to 30 for urgency
    score += min(patterns * 15, 25)       # Up to 25 for CTA patterns
    return min(score, 100)


def handle_status():
    state = load_state()
    print("CTA Validation Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Files with CTA: {state['has_cta']}")
    print(f"  Files missing CTA: {state['missing_cta']}")
    if state["checks"]:
        print("  Recent checks:")
        for c in state["checks"][-5:]:
            score = c.get("cta_score", 0)
            status = "HAS CTA" if score > 20 else "MISSING CTA"
            print(f"    [{status}] {c.get('file', 'unknown')} (score: {score})")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "checks": [], "missing_cta": 0, "has_cta": 0, "total_checks": 0,
    }))
    print("CTA Validation: State reset.")
    sys.exit(0)


def main():
    if "--status" in sys.argv:
        handle_status()
    if "--reset" in sys.argv:
        handle_reset()

    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, IOError):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Write" or "tool_result" not in data:
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    if not requires_cta(file_path) or not content:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    actions, urgency, patterns = find_cta_elements(content)
    score = compute_cta_score(actions, urgency, patterns)

    file_name = Path(file_path).name
    check_entry = {
        "file": file_name,
        "cta_score": score,
        "action_verbs": actions[:5],
        "urgency_words": urgency[:5],
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_entry)

    if score < 20:
        state["missing_cta"] += 1
        save_state(state)
        reason = (
            f"Marketing content {file_name} appears to lack a clear CTA "
            f"(score: {score}/100). "
            f"Consider adding action verbs ({', '.join(ACTION_VERBS[:5])}) "
            f"and urgency elements."
        )
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        state["has_cta"] += 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
