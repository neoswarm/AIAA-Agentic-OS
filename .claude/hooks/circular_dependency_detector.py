#!/usr/bin/env python3
"""
Hook 96: circular_dependency_detector.py (PreToolUse on Bash)
Purpose: Find circular dependencies in workflow chains.
Logic: Track directive chains (directive A calls script that triggers directive B).
Build dependency graph in state. Warn if circular dependency detected (A->B->C->A).

Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages to user via sys.stderr.write()
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "circular_deps.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "dependency_graph": {},
        "detected_cycles": [],
        "total_checks": 0,
        "last_directive": None,
        "directive_script_map": {}
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def find_cycles(graph):
    """Detect cycles in a directed graph using DFS."""
    cycles = []
    visited = set()
    rec_stack = set()

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path)
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycle_str = " -> ".join(cycle)
                if cycle_str not in cycles:
                    cycles.append(cycle_str)

        path.pop()
        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node, [])

    return cycles


def extract_directive_from_command(command):
    """Extract directive name from a bash command that reads a directive."""
    match = re.search(r'directives/([a-zA-Z0-9_-]+)\.md', command)
    if match:
        return match.group(1)
    return None


def extract_script_from_command(command):
    """Extract execution script name from a bash command."""
    match = re.search(r'execution/([a-zA-Z0-9_-]+\.py)', command)
    if match:
        return match.group(1)
    return None


def map_script_to_directive(script_name):
    """Attempt to map a script name back to a directive."""
    base = script_name.replace(".py", "")
    # Common prefixes to strip
    for prefix in ["generate_", "run_", "execute_", "create_", "deploy_"]:
        if base.startswith(prefix):
            base = base[len(prefix):]
            break
    return base


def show_status():
    state = load_state()
    graph = state.get("dependency_graph", {})
    cycles = state.get("detected_cycles", [])
    script_map = state.get("directive_script_map", {})

    print("=== Circular Dependency Detector ===")
    print(f"Total checks: {state.get('total_checks', 0)}")
    print(f"Nodes in graph: {len(graph)}")
    print(f"Last directive: {state.get('last_directive', 'None')}")

    if graph:
        print("\nDependency graph:")
        for node, deps in sorted(graph.items()):
            if deps:
                print(f"  {node} -> {', '.join(deps)}")
            else:
                print(f"  {node} -> (no deps)")

    if script_map:
        print(f"\nDirective-to-script mappings: {len(script_map)}")
        for directive, scripts in sorted(script_map.items())[:10]:
            print(f"  {directive}: {', '.join(scripts)}")

    if cycles:
        print(f"\nDETECTED CYCLES ({len(cycles)}):")
        for cycle in cycles:
            print(f"  CYCLE: {cycle}")
    else:
        print("\nNo circular dependencies detected.")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Circular dependency detector state reset.")
    sys.exit(0)


def main():
    if "--status" in sys.argv:
        show_status()
    if "--reset" in sys.argv:
        reset_state()

    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only care about Bash commands
    if tool_name not in ("Bash", "bash"):
        sys.exit(0)

    command = tool_input.get("command", "")
    if not command:
        sys.exit(0)

    state = load_state()
    state["total_checks"] = state.get("total_checks", 0) + 1

    # Track directive reads
    directive = extract_directive_from_command(command)
    script = extract_script_from_command(command)

    updated = False

    if directive:
        state["last_directive"] = directive
        if directive not in state["dependency_graph"]:
            state["dependency_graph"][directive] = []
        updated = True

    if script:
        # Map script execution back to a directive dependency
        target_directive = map_script_to_directive(script)
        current_directive = state.get("last_directive")

        if current_directive and target_directive != current_directive:
            deps = state["dependency_graph"].get(current_directive, [])
            if target_directive not in deps:
                deps.append(target_directive)
                state["dependency_graph"][current_directive] = deps

            # Track the mapping
            script_map = state.get("directive_script_map", {})
            if current_directive not in script_map:
                script_map[current_directive] = []
            if script not in script_map[current_directive]:
                script_map[current_directive].append(script)
            state["directive_script_map"] = script_map

        # Ensure target exists in graph
        if target_directive not in state["dependency_graph"]:
            state["dependency_graph"][target_directive] = []
        updated = True

    # Check for cycles
    if updated:
        cycles = find_cycles(state["dependency_graph"])
        state["detected_cycles"] = cycles

        if cycles:
            cycle_msg = "\n".join(f"    {c}" for c in cycles)
            sys.stderr.write(
                f"[Circular Dependency Detector] WARNING: Circular dependencies detected!\n"
                f"{cycle_msg}\n"
                f"  This may cause infinite workflow loops.\n"
                f"  Review the dependency chain and break the cycle.\n"
            )

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
