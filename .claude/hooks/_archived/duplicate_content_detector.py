#!/usr/bin/env python3
"""
Hook 84: duplicate_content_detector.py - PostToolUse on Write

Detects recycled/duplicate paragraphs across outputs. Hashes paragraphs
(3+ sentences) and compares against previously written content in session.
Warns if >30% duplicate paragraphs detected.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional duplicate warnings

CLI Flags:
  --status  Show duplicate detection stats
  --reset   Clear content hash state
"""

import json
import sys
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "duplicate_content.json"

DUPLICATE_THRESHOLD = 0.30  # 30% duplicate paragraphs
MIN_SENTENCES_PER_PARAGRAPH = 3
MIN_PARAGRAPH_LENGTH = 100  # chars


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "content_hashes": {},
        "checks": [],
        "duplicates_found": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Keep hashes manageable
    if len(state["content_hashes"]) > 500:
        # Keep most recent 300
        items = sorted(state["content_hashes"].items(),
                       key=lambda x: x[1].get("timestamp", ""), reverse=True)
        state["content_hashes"] = dict(items[:300])
    state["checks"] = state["checks"][-30:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_paragraphs(content):
    """Extract meaningful paragraphs (3+ sentences)."""
    # Split by double newlines
    blocks = re.split(r'\n\s*\n', content)
    paragraphs = []

    for block in blocks:
        block = block.strip()
        # Skip headers, code blocks, lists
        if not block or block.startswith('#') or block.startswith('```'):
            continue
        if block.startswith('- ') or block.startswith('* ') or re.match(r'^\d+\.', block):
            continue

        # Count sentences
        sentences = re.split(r'[.!?]+\s+', block)
        sentences = [s for s in sentences if len(s.strip()) > 10]

        if len(sentences) >= MIN_SENTENCES_PER_PARAGRAPH and len(block) >= MIN_PARAGRAPH_LENGTH:
            paragraphs.append(block)

    return paragraphs


def hash_paragraph(paragraph):
    """Create a normalized hash of a paragraph."""
    # Normalize whitespace and case for comparison
    normalized = re.sub(r'\s+', ' ', paragraph.strip().lower())
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


def handle_status():
    state = load_state()
    print("Duplicate Content Detector Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Duplicates found: {state['duplicates_found']}")
    print(f"  Content hashes tracked: {len(state['content_hashes'])}")
    print(f"  Duplicate threshold: {DUPLICATE_THRESHOLD:.0%}")
    if state["checks"]:
        print("  Recent checks:")
        for c in state["checks"][-5:]:
            dup_pct = c.get("duplicate_pct", 0)
            status = f"DUPLICATE ({dup_pct:.0%})" if dup_pct > DUPLICATE_THRESHOLD else "clean"
            print(f"    [{status}] {c.get('file', 'unknown')}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "content_hashes": {}, "checks": [],
        "duplicates_found": 0, "total_checks": 0,
    }))
    print("Duplicate Content Detector: State reset.")
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

    if not content or len(content) < MIN_PARAGRAPH_LENGTH:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    paragraphs = extract_paragraphs(content)
    if not paragraphs:
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_name = Path(file_path).name
    existing_hashes = state.get("content_hashes", {})
    duplicate_count = 0
    new_hashes = {}

    for para in paragraphs:
        h = hash_paragraph(para)
        if h in existing_hashes and existing_hashes[h].get("file") != file_name:
            duplicate_count += 1
        new_hashes[h] = {
            "file": file_name,
            "preview": para[:60],
            "timestamp": datetime.now().isoformat(),
        }

    duplicate_pct = duplicate_count / len(paragraphs) if paragraphs else 0

    # Store new hashes
    existing_hashes.update(new_hashes)
    state["content_hashes"] = existing_hashes

    check_entry = {
        "file": file_name,
        "paragraphs": len(paragraphs),
        "duplicates": duplicate_count,
        "duplicate_pct": round(duplicate_pct, 3),
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_entry)

    if duplicate_pct > DUPLICATE_THRESHOLD:
        state["duplicates_found"] += 1
        save_state(state)
        reason = (
            f"High duplicate content in {file_name}: "
            f"{duplicate_count}/{len(paragraphs)} paragraphs ({duplicate_pct:.0%}) "
            f"match previously written content. Consider making content more unique."
        )
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
