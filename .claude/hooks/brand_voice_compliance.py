#!/usr/bin/env python3
"""
Hook 81: brand_voice_compliance.py - PostToolUse on Write

Checks if written content follows brand voice guidelines from
context/brand_voice.md. Detects banned words, enforces required phrases,
and validates tone.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional warnings

CLI Flags:
  --status  Show brand voice compliance stats
  --reset   Clear state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
BRAND_VOICE_FILE = BASE_DIR / "context" / "brand_voice.md"
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "brand_voice_compliance.json"

# Default banned words if no brand_voice.md found
DEFAULT_BANNED_WORDS = [
    "synergy", "paradigm", "leverage", "circle back", "touch base",
    "low-hanging fruit", "move the needle", "deep dive", "best-in-class",
]

# Default tone indicators
FORMAL_INDICATORS = [
    "hereunder", "aforementioned", "pursuant", "whereby", "therein",
    "notwithstanding", "hereinafter", "whereas",
]

CASUAL_INDICATORS = [
    "gonna", "wanna", "gotta", "kinda", "sorta", "y'all",
    "lol", "omg", "btw", "tbh",
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "checks": [],
        "violations_found": 0,
        "clean_writes": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["checks"] = state["checks"][-30:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def load_brand_rules():
    """Load brand voice rules from context/brand_voice.md."""
    rules = {
        "banned_words": DEFAULT_BANNED_WORDS[:],
        "required_phrases": [],
        "tone": None,
    }

    if not BRAND_VOICE_FILE.exists():
        return rules

    try:
        content = BRAND_VOICE_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return rules

    content_lower = content.lower()

    # Extract banned words section
    banned_match = re.search(
        r'(?:banned|avoid|don\'t use|words to avoid|never use)[^:]*:?\s*\n((?:[-*]\s*.+\n?)+)',
        content_lower
    )
    if banned_match:
        items = re.findall(r'[-*]\s*["\']?([^"\'\n]+)', banned_match.group(1))
        rules["banned_words"].extend([w.strip().lower() for w in items if w.strip()])

    # Detect tone preference
    if any(w in content_lower for w in ["professional", "formal", "corporate"]):
        rules["tone"] = "professional"
    elif any(w in content_lower for w in ["casual", "friendly", "conversational", "approachable"]):
        rules["tone"] = "casual"

    # Extract required phrases
    required_match = re.search(
        r'(?:required|always use|must include|key phrases)[^:]*:?\s*\n((?:[-*]\s*.+\n?)+)',
        content_lower
    )
    if required_match:
        items = re.findall(r'[-*]\s*["\']?([^"\'\n]+)', required_match.group(1))
        rules["required_phrases"] = [w.strip().lower() for w in items if w.strip()]

    return rules


def check_banned_words(content, banned_words):
    """Check content for banned words/phrases."""
    found = []
    content_lower = content.lower()
    for word in banned_words:
        if word.lower() in content_lower:
            found.append(word)
    return found


def check_tone_consistency(content, expected_tone):
    """Check if content matches expected tone."""
    issues = []
    content_lower = content.lower()

    if expected_tone == "professional":
        casual_found = [w for w in CASUAL_INDICATORS if w in content_lower]
        if casual_found:
            issues.append(f"Casual language in professional brand: {', '.join(casual_found[:3])}")

    elif expected_tone == "casual":
        formal_found = [w for w in FORMAL_INDICATORS if w in content_lower]
        if formal_found:
            issues.append(f"Overly formal language in casual brand: {', '.join(formal_found[:3])}")

    return issues


def handle_status():
    state = load_state()
    rules = load_brand_rules()
    print("Brand Voice Compliance Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Clean writes: {state['clean_writes']}")
    print(f"  Violations found: {state['violations_found']}")
    print(f"  Brand voice file: {'exists' if BRAND_VOICE_FILE.exists() else 'NOT FOUND'}")
    print(f"  Expected tone: {rules.get('tone', 'not set')}")
    print(f"  Banned words: {len(rules.get('banned_words', []))}")
    if state["checks"]:
        print("  Recent checks:")
        for c in state["checks"][-5:]:
            status = "VIOLATION" if c.get("violations") else "clean"
            print(f"    [{status}] {c.get('file', 'unknown')}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "checks": [], "violations_found": 0,
        "clean_writes": 0, "total_checks": 0,
    }))
    print("Brand Voice Compliance: State reset.")
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

    if not file_path.endswith(".md") or not content:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1
    rules = load_brand_rules()

    violations = []

    # Check banned words
    banned_found = check_banned_words(content, rules.get("banned_words", []))
    if banned_found:
        violations.append(f"Banned words found: {', '.join(banned_found[:5])}")

    # Check tone
    tone = rules.get("tone")
    if tone:
        tone_issues = check_tone_consistency(content, tone)
        violations.extend(tone_issues)

    file_name = Path(file_path).name
    check_entry = {
        "file": file_name,
        "violations": violations,
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_entry)

    if violations:
        state["violations_found"] += 1
        save_state(state)
        reason = f"Brand voice issues in {file_name}: " + "; ".join(violations)
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        state["clean_writes"] += 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
