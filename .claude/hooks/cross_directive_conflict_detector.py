#!/usr/bin/env python3
"""
Hook 75: cross_directive_conflict_detector.py - PostToolUse on Read

When loading multiple directives in a session, detects conflicting instructions
such as conflicting output paths, conflicting quality rules, or overlapping scope.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional conflict warnings

CLI Flags:
  --status  Show loaded directives and detected conflicts
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
STATE_FILE = STATE_DIR / "directive_conflicts.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"loaded_directives": {}, "conflicts": [], "total_checks": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_directive_file(file_path):
    path = str(file_path).lower()
    return "directives/" in path and path.endswith(".md")


def extract_output_paths(content):
    """Extract output file paths from directive content."""
    paths = []
    matches = re.findall(r'\.tmp/\S+', content)
    paths.extend(matches)
    matches = re.findall(r'output[s]?\s*(?:to|:)\s*["\']?(\S+)', content, re.IGNORECASE)
    paths.extend(matches)
    return list(set(paths))


def extract_quality_rules(content):
    """Extract quality-related rules from directive content."""
    rules = []
    content_lower = content.lower()
    # Look for word count requirements
    wc_matches = re.findall(r'(\d+)\s*(?:words?|word count)', content_lower)
    for wc in wc_matches:
        rules.append(f"word_count:{wc}")
    # Look for section requirements
    sec_matches = re.findall(r'(\d+)\s*sections?', content_lower)
    for sec in sec_matches:
        rules.append(f"sections:{sec}")
    # Look for tone requirements
    tone_words = ["professional", "casual", "formal", "friendly", "authoritative"]
    for tw in tone_words:
        if tw in content_lower:
            rules.append(f"tone:{tw}")
    return rules


def extract_scope_keywords(content):
    """Extract scope keywords to detect overlap."""
    scope_keywords = set()
    # Extract from title and first paragraph
    lines = content.split("\n")
    for line in lines[:10]:
        cleaned = re.sub(r'[#*_\[\]()]', '', line).strip().lower()
        words = cleaned.split()
        for w in words:
            if len(w) > 3 and w.isalpha():
                scope_keywords.add(w)
    return scope_keywords


def detect_conflicts(new_directive, new_info, existing_directives):
    """Detect conflicts between new directive and existing ones."""
    conflicts = []

    for name, info in existing_directives.items():
        if name == new_directive:
            continue

        # Check output path conflicts
        new_paths = set(new_info.get("output_paths", []))
        old_paths = set(info.get("output_paths", []))
        path_overlap = new_paths & old_paths
        if path_overlap:
            conflicts.append({
                "type": "output_path_conflict",
                "directives": [new_directive, name],
                "detail": f"Shared output paths: {', '.join(path_overlap)}",
            })

        # Check quality rule conflicts (e.g., different word counts)
        new_rules = new_info.get("quality_rules", [])
        old_rules = info.get("quality_rules", [])
        for nr in new_rules:
            for orule in old_rules:
                if nr.split(":")[0] == orule.split(":")[0] and nr != orule:
                    conflicts.append({
                        "type": "quality_rule_conflict",
                        "directives": [new_directive, name],
                        "detail": f"Conflicting rules: {nr} vs {orule}",
                    })

        # Check scope overlap
        new_scope = set(new_info.get("scope_keywords", []))
        old_scope = set(info.get("scope_keywords", []))
        overlap = new_scope & old_scope
        overlap_ratio = len(overlap) / max(len(new_scope | old_scope), 1)
        if overlap_ratio > 0.5 and len(overlap) > 5:
            conflicts.append({
                "type": "scope_overlap",
                "directives": [new_directive, name],
                "detail": f"High scope overlap ({len(overlap)} shared keywords, {overlap_ratio:.0%})",
            })

    return conflicts


def handle_status():
    state = load_state()
    print("Cross-Directive Conflict Detector Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Directives loaded: {len(state['loaded_directives'])}")
    print(f"  Conflicts found: {len(state['conflicts'])}")
    if state["loaded_directives"]:
        print("  Loaded directives:")
        for name in state["loaded_directives"]:
            print(f"    - {name}")
    if state["conflicts"]:
        print("  Conflicts:")
        for c in state["conflicts"][-5:]:
            print(f"    [{c['type']}] {' <-> '.join(c['directives'])}")
            print(f"      {c['detail']}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"loaded_directives": {}, "conflicts": [], "total_checks": 0}))
    print("Cross-Directive Conflict Detector: State reset.")
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
    tool_result = data.get("tool_result", "")

    if tool_name != "Read" or "tool_result" not in data:
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    if not is_directive_file(file_path):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1
    content = str(tool_result) if tool_result else ""
    directive_name = Path(file_path).name

    new_info = {
        "output_paths": extract_output_paths(content),
        "quality_rules": extract_quality_rules(content),
        "scope_keywords": list(extract_scope_keywords(content)),
        "loaded_at": datetime.now().isoformat(),
    }

    conflicts = detect_conflicts(directive_name, new_info, state["loaded_directives"])
    state["loaded_directives"][directive_name] = new_info
    state["conflicts"].extend(conflicts)
    save_state(state)

    if conflicts:
        warnings = []
        for c in conflicts:
            warnings.append(f"[{c['type']}] {' <-> '.join(c['directives'])}: {c['detail']}")
        reason = "Potential conflicts detected:\n" + "\n".join(warnings)
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
