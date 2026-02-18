#!/usr/bin/env python3
"""
Hook 27: Multi-Directive Chain Tracker (PostToolUse on Read)

When a directive file is read, scan its content for references to other directives:
- Look for patterns: "See also:", "Related Directives:", "directives/", "Follow directive:"
- Log the dependency chain to .tmp/hooks/directive_chains.json
- Track: {parent_directive: [child_directives]}
- When status checked, show the full chain for the current workflow

ALLOW always. Informational tracking only.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "directive_chains.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"chains": {}, "read_order": [], "stats": {"total_reads": 0, "chains_found": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_directive_references(content):
    """Extract references to other directives from content."""
    references = set()

    # Pattern: directives/some_name.md
    for match in re.findall(r'directives/([a-zA-Z0-9_\-]+\.md)', content):
        references.add(match)

    # Pattern: directives/some_name (without .md)
    for match in re.findall(r'directives/([a-zA-Z0-9_\-]+)(?:\s|$|,|\))', content):
        if not match.endswith('.md'):
            references.add(match + '.md')

    # Pattern: "See also:" followed by directive names
    see_also = re.findall(r'[Ss]ee\s+[Aa]lso:\s*(.+)', content)
    for line in see_also:
        for name in re.findall(r'([a-zA-Z0-9_\-]+(?:_[a-zA-Z0-9_\-]+)+)', line):
            if len(name) > 5:
                references.add(name if name.endswith('.md') else name + '.md')

    # Pattern: "Related Directives:" section
    related = re.findall(r'[Rr]elated\s+[Dd]irectives?:\s*(.+?)(?:\n\n|\n#|\Z)', content, re.DOTALL)
    for block in related:
        for name in re.findall(r'([a-zA-Z0-9_\-]+(?:_[a-zA-Z0-9_\-]+)+)', block):
            if len(name) > 5:
                references.add(name if name.endswith('.md') else name + '.md')

    # Pattern: "Follow directive:" or "Use directive:"
    follow = re.findall(r'(?:[Ff]ollow|[Uu]se)\s+directive:\s*(.+)', content)
    for line in follow:
        for name in re.findall(r'([a-zA-Z0-9_\-]+(?:_[a-zA-Z0-9_\-]+)+)', line):
            if len(name) > 5:
                references.add(name if name.endswith('.md') else name + '.md')

    # Pattern: "Next step:" or "Then run:"
    next_step = re.findall(r'(?:[Nn]ext\s+step|[Tt]hen\s+run):\s*(.+)', content)
    for line in next_step:
        for name in re.findall(r'([a-zA-Z0-9_\-]+(?:_[a-zA-Z0-9_\-]+)+)', line):
            if len(name) > 5:
                references.add(name if name.endswith('.md') else name + '.md')

    return list(references)


def build_chain(chains, start_directive, visited=None):
    """Recursively build the full dependency chain."""
    if visited is None:
        visited = set()
    if start_directive in visited:
        return []
    visited.add(start_directive)

    children = chains.get(start_directive, [])
    full_chain = list(children)

    for child in children:
        grandchildren = build_chain(chains, child, visited)
        full_chain.extend(grandchildren)

    return full_chain


def handle_status():
    state = load_state()
    print("=== Multi-Directive Chain Tracker Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"Total directive reads: {stats.get('total_reads', 0)}")
    print(f"Chains found: {stats.get('chains_found', 0)}")

    chains = state.get("chains", {})
    if chains:
        print(f"\nDirective dependency chains:")
        for parent, children in chains.items():
            print(f"  {parent}")
            for child in children:
                print(f"    -> {child}")
                # Show grandchildren
                grandchildren = chains.get(child, [])
                for gc in grandchildren:
                    print(f"       -> {gc}")
    else:
        print("\nNo directive chains tracked yet.")

    read_order = state.get("read_order", [])
    if read_order:
        print(f"\nRecent directive reads (last 10):")
        for entry in read_order[-10:]:
            print(f"  {entry.get('directive', '?')} at {entry.get('timestamp', '?')}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Directive chain tracker state reset.")
    else:
        print("No state file to reset.")


def main():
    if "--status" in sys.argv:
        handle_status()
        return
    if "--reset" in sys.argv:
        handle_reset()
        return

    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Read":
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")

    # Only track directive files
    if "directives/" not in file_path or not file_path.endswith(".md"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    directive_name = Path(file_path).name

    # Record the read
    state["read_order"].append({
        "directive": directive_name,
        "path": file_path,
        "timestamp": datetime.now().isoformat(),
    })
    # Keep last 100 reads
    state["read_order"] = state["read_order"][-100:]
    state["stats"]["total_reads"] = state["stats"].get("total_reads", 0) + 1

    # Extract references from tool_result (the file content)
    tool_result = data.get("tool_result", "")
    if tool_result:
        references = extract_directive_references(str(tool_result))
        # Remove self-references
        references = [r for r in references if r != directive_name]

        if references:
            state["chains"][directive_name] = references
            state["stats"]["chains_found"] = state["stats"].get("chains_found", 0) + 1

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
