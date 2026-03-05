#!/usr/bin/env python3
"""
Hook 87: headline_effectiveness_scorer.py - PostToolUse on Write

Scores headlines and subject lines using power word analysis. Extracts H1/H2
headers and email subject lines. Scores based on power words, emotional triggers,
specificity, and length (6-12 words ideal).

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional headline score warnings

CLI Flags:
  --status  Show headline scoring stats
  --reset   Clear state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "headline_scores.json"

# Power words by category
POWER_WORDS = {
    "urgency": [
        "now", "today", "immediately", "instant", "hurry", "fast",
        "quick", "limited", "deadline", "urgent", "before",
    ],
    "exclusivity": [
        "secret", "exclusive", "insider", "private", "hidden",
        "members-only", "invitation", "vip", "elite",
    ],
    "curiosity": [
        "surprising", "shocking", "unexpected", "revealed", "discover",
        "unbelievable", "strange", "weird", "bizarre", "truth",
    ],
    "value": [
        "free", "proven", "guaranteed", "results", "ultimate",
        "complete", "essential", "powerful", "massive", "breakthrough",
    ],
    "emotional": [
        "amazing", "incredible", "stunning", "remarkable", "extraordinary",
        "devastating", "terrifying", "heartbreaking", "inspiring", "brilliant",
    ],
    "specificity": [
        # Numbers are checked separately
    ],
}

IDEAL_WORD_COUNT = (6, 12)
LOW_SCORE_THRESHOLD = 30


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "scores": [],
        "low_scores": 0,
        "high_scores": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["scores"] = state["scores"][-30:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_headlines(content):
    """Extract H1, H2 headlines and email subject lines."""
    headlines = []

    # H1 and H2 headers
    for match in re.finditer(r'^(#{1,2})\s+(.+)', content, re.MULTILINE):
        level = len(match.group(1))
        text = match.group(2).strip()
        headlines.append({"text": text, "type": f"H{level}"})

    # Email subject lines
    for match in re.finditer(r'(?:subject|subject line)\s*:\s*(.+)', content, re.IGNORECASE):
        text = match.group(1).strip().strip('"\'')
        headlines.append({"text": text, "type": "subject"})

    return headlines


def score_headline(headline_text):
    """Score a headline 0-100."""
    score = 0
    details = {}
    words = headline_text.lower().split()
    word_count = len(words)

    # Length score (0-25 points)
    if IDEAL_WORD_COUNT[0] <= word_count <= IDEAL_WORD_COUNT[1]:
        score += 25
        details["length"] = "ideal"
    elif word_count < IDEAL_WORD_COUNT[0]:
        score += 10
        details["length"] = "too_short"
    elif word_count <= IDEAL_WORD_COUNT[1] + 3:
        score += 15
        details["length"] = "slightly_long"
    else:
        score += 5
        details["length"] = "too_long"

    # Power words score (0-35 points)
    power_found = {}
    for category, power_list in POWER_WORDS.items():
        for pw in power_list:
            if pw in headline_text.lower():
                power_found.setdefault(category, []).append(pw)

    categories_hit = len(power_found)
    total_power = sum(len(v) for v in power_found.values())
    score += min(categories_hit * 10, 25)
    score += min(total_power * 5, 10)
    details["power_words"] = power_found

    # Specificity: numbers (0-20 points)
    has_number = bool(re.search(r'\d+', headline_text))
    if has_number:
        score += 20
        details["has_number"] = True
    else:
        details["has_number"] = False

    # Punctuation/emotion (0-10 points)
    if headline_text.endswith("?"):
        score += 8  # Questions engage
        details["ends_with_question"] = True
    elif headline_text.endswith("!"):
        score += 5
    if ":" in headline_text:
        score += 5  # Colons add specificity

    # Capitalization check (0-10 points)
    if headline_text == headline_text.upper() and len(headline_text) > 10:
        score -= 5  # All caps is spammy
        details["all_caps"] = True

    return min(max(score, 0), 100), details


def handle_status():
    state = load_state()
    print("Headline Effectiveness Scorer Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  High scores (>{LOW_SCORE_THRESHOLD}): {state['high_scores']}")
    print(f"  Low scores (<={LOW_SCORE_THRESHOLD}): {state['low_scores']}")
    if state["scores"]:
        print("  Recent headline scores:")
        for s in state["scores"][-8:]:
            print(f"    [{s.get('score', 0)}/100] ({s.get('type', '?')}) {s.get('text', '')[:60]}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "scores": [], "low_scores": 0,
        "high_scores": 0, "total_checks": 0,
    }))
    print("Headline Effectiveness Scorer: State reset.")
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

    content = tool_input.get("content", "")
    file_path = tool_input.get("file_path", "")

    if not content:
        print(json.dumps({"decision": "ALLOW"}))
        return

    headlines = extract_headlines(content)
    if not headlines:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    low_headlines = []
    for h in headlines:
        score, details = score_headline(h["text"])
        entry = {
            "text": h["text"][:80],
            "type": h["type"],
            "score": score,
            "file": Path(file_path).name,
            "timestamp": datetime.now().isoformat(),
        }
        state["scores"].append(entry)

        if score <= LOW_SCORE_THRESHOLD:
            state["low_scores"] += 1
            low_headlines.append(f"'{h['text'][:50]}' ({h['type']}, score: {score})")
        else:
            state["high_scores"] += 1

    save_state(state)

    if low_headlines:
        reason = (
            f"Weak headlines detected in {Path(file_path).name}: "
            + "; ".join(low_headlines[:3])
            + ". Consider adding power words, numbers, or questions."
        )
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
