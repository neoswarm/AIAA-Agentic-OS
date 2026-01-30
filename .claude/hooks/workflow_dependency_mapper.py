#!/usr/bin/env python3
"""
Hook 67: workflow_dependency_mapper.py (PostToolUse on Read)
When directives are read, parses them for workflow dependencies and builds a dependency graph.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "workflow_deps.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"dependency_graph": {}, "recent_directives": [], "total_parsed": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_dependencies(content):
    """Parse directive content for references to other files."""
    deps = {
        "execution_scripts": [],
        "directives": [],
        "skill_bibles": [],
    }

    if not content:
        return deps

    # Find execution script references
    for match in re.finditer(r'execution/(\w+\.py)', content):
        script = match.group(1)
        if script not in deps["execution_scripts"]:
            deps["execution_scripts"].append(script)

    # Find directive references
    for match in re.finditer(r'directives/([a-zA-Z0-9_-]+\.md)', content):
        directive = match.group(1)
        if directive not in deps["directives"]:
            deps["directives"].append(directive)

    # Find skill bible references
    for match in re.finditer(r'(?:skills/)?SKILL_BIBLE_([a-zA-Z0-9_-]+)\.md', content):
        skill = match.group(1)
        if skill not in deps["skill_bibles"]:
            deps["skill_bibles"].append(skill)

    # Also look for skill bible references by name pattern
    for match in re.finditer(r'SKILL_BIBLE_([a-zA-Z0-9_]+)', content):
        skill = match.group(1)
        if skill not in deps["skill_bibles"]:
            deps["skill_bibles"].append(skill)

    return deps


def extract_directive_name(file_path):
    """Extract directive name from file path."""
    match = re.search(r'directives/(.+?)\.md', file_path)
    if match:
        return match.group(1)
    return None


def show_status():
    state = load_state()
    graph = state.get("dependency_graph", {})
    print("=== Workflow Dependency Mapper ===")
    print(f"Directives parsed: {state.get('total_parsed', 0)}")
    print(f"Directives with deps mapped: {len(graph)}")

    recent = state.get("recent_directives", [])
    if recent:
        print("\nRecently loaded directives and their dependencies:")
        for name in recent[-5:]:
            deps = graph.get(name, {})
            print(f"\n  {name}:")
            scripts = deps.get("execution_scripts", [])
            if scripts:
                print(f"    Scripts: {', '.join(scripts[:5])}")
            directives = deps.get("directives", [])
            if directives:
                print(f"    Directives: {', '.join(directives[:5])}")
            skills = deps.get("skill_bibles", [])
            if skills:
                print(f"    Skill Bibles: {', '.join(skills[:5])}")
            if not scripts and not directives and not skills:
                print(f"    No dependencies found")

    # Show most connected directives
    if graph:
        print("\nMost connected directives:")
        scored = []
        for name, deps in graph.items():
            total_deps = (
                len(deps.get("execution_scripts", []))
                + len(deps.get("directives", []))
                + len(deps.get("skill_bibles", []))
            )
            scored.append((name, total_deps))
        scored.sort(key=lambda x: x[1], reverse=True)
        for name, count in scored[:5]:
            print(f"  {name}: {count} dependencies")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("State reset.")
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
    tool_result = data.get("tool_result", "")

    if tool_name not in ("Read", "read"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    if "directives/" not in file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    directive_name = extract_directive_name(file_path)
    if not directive_name:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()
    state["total_parsed"] = state.get("total_parsed", 0) + 1

    # Parse dependencies from the content
    content = str(tool_result) if tool_result else ""
    deps = extract_dependencies(content)

    # Update graph
    graph = state.get("dependency_graph", {})
    graph[directive_name] = {
        "execution_scripts": deps["execution_scripts"],
        "directives": deps["directives"],
        "skill_bibles": deps["skill_bibles"],
        "last_parsed": now
    }
    state["dependency_graph"] = graph

    # Track recent directives
    recent = state.get("recent_directives", [])
    if directive_name not in recent:
        recent.append(directive_name)
    state["recent_directives"] = recent[-20:]

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
