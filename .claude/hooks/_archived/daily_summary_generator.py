#!/usr/bin/env python3
"""
Hook 69: daily_summary_generator.py (PostToolUse on Bash)
Accumulates data for a daily summary. Only updates on execution script runs.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "daily_summary.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "scripts_run": 0,
        "scripts_succeeded": 0,
        "scripts_failed": 0,
        "deliverables_created": 0,
        "errors_encountered": 0,
        "directives_used": [],
        "skill_bibles_loaded": [],
        "estimated_api_cost": 0.0,
        "first_activity": "",
        "last_activity": "",
        "script_details": []
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def reset_for_new_day(state):
    """Reset state if the date has changed."""
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("date") != today:
        return {
            "date": today,
            "scripts_run": 0,
            "scripts_succeeded": 0,
            "scripts_failed": 0,
            "deliverables_created": 0,
            "errors_encountered": 0,
            "directives_used": [],
            "skill_bibles_loaded": [],
            "estimated_api_cost": 0.0,
            "first_activity": "",
            "last_activity": "",
            "script_details": []
        }
    return state


def extract_script_name(command):
    """Extract execution script name from command."""
    match = re.search(r'execution/(\w+\.py)', command)
    if match:
        return match.group(1)
    return None


def determine_success(tool_result):
    """Determine if command succeeded."""
    if not tool_result:
        return None
    result_str = str(tool_result).lower()
    failure_indicators = [
        "error", "traceback", "exception", "failed",
        "modulenotfounderror", "importerror", "syntaxerror"
    ]
    for ind in failure_indicators:
        if ind in result_str:
            return False
    return True


def estimate_cost(script_name):
    """Quick cost estimate based on script type."""
    if script_name.startswith("research_"):
        return 0.005
    if script_name.startswith("generate_complete"):
        return 0.15
    if script_name.startswith("generate_"):
        return 0.03
    if script_name.startswith("scrape_"):
        return 0.03
    if script_name.startswith("write_"):
        return 0.03
    return 0.01


def format_duration(first, last):
    """Format duration between two ISO timestamps."""
    try:
        t1 = datetime.fromisoformat(first)
        t2 = datetime.fromisoformat(last)
        delta = t2 - t1
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except (ValueError, TypeError):
        return "unknown"


def show_status():
    state = load_state()
    state = reset_for_new_day(state)

    print("=== Daily Summary ===")
    print(f"Date: {state.get('date', 'unknown')}")

    first = state.get("first_activity", "")
    last = state.get("last_activity", "")
    if first and last:
        duration = format_duration(first, last)
        print(f"Session duration: {duration}")
        print(f"  First activity: {first[:19]}")
        print(f"  Last activity:  {last[:19]}")

    print(f"\nScripts run:     {state.get('scripts_run', 0)}")
    print(f"  Succeeded:     {state.get('scripts_succeeded', 0)}")
    print(f"  Failed:        {state.get('scripts_failed', 0)}")
    print(f"Deliverables:    {state.get('deliverables_created', 0)}")
    print(f"Errors:          {state.get('errors_encountered', 0)}")
    print(f"Est. API cost:   ${state.get('estimated_api_cost', 0):.4f}")

    directives = state.get("directives_used", [])
    if directives:
        print(f"\nDirectives used ({len(directives)}):")
        for d in directives[:10]:
            print(f"  - {d}")

    skills = state.get("skill_bibles_loaded", [])
    if skills:
        print(f"\nSkill bibles loaded ({len(skills)}):")
        for s in skills[:10]:
            print(f"  - {s}")

    details = state.get("script_details", [])
    if details:
        print(f"\nScript execution log:")
        for d in details[-10:]:
            status = "OK" if d.get("success") else "FAIL"
            print(f"  [{status}] {d.get('script', '?')} ({d.get('timestamp', '?')[:19]})")

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

    if tool_name not in ("Bash", "bash"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    script_name = extract_script_name(command)

    # Only track execution script runs
    if not script_name:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state = reset_for_new_day(state)
    now = datetime.now().isoformat()

    # Track timing
    if not state.get("first_activity"):
        state["first_activity"] = now
    state["last_activity"] = now

    # Track script run
    state["scripts_run"] = state.get("scripts_run", 0) + 1

    success = determine_success(tool_result)
    if success is True:
        state["scripts_succeeded"] = state.get("scripts_succeeded", 0) + 1
    elif success is False:
        state["scripts_failed"] = state.get("scripts_failed", 0) + 1
        state["errors_encountered"] = state.get("errors_encountered", 0) + 1

    # Track deliverables
    if "create_google_doc" in script_name or "send_slack" in script_name:
        if success is not False:
            state["deliverables_created"] = state.get("deliverables_created", 0) + 1

    # Estimate API cost
    cost = estimate_cost(script_name)
    state["estimated_api_cost"] = state.get("estimated_api_cost", 0) + cost

    # Log script detail
    detail = {
        "timestamp": now,
        "script": script_name,
        "success": success is True
    }
    state["script_details"] = state.get("script_details", [])
    state["script_details"].append(detail)
    state["script_details"] = state["script_details"][-100:]

    # Try to load directive and skill bible info from other state files
    try:
        coverage_file = STATE_DIR / "directive_coverage.json"
        if coverage_file.exists():
            coverage = json.loads(coverage_file.read_text())
            used_directives = list(coverage.get("directives_used", {}).keys())
            state["directives_used"] = used_directives
    except (json.JSONDecodeError, OSError):
        pass

    try:
        skill_file = STATE_DIR / "skill_bible_usage.json"
        if skill_file.exists():
            skill_data = json.loads(skill_file.read_text())
            used_skills = list(skill_data.get("skill_bibles", {}).keys())
            state["skill_bibles_loaded"] = used_skills
    except (json.JSONDecodeError, OSError):
        pass

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
