#!/usr/bin/env python3
"""
Hook 68: self_anneal_effectiveness_tracker.py (PostToolUse on Bash + PostToolUse on Write)
Tracks whether self-annealing fixes are effective by comparing pre/post success rates.
Dual mode: detect tool_result for PostToolUse.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "anneal_effectiveness.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "annealed_files": {},
        "script_runs_pre": {},
        "script_runs_post": {},
        "anneal_events": [],
        "total_anneals": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_script_name(command):
    """Extract execution script name from command."""
    match = re.search(r'execution/(\w+\.py)', command)
    if match:
        return match.group(1)
    return None


def determine_success(tool_result):
    """Determine if command succeeded from result."""
    if not tool_result:
        return None
    result_str = str(tool_result).lower()
    failure_indicators = [
        "error", "traceback", "exception", "failed",
        "modulenotfounderror", "importerror"
    ]
    for ind in failure_indicators:
        if ind in result_str:
            return False
    return True


def calculate_effectiveness(state):
    """Calculate effectiveness scores for annealed scripts."""
    results = {}
    annealed = state.get("annealed_files", {})
    pre = state.get("script_runs_pre", {})
    post = state.get("script_runs_post", {})

    for filename, info in annealed.items():
        # Derive corresponding script name from the annealed file
        script_base = filename.replace(".md", ".py")

        pre_runs = pre.get(script_base, {"success": 0, "fail": 0})
        post_runs = post.get(script_base, {"success": 0, "fail": 0})

        pre_total = pre_runs.get("success", 0) + pre_runs.get("fail", 0)
        post_total = post_runs.get("success", 0) + post_runs.get("fail", 0)

        pre_rate = (pre_runs.get("success", 0) / pre_total * 100) if pre_total > 0 else None
        post_rate = (post_runs.get("success", 0) / post_total * 100) if post_total > 0 else None

        results[filename] = {
            "pre_success_rate": pre_rate,
            "post_success_rate": post_rate,
            "pre_runs": pre_total,
            "post_runs": post_total,
            "anneal_count": info.get("count", 0)
        }
    return results


def show_status():
    state = load_state()
    effectiveness = calculate_effectiveness(state)
    total = state.get("total_anneals", 0)

    print("=== Self-Anneal Effectiveness Tracker ===")
    print(f"Total anneal events: {total}")
    print(f"Files annealed: {len(state.get('annealed_files', {}))}")

    if effectiveness:
        print("\nEffectiveness by file:")
        for filename, info in effectiveness.items():
            print(f"\n  {filename}:")
            print(f"    Anneal count: {info['anneal_count']}")
            if info['pre_success_rate'] is not None:
                print(f"    Pre-anneal success rate: {info['pre_success_rate']:.0f}% ({info['pre_runs']} runs)")
            else:
                print(f"    Pre-anneal: no data")
            if info['post_success_rate'] is not None:
                print(f"    Post-anneal success rate: {info['post_success_rate']:.0f}% ({info['post_runs']} runs)")
                if info['pre_success_rate'] is not None:
                    diff = info['post_success_rate'] - info['pre_success_rate']
                    direction = "improved" if diff > 0 else "degraded" if diff < 0 else "unchanged"
                    print(f"    Change: {diff:+.0f}% ({direction})")
            else:
                print(f"    Post-anneal: no runs yet")

    events = state.get("anneal_events", [])
    if events:
        print("\nRecent anneal events:")
        for e in events[-5:]:
            print(f"  [{e.get('timestamp', '?')[:19]}] {e.get('file', '?')}")
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
    has_result = "tool_result" in data

    state = load_state()
    now = datetime.now().isoformat()

    # Handle Write events (self-anneal detection)
    if tool_name in ("Write", "write"):
        file_path = tool_input.get("file_path", "")
        is_anneal = False

        # Check if writing to directives/ or execution/
        if "directives/" in file_path or "execution/" in file_path:
            is_anneal = True

        if is_anneal:
            filename = Path(file_path).name
            annealed = state.get("annealed_files", {})
            if filename not in annealed:
                annealed[filename] = {"count": 0, "first_annealed": now}
            annealed[filename]["count"] = annealed[filename].get("count", 0) + 1
            annealed[filename]["last_annealed"] = now
            state["annealed_files"] = annealed
            state["total_anneals"] = state.get("total_anneals", 0) + 1

            # Move any existing pre-anneal stats to "pre" bucket
            script_name = filename.replace(".md", ".py")
            # Reset post-anneal counters for this script
            post = state.get("script_runs_post", {})
            if script_name in post:
                # Move post stats to pre
                pre = state.get("script_runs_pre", {})
                pre[script_name] = post[script_name]
                state["script_runs_pre"] = pre
                post[script_name] = {"success": 0, "fail": 0}
                state["script_runs_post"] = post

            state["anneal_events"] = state.get("anneal_events", [])
            state["anneal_events"].append({"timestamp": now, "file": filename})
            state["anneal_events"] = state["anneal_events"][-100:]

        save_state(state)
        if has_result:
            print(json.dumps({"decision": "ALLOW"}))
        else:
            sys.exit(0)
        return

    # Handle Bash events (script run tracking)
    if tool_name in ("Bash", "bash"):
        command = tool_input.get("command", "")
        script_name = extract_script_name(command)

        if script_name:
            success = determine_success(tool_result)
            annealed = state.get("annealed_files", {})

            # Check if this script (or its directive) was annealed
            was_annealed = (
                script_name in annealed
                or script_name.replace(".py", ".md") in annealed
            )

            if was_annealed and success is not None:
                # Track as post-anneal run
                post = state.get("script_runs_post", {})
                if script_name not in post:
                    post[script_name] = {"success": 0, "fail": 0}
                if success:
                    post[script_name]["success"] = post[script_name].get("success", 0) + 1
                else:
                    post[script_name]["fail"] = post[script_name].get("fail", 0) + 1
                state["script_runs_post"] = post
            elif success is not None:
                # Track as pre-anneal run
                pre = state.get("script_runs_pre", {})
                if script_name not in pre:
                    pre[script_name] = {"success": 0, "fail": 0}
                if success:
                    pre[script_name]["success"] = pre[script_name].get("success", 0) + 1
                else:
                    pre[script_name]["fail"] = pre[script_name].get("fail", 0) + 1
                state["script_runs_pre"] = pre

        save_state(state)
        if has_result:
            print(json.dumps({"decision": "ALLOW"}))
        else:
            sys.exit(0)
        return

    # Default
    if has_result:
        print(json.dumps({"decision": "ALLOW"}))
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
