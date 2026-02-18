#!/usr/bin/env python3
"""
Hook 86: tone_consistency_checker.py - PostToolUse on Write

Ensures consistent tone across sections of a deliverable. Analyzes formality
level via sentence length, vocabulary complexity, and personal pronoun usage.
Flags sections that deviate significantly from the overall tone.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional tone warnings

CLI Flags:
  --status  Show tone consistency stats
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
STATE_FILE = STATE_DIR / "tone_consistency.json"

# Personal pronouns indicating casual tone
FIRST_PERSON = {"i", "me", "my", "mine", "we", "us", "our", "ours"}
SECOND_PERSON = {"you", "your", "yours", "yourself"}

# Complex vocabulary indicators (formal tone)
COMPLEX_WORDS = {
    "utilize", "implement", "facilitate", "leverage", "optimize",
    "constitute", "demonstrate", "subsequent", "therefore", "furthermore",
    "moreover", "consequently", "notwithstanding", "aforementioned",
    "herein", "whereas", "thereby", "nevertheless", "henceforth",
}

DEVIATION_THRESHOLD = 2.0  # Standard deviations


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "checks": [],
        "inconsistencies_found": 0,
        "consistent_writes": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["checks"] = state["checks"][-30:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def split_into_sections(content):
    """Split content into sections by headers."""
    sections = []
    current_section = {"header": "(intro)", "text": ""}

    for line in content.split("\n"):
        if line.strip().startswith("#"):
            if current_section["text"].strip():
                sections.append(current_section)
            header = re.sub(r'^#+\s*', '', line.strip())
            current_section = {"header": header[:60], "text": ""}
        else:
            current_section["text"] += line + "\n"

    if current_section["text"].strip():
        sections.append(current_section)

    return sections


def analyze_section_tone(text):
    """Analyze the tone of a text section. Returns a formality score."""
    words = text.lower().split()
    if len(words) < 20:
        return None  # Too short to analyze

    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

    if not sentences:
        return None

    # Average sentence length (longer = more formal)
    avg_sentence_len = sum(len(s.split()) for s in sentences) / len(sentences)

    # Personal pronoun density (higher = more casual)
    word_set = set(words)
    first_person_count = sum(1 for w in words if w in FIRST_PERSON)
    second_person_count = sum(1 for w in words if w in SECOND_PERSON)
    pronoun_density = (first_person_count + second_person_count) / len(words)

    # Complex word density (higher = more formal)
    complex_count = sum(1 for w in words if w in COMPLEX_WORDS)
    complex_density = complex_count / len(words)

    # Formality score: higher = more formal
    formality = (
        avg_sentence_len * 0.3 +        # Longer sentences = formal
        complex_density * 100 * 0.4 +    # Complex words = formal
        (1 - pronoun_density) * 10 * 0.3  # Fewer pronouns = formal
    )

    return {
        "formality": round(formality, 2),
        "avg_sentence_len": round(avg_sentence_len, 1),
        "pronoun_density": round(pronoun_density, 4),
        "complex_density": round(complex_density, 4),
        "word_count": len(words),
    }


def find_inconsistencies(section_analyses):
    """Find sections that deviate significantly from the average tone."""
    if len(section_analyses) < 2:
        return []

    formality_scores = [a["analysis"]["formality"] for a in section_analyses if a["analysis"]]
    if len(formality_scores) < 2:
        return []

    avg = sum(formality_scores) / len(formality_scores)
    # Simple standard deviation
    variance = sum((s - avg) ** 2 for s in formality_scores) / len(formality_scores)
    std_dev = variance ** 0.5

    if std_dev < 0.5:
        return []  # Very consistent

    inconsistencies = []
    for sa in section_analyses:
        if not sa["analysis"]:
            continue
        score = sa["analysis"]["formality"]
        deviation = abs(score - avg) / max(std_dev, 0.1)
        if deviation > DEVIATION_THRESHOLD:
            direction = "more formal" if score > avg else "more casual"
            inconsistencies.append({
                "section": sa["header"],
                "deviation": round(deviation, 1),
                "direction": direction,
                "score": score,
                "avg": round(avg, 2),
            })

    return inconsistencies


def handle_status():
    state = load_state()
    print("Tone Consistency Checker Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Consistent writes: {state['consistent_writes']}")
    print(f"  Inconsistencies found: {state['inconsistencies_found']}")
    if state["checks"]:
        print("  Recent checks:")
        for c in state["checks"][-5:]:
            issues = c.get("inconsistencies", [])
            status = f"{len(issues)} issues" if issues else "consistent"
            print(f"    [{status}] {c.get('file', 'unknown')}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "checks": [], "inconsistencies_found": 0,
        "consistent_writes": 0, "total_checks": 0,
    }))
    print("Tone Consistency Checker: State reset.")
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

    if not content or len(content) < 500:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    sections = split_into_sections(content)
    if len(sections) < 2:
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))
        return

    section_analyses = []
    for section in sections:
        analysis = analyze_section_tone(section["text"])
        section_analyses.append({
            "header": section["header"],
            "analysis": analysis,
        })

    inconsistencies = find_inconsistencies(section_analyses)

    file_name = Path(file_path).name
    check_entry = {
        "file": file_name,
        "sections_analyzed": len(section_analyses),
        "inconsistencies": inconsistencies,
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_entry)

    if inconsistencies:
        state["inconsistencies_found"] += 1
        save_state(state)
        warnings = []
        for inc in inconsistencies[:3]:
            warnings.append(
                f"Section '{inc['section']}' is {inc['direction']} than average "
                f"(deviation: {inc['deviation']}x)"
            )
        reason = f"Tone inconsistencies in {file_name}: " + "; ".join(warnings)
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        state["consistent_writes"] += 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
