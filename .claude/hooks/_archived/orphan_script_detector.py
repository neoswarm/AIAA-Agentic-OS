#!/usr/bin/env python3
"""
Hook 98: orphan_script_detector.py (PostToolUse on Read)
Purpose: When browsing execution scripts, flag ones with no matching directive.
Logic: When reading execution/*.py, check if corresponding directive exists.
Use naming conventions to map (e.g., generate_vsl_funnel.py -> vsl_funnel*.md).
Track orphan scripts in state.

Protocol:
  - PostToolUse: prints JSON to stdout {"decision": "ALLOW"}
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime
from fnmatch import fnmatch

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "orphan_scripts.json"
DIRECTIVES_DIR = Path("directives")


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "orphan_scripts": {},
        "matched_scripts": {},
        "total_scanned": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_script_name(file_path):
    """Extract script name from file path."""
    match = re.search(r'execution/([a-zA-Z0-9_-]+\.py)', file_path)
    if match:
        return match.group(1)
    return None


def generate_directive_candidates(script_name):
    """Generate possible directive filenames from a script name."""
    base = script_name.replace(".py", "")
    candidates = []

    # Direct match
    candidates.append(f"{base}.md")

    # Strip common prefixes
    prefixes_to_strip = [
        "generate_", "create_", "run_", "execute_", "deploy_",
        "send_", "write_", "build_", "process_", "validate_",
        "scrape_", "research_", "parse_", "convert_", "check_",
        "update_", "sync_", "fetch_", "upload_", "download_"
    ]

    stripped = base
    for prefix in prefixes_to_strip:
        if base.startswith(prefix):
            stripped = base[len(prefix):]
            candidates.append(f"{stripped}.md")
            candidates.append(f"{stripped}_orchestrator.md")
            candidates.append(f"{stripped}_workflow.md")
            break

    # Add orchestrator/workflow variants
    candidates.append(f"{base}_orchestrator.md")
    candidates.append(f"{base}_workflow.md")

    # Add with "complete_" prefix stripped
    if base.startswith("generate_complete_"):
        inner = base[len("generate_complete_"):]
        candidates.append(f"{inner}.md")
        candidates.append(f"{inner}_orchestrator.md")

    return list(set(candidates))


def find_matching_directive(script_name):
    """Search for a matching directive file."""
    if not DIRECTIVES_DIR.exists():
        return None

    candidates = generate_directive_candidates(script_name)
    base = script_name.replace(".py", "")

    # Strip prefix for fuzzy matching
    stripped_base = base
    for prefix in ["generate_", "create_", "run_", "execute_", "deploy_",
                    "send_", "write_", "build_", "process_"]:
        if base.startswith(prefix):
            stripped_base = base[len(prefix):]
            break

    try:
        directive_files = [f.name for f in DIRECTIVES_DIR.iterdir() if f.suffix == ".md"]
    except OSError:
        return None

    # Exact candidate match
    for candidate in candidates:
        if candidate in directive_files:
            return candidate

    # Fuzzy match: directive contains the stripped script name
    for df in directive_files:
        df_base = df.replace(".md", "")
        if stripped_base in df_base or df_base in stripped_base:
            return df

    # Partial keyword match (at least 2 meaningful words match)
    script_words = set(stripped_base.split("_"))
    script_words -= {"the", "a", "an", "to", "for", "and", "or", "of"}
    if len(script_words) >= 2:
        for df in directive_files:
            df_words = set(df.replace(".md", "").split("_"))
            overlap = script_words & df_words
            if len(overlap) >= 2:
                return df

    return None


def show_status():
    state = load_state()
    orphans = state.get("orphan_scripts", {})
    matched = state.get("matched_scripts", {})

    print("=== Orphan Script Detector ===")
    print(f"Total scripts scanned: {state.get('total_scanned', 0)}")
    print(f"Matched scripts: {len(matched)}")
    print(f"Orphan scripts: {len(orphans)}")

    if orphans:
        print("\nOrphan scripts (no matching directive):")
        for name, info in sorted(orphans.items()):
            candidates = info.get("candidates_checked", [])
            last_seen = info.get("last_scanned", "?")[:19]
            print(f"  {name} (scanned: {last_seen})")
            if candidates:
                print(f"    Checked for: {', '.join(candidates[:5])}")

    if matched:
        print(f"\nMatched scripts (last {min(10, len(matched))}):")
        sorted_matched = sorted(matched.items(),
                                key=lambda x: x[1].get("last_scanned", ""),
                                reverse=True)
        for name, info in sorted_matched[:10]:
            directive = info.get("matching_directive", "?")
            print(f"  {name} -> {directive}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Orphan script detector state reset.")
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

    # Only act on Read tool
    if tool_name not in ("Read", "read"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    if "execution/" not in file_path or not file_path.endswith(".py"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    script_name = extract_script_name(file_path)
    if not script_name:
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Skip utility scripts
    utility_patterns = ["__init__", "utils", "helpers", "common", "config", "setup"]
    base = script_name.replace(".py", "")
    if any(pat in base for pat in utility_patterns):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_scanned"] = state.get("total_scanned", 0) + 1
    now = datetime.now().isoformat()

    # Find matching directive
    matching = find_matching_directive(script_name)
    candidates = generate_directive_candidates(script_name)

    if matching:
        state["matched_scripts"][script_name] = {
            "matching_directive": matching,
            "last_scanned": now
        }
        state.get("orphan_scripts", {}).pop(script_name, None)
    else:
        state["orphan_scripts"][script_name] = {
            "candidates_checked": candidates[:5],
            "last_scanned": now
        }
        state.get("matched_scripts", {}).pop(script_name, None)

    save_state(state)

    if not matching:
        output = {
            "decision": "ALLOW",
            "reason": f"[Orphan Script] '{script_name}' has no matching directive. Consider creating directives/{candidates[0]} or linking it to an existing directive."
        }
        print(json.dumps(output))
    else:
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
