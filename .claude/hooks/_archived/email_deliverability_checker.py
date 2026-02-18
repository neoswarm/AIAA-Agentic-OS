#!/usr/bin/env python3
"""
Hook 88: email_deliverability_checker.py - PostToolUse on Write

Checks email content for spam triggers that hurt deliverability: spam trigger
words, excessive punctuation, ALL CAPS, and other red flags.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional spam risk warnings

CLI Flags:
  --status  Show deliverability check stats
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
STATE_FILE = STATE_DIR / "email_deliverability.json"

EMAIL_PATTERNS = ["*email*", "*outreach*", "*cold*email*", "*nurture*", "*drip*"]

# Spam trigger words (grouped by severity)
SPAM_TRIGGERS_HIGH = [
    "act now", "buy now", "limited time", "order now", "urgent",
    "free gift", "winner", "congratulations", "cash bonus",
    "100% free", "click here", "click below",
    "no obligation", "no cost", "no fee", "risk free",
    "guarantee", "double your", "earn extra cash",
    "make money", "extra income",
]

SPAM_TRIGGERS_MEDIUM = [
    "amazing", "incredible offer", "once in a lifetime",
    "special promotion", "exclusive deal", "act immediately",
    "don't delete", "not spam", "this isn't spam",
    "dear friend", "as seen on", "call now",
    "apply now", "instant access", "limited offer",
    "offer expires", "while supplies last",
]

SPAM_TRIGGERS_LOW = [
    "free", "bonus", "discount", "save", "offer",
    "deal", "affordable", "bargain", "cheap",
    "lowest price", "best price",
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "checks": [],
        "high_risk": 0,
        "medium_risk": 0,
        "low_risk": 0,
        "clean": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["checks"] = state["checks"][-30:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_email_content(file_path):
    filename_lower = Path(file_path).name.lower()
    return any(fnmatch(filename_lower, pat) for pat in EMAIL_PATTERNS)


def check_spam_words(content):
    """Check for spam trigger words. Returns categorized findings."""
    content_lower = content.lower()
    high = [w for w in SPAM_TRIGGERS_HIGH if w in content_lower]
    medium = [w for w in SPAM_TRIGGERS_MEDIUM if w in content_lower]
    low = [w for w in SPAM_TRIGGERS_LOW if w in content_lower]
    return {"high": high, "medium": medium, "low": low}


def check_formatting_issues(content):
    """Check for formatting issues that trigger spam filters."""
    issues = []

    # Excessive exclamation marks
    exclamation_count = content.count("!")
    if exclamation_count > 5:
        issues.append(f"Excessive exclamation marks ({exclamation_count})")

    # Excessive question marks
    question_runs = re.findall(r'\?{2,}', content)
    if question_runs:
        issues.append("Multiple consecutive question marks")

    # ALL CAPS words (more than 3 in a row)
    caps_words = re.findall(r'\b[A-Z]{3,}\b', content)
    # Filter out common abbreviations
    caps_words = [w for w in caps_words if w not in {"CTA", "VSL", "ROI", "CEO", "SaaS", "API", "URL", "SEO", "HTML", "CSS"}]
    if len(caps_words) > 3:
        issues.append(f"Excessive ALL CAPS words ({len(caps_words)}): {', '.join(caps_words[:5])}")

    # Excessive use of $ signs
    dollar_count = content.count("$")
    if dollar_count > 5:
        issues.append(f"Excessive dollar signs ({dollar_count})")

    # Lines that are all bold/caps
    lines = content.split("\n")
    bold_lines = sum(1 for l in lines if l.strip().startswith("**") and l.strip().endswith("**"))
    if bold_lines > 5:
        issues.append(f"Many all-bold lines ({bold_lines})")

    # Subject line length (if detectable)
    subject_match = re.search(r'subject\s*(?:line)?\s*:\s*(.+)', content, re.IGNORECASE)
    if subject_match:
        subject = subject_match.group(1).strip()
        if len(subject) > 60:
            issues.append(f"Subject line too long ({len(subject)} chars, recommended: <60)")

    return issues


def compute_spam_score(spam_words, formatting_issues):
    """Compute a spam risk score (0-100, higher = more risky)."""
    score = 0
    score += len(spam_words.get("high", [])) * 15
    score += len(spam_words.get("medium", [])) * 8
    score += len(spam_words.get("low", [])) * 3
    score += len(formatting_issues) * 10
    return min(score, 100)


def handle_status():
    state = load_state()
    print("Email Deliverability Checker Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  High risk: {state['high_risk']}")
    print(f"  Medium risk: {state['medium_risk']}")
    print(f"  Low risk: {state['low_risk']}")
    print(f"  Clean: {state['clean']}")
    if state["checks"]:
        print("  Recent checks:")
        for c in state["checks"][-5:]:
            score = c.get("spam_score", 0)
            risk = "HIGH" if score > 50 else "MEDIUM" if score > 25 else "LOW" if score > 10 else "clean"
            print(f"    [{risk}] {c.get('file', 'unknown')} (spam score: {score})")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "checks": [], "high_risk": 0, "medium_risk": 0,
        "low_risk": 0, "clean": 0, "total_checks": 0,
    }))
    print("Email Deliverability Checker: State reset.")
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

    if not is_email_content(file_path) or not content:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    spam_words = check_spam_words(content)
    formatting_issues = check_formatting_issues(content)
    spam_score = compute_spam_score(spam_words, formatting_issues)

    file_name = Path(file_path).name
    check_entry = {
        "file": file_name,
        "spam_score": spam_score,
        "high_triggers": spam_words["high"][:5],
        "formatting_issues": formatting_issues[:3],
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_entry)

    if spam_score > 50:
        state["high_risk"] += 1
        save_state(state)
        warnings = []
        if spam_words["high"]:
            warnings.append(f"High-risk spam words: {', '.join(spam_words['high'][:3])}")
        warnings.extend(formatting_issues[:2])
        reason = f"High spam risk in {file_name} (score: {spam_score}): " + "; ".join(warnings)
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    elif spam_score > 25:
        state["medium_risk"] += 1
        save_state(state)
        reason = f"Moderate spam risk in {file_name} (score: {spam_score}). Review spam triggers."
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    elif spam_score > 10:
        state["low_risk"] += 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))
    else:
        state["clean"] += 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
