#!/usr/bin/env python3
"""
Hook 118: workflow_bottleneck_detector.py (PostToolUse on Bash)
Purpose: Find slowest steps in workflows.
Logic: Track time between phase transitions. Identify bottleneck phases (slowest
steps). Store bottleneck data per workflow type. Suggest optimization targets.

Protocol:
  - PostToolUse: prints JSON to stdout {"decision": "ALLOW"}
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
import time
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "workflow_bottlenecks.json"

# Workflow step detection
STEP_PATTERNS = {
    "research": [r'research_', r'perplexity'],
    "generation": [r'generate_', r'write_cold'],
    "formatting": [r'format_', r'template_'],
    "validation": [r'validate_', r'quality_', r'check_'],
    "delivery": [r'create_google_doc', r'send_slack', r'send_email'],
    "scraping": [r'scrape_', r'apify'],
    "deployment": [r'railway', r'deploy_'],
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "current_step": None,
        "step_start_time": None,
        "step_durations": {},
        "workflow_steps": [],
        "bottlenecks": {},
        "total_steps": 0,
        "optimization_suggestions": []
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def detect_step(command):
    """Detect workflow step from command."""
    for step, patterns in STEP_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return step
    return None


def extract_workflow_type(command):
    """Extract workflow type from command."""
    if "vsl" in command.lower():
        return "vsl_funnel"
    if "cold_email" in command.lower():
        return "cold_email"
    if "blog" in command.lower():
        return "blog_post"
    if "linkedin" in command.lower():
        return "linkedin"
    if "research" in command.lower():
        return "research"
    return "general"


def identify_bottleneck(step_durations):
    """Identify the bottleneck step from duration data."""
    if not step_durations:
        return None, 0

    # Find step with highest average duration
    bottleneck = None
    max_avg = 0

    for step, durations in step_durations.items():
        if durations:
            avg = sum(durations) / len(durations)
            if avg > max_avg:
                max_avg = avg
                bottleneck = step

    return bottleneck, max_avg


def generate_suggestions(step_durations):
    """Generate optimization suggestions based on bottleneck data."""
    suggestions = []
    for step, durations in step_durations.items():
        if not durations:
            continue
        avg = sum(durations) / len(durations)
        if avg > 60:  # More than 60 seconds
            if step == "research":
                suggestions.append(f"Research step avg {avg:.0f}s - consider caching research results")
            elif step == "generation":
                suggestions.append(f"Generation step avg {avg:.0f}s - consider simpler prompts or smaller models")
            elif step == "scraping":
                suggestions.append(f"Scraping step avg {avg:.0f}s - consider batch processing or pre-fetching")
            elif step == "delivery":
                suggestions.append(f"Delivery step avg {avg:.0f}s - check API latency")
            else:
                suggestions.append(f"{step} step avg {avg:.0f}s - review for optimization")
    return suggestions


def show_status():
    state = load_state()
    step_durations = state.get("step_durations", {})
    bottlenecks = state.get("bottlenecks", {})

    print("=== Workflow Bottleneck Detector ===")
    print(f"Total steps tracked: {state.get('total_steps', 0)}")
    print(f"Current step: {state.get('current_step', 'None')}")

    if step_durations:
        print("\nStep performance:")
        for step, durations in sorted(step_durations.items()):
            if not durations:
                continue
            avg = sum(durations) / len(durations)
            min_d = min(durations)
            max_d = max(durations)
            count = len(durations)
            print(f"\n  {step} ({count} runs)")
            print(f"    Avg: {avg:.1f}s | Min: {min_d:.1f}s | Max: {max_d:.1f}s")

        # Identify overall bottleneck
        bottleneck, max_avg = identify_bottleneck(step_durations)
        if bottleneck:
            print(f"\n  BOTTLENECK: {bottleneck} ({max_avg:.1f}s avg)")

    if bottlenecks:
        print("\nBottlenecks by workflow type:")
        for wf_type, bn_data in sorted(bottlenecks.items()):
            step = bn_data.get("step", "?")
            avg = bn_data.get("avg_duration", 0)
            print(f"  {wf_type}: {step} ({avg:.1f}s avg)")

    suggestions = state.get("optimization_suggestions", [])
    if not suggestions:
        suggestions = generate_suggestions(step_durations)
    if suggestions:
        print("\nOptimization suggestions:")
        for s in suggestions:
            print(f"  - {s}")

    recent_steps = state.get("workflow_steps", [])
    if recent_steps:
        print(f"\nRecent steps (last {min(10, len(recent_steps))}):")
        for s in recent_steps[-10:]:
            ts = s.get("timestamp", "?")[:19]
            step = s.get("step", "?")
            dur = s.get("duration", None)
            dur_str = f" ({dur:.1f}s)" if dur is not None else ""
            print(f"  [{ts}] {step}{dur_str}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Workflow bottleneck detector state reset.")
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

    if tool_name not in ("Bash", "bash"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    step = detect_step(command)

    if not step:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()
    now_ts = time.time()
    state["total_steps"] = state.get("total_steps", 0) + 1

    previous_step = state.get("current_step")
    previous_start = state.get("step_start_time")

    # Calculate duration of previous step
    duration = None
    if previous_step and previous_start and previous_step != step:
        duration = now_ts - previous_start
        step_durations = state.get("step_durations", {})
        if previous_step not in step_durations:
            step_durations[previous_step] = []
        step_durations[previous_step].append(round(duration, 2))
        step_durations[previous_step] = step_durations[previous_step][-30:]
        state["step_durations"] = step_durations

    # Update current step
    state["current_step"] = step
    state["step_start_time"] = now_ts

    # Log step
    step_entry = {
        "timestamp": now,
        "step": step,
        "duration": round(duration, 2) if duration else None,
        "workflow_type": extract_workflow_type(command)
    }
    state["workflow_steps"] = state.get("workflow_steps", [])
    state["workflow_steps"].append(step_entry)
    state["workflow_steps"] = state["workflow_steps"][-100:]

    # Update bottlenecks per workflow type
    wf_type = extract_workflow_type(command)
    step_durations = state.get("step_durations", {})
    bottleneck, max_avg = identify_bottleneck(step_durations)
    if bottleneck:
        bottlenecks = state.get("bottlenecks", {})
        bottlenecks[wf_type] = {
            "step": bottleneck,
            "avg_duration": round(max_avg, 2),
            "updated_at": now
        }
        state["bottlenecks"] = bottlenecks

    # Generate suggestions
    state["optimization_suggestions"] = generate_suggestions(step_durations)

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
