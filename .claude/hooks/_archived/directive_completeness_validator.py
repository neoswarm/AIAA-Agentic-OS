#!/usr/bin/env python3
"""
Hook 71: directive_completeness_validator.py - PreToolUse on Bash

When executing a script from execution/, checks that the corresponding directive
exists and has required sections (What This Workflow Is, Prerequisites, How to Run,
Inputs, Process, Quality Gates).

Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages via sys.stderr.write()
  - Never prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show directive completeness stats
  --reset   Clear state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
DIRECTIVES_DIR = BASE_DIR / "directives"
EXECUTION_DIR = BASE_DIR / "execution"
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "directive_completeness.json"

REQUIRED_SECTIONS = [
    "What This Workflow Is",
    "Prerequisites",
    "How to Run",
    "Inputs",
    "Process",
    "Quality Gates",
]

STRIP_PREFIXES = ["generate_", "create_", "deploy_", "run_", "write_", "send_", "research_", "validate_"]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": [], "missing_directives": [], "incomplete_directives": []}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_script_name(command):
    """Extract script filename from bash command."""
    match = re.search(r'python3?\s+(?:\S*/)?execution/(\S+\.py)', command)
    return match.group(1) if match else None


def derive_directive_keywords(script_name):
    """Derive keywords from script name for directive matching."""
    name = script_name.replace(".py", "")
    for prefix in STRIP_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    keywords = set(name.split("_"))
    return {k for k in keywords if len(k) > 2}


def find_matching_directive(keywords):
    """Find a directive that matches the script keywords."""
    if not DIRECTIVES_DIR.exists():
        return None
    for directive in DIRECTIVES_DIR.glob("*.md"):
        d_name = directive.stem.lower().replace("-", "_")
        d_words = set(d_name.split("_"))
        overlap = keywords & d_words
        if len(overlap) >= 1:
            return directive
    return None


def check_directive_sections(directive_path):
    """Check which required sections are present in a directive."""
    try:
        content = directive_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], REQUIRED_SECTIONS[:]

    found = []
    missing = []
    content_lower = content.lower()

    for section in REQUIRED_SECTIONS:
        pattern = r'^#+\s*' + re.escape(section.lower())
        if re.search(pattern, content_lower, re.MULTILINE):
            found.append(section)
        elif section.lower() in content_lower:
            found.append(section)
        else:
            missing.append(section)

    return found, missing


def handle_status():
    state = load_state()
    print("Directive Completeness Validator Status")
    print(f"  Total checks: {len(state['checks'])}")
    print(f"  Missing directives: {len(state['missing_directives'])}")
    print(f"  Incomplete directives: {len(state['incomplete_directives'])}")
    if state["missing_directives"]:
        print("  Missing directives for scripts:")
        for item in state["missing_directives"][-5:]:
            print(f"    - {item}")
    if state["incomplete_directives"]:
        print("  Incomplete directives:")
        for item in state["incomplete_directives"][-5:]:
            print(f"    - {item}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"checks": [], "missing_directives": [], "incomplete_directives": []}))
    print("Directive Completeness Validator: State reset.")
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
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")
    script_name = extract_script_name(command)
    if not script_name:
        sys.exit(0)

    state = load_state()
    keywords = derive_directive_keywords(script_name)

    if not keywords:
        sys.exit(0)

    directive = find_matching_directive(keywords)

    check_entry = {
        "script": script_name,
        "timestamp": datetime.now().isoformat(),
        "keywords": list(keywords),
    }

    if directive is None:
        check_entry["result"] = "no_directive"
        state["checks"].append(check_entry)
        if script_name not in state["missing_directives"]:
            state["missing_directives"].append(script_name)
        save_state(state)
        sys.stderr.write(
            f"[Directive Completeness] WARNING: No matching directive found for {script_name}\n"
            f"  Keywords searched: {', '.join(sorted(keywords))}\n"
            f"  Consider creating directives/{script_name.replace('.py', '.md')}\n"
        )
        sys.exit(0)

    found, missing = check_directive_sections(directive)
    check_entry["directive"] = directive.name
    check_entry["found_sections"] = found
    check_entry["missing_sections"] = missing

    if missing:
        check_entry["result"] = "incomplete"
        state["checks"].append(check_entry)
        entry_str = f"{directive.name} (missing: {', '.join(missing)})"
        if entry_str not in state["incomplete_directives"]:
            state["incomplete_directives"].append(entry_str)
        save_state(state)
        sys.stderr.write(
            f"[Directive Completeness] WARNING: Directive {directive.name} is incomplete\n"
            f"  Found sections: {', '.join(found) if found else '(none)'}\n"
            f"  Missing sections: {', '.join(missing)}\n"
            f"  The directive should have all of: {', '.join(REQUIRED_SECTIONS)}\n"
        )
        sys.exit(0)
    else:
        check_entry["result"] = "complete"
        state["checks"].append(check_entry)
        save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
