#!/usr/bin/env python3
"""
Hook 113: workflow_completion_tracker.py (PostToolUse on Bash)
Purpose: Track workflow completion rates vs abandonment.
Logic: Detect workflow start (directive load) and completion (delivery step).
Track completion rate, average phases completed before abandonment,
most common failure points.

Protocol:
  - PostToolUse: prints JSON to stdout {"decision": "ALLOW"}
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "workflow_completions.json"

# Workflow lifecycle stages
STAGE_PATTERNS = {
    "start": [r'directives/\w+\.md', r'--help', r'ls\s+directives/'],
    "research": [r'research_', r'perplexity'],
    "generation": [r'generate_', r'write_'],
    "quality": [r'validate', r'quality', r'check'],
    "delivery": [r'create_google_doc', r'send_slack', r'send_email', r'upload'],
}

# Completion = delivery stage reached
COMPLETION_STAGE = "delivery"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "active_workflows": {},
        "completed": [],
        "abandoned": [],
        "total_started": 0,
        "total_completed": 0,
        "total_abandoned": 0,
        "failure_points": {},
        "stage_reach_counts": {}
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def detect_stage(command):
    """Detect workflow stage from command."""
    for stage, patterns in STAGE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return stage
    return None


def detect_workflow_name(command):
    """Extract workflow name from command."""
    match = re.search(r'execution/([a-zA-Z0-9_-]+)\.py', command)
    if match:
        return match.group(1)
    match = re.search(r'directives/([a-zA-Z0-9_-]+)\.md', command)
    if match:
        return match.group(1)
    return None


def check_abandoned_workflows(state, timeout_minutes=60):
    """Check for workflows that seem abandoned."""
    active = state.get("active_workflows", {})
    now = datetime.now()
    abandoned = []

    for wf_id, wf in list(active.items()):
        last_activity = datetime.fromisoformat(wf.get("last_activity", now.isoformat()))
        elapsed = (now - last_activity).total_seconds() / 60

        if elapsed > timeout_minutes:
            # Mark as abandoned
            abandoned.append(wf_id)
            last_stage = wf.get("stages_reached", ["start"])[-1]

            state["abandoned"] = state.get("abandoned", [])
            state["abandoned"].append({
                "workflow_id": wf_id,
                "workflow_name": wf.get("name", "unknown"),
                "stages_reached": wf.get("stages_reached", []),
                "last_stage": last_stage,
                "started_at": wf.get("started_at"),
                "abandoned_at": now.isoformat(),
                "elapsed_minutes": elapsed
            })
            state["abandoned"] = state["abandoned"][-100:]
            state["total_abandoned"] = state.get("total_abandoned", 0) + 1

            # Track failure point
            failure_points = state.get("failure_points", {})
            failure_points[last_stage] = failure_points.get(last_stage, 0) + 1
            state["failure_points"] = failure_points

    for wf_id in abandoned:
        del active[wf_id]
    state["active_workflows"] = active


def show_status():
    state = load_state()
    total_started = state.get("total_started", 0)
    total_completed = state.get("total_completed", 0)
    total_abandoned = state.get("total_abandoned", 0)

    print("=== Workflow Completion Tracker ===")
    print(f"Total started: {total_started}")
    print(f"Total completed: {total_completed}")
    print(f"Total abandoned: {total_abandoned}")

    if total_started > 0:
        rate = (total_completed / total_started) * 100
        print(f"Completion rate: {rate:.1f}%")

    active = state.get("active_workflows", {})
    if active:
        print(f"\nActive workflows ({len(active)}):")
        for wf_id, wf in active.items():
            stages = wf.get("stages_reached", [])
            name = wf.get("name", "unknown")
            print(f"  {wf_id}: {name} (stages: {', '.join(stages)})")

    failure_points = state.get("failure_points", {})
    if failure_points:
        print("\nCommon failure/abandonment points:")
        for stage, count in sorted(failure_points.items(), key=lambda x: x[1], reverse=True):
            print(f"  {stage}: {count} times")

    stage_counts = state.get("stage_reach_counts", {})
    if stage_counts:
        print("\nStage reach counts:")
        for stage, count in sorted(stage_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {stage}: {count}")

    completed = state.get("completed", [])
    if completed:
        print(f"\nRecent completions (last {min(5, len(completed))}):")
        for c in completed[-5:]:
            name = c.get("workflow_name", "?")
            ts = c.get("completed_at", "?")[:19]
            print(f"  {name} ({ts})")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Workflow completion tracker state reset.")
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
    if not command:
        print(json.dumps({"decision": "ALLOW"}))
        return

    stage = detect_stage(command)
    if not stage:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()
    workflow_name = detect_workflow_name(command) or "unknown"

    # Check for abandoned workflows periodically
    check_abandoned_workflows(state)

    active = state.get("active_workflows", {})

    if stage == "start":
        # New workflow
        wf_id = f"{workflow_name}_{now[:19].replace(':', '-')}"
        active[wf_id] = {
            "name": workflow_name,
            "started_at": now,
            "last_activity": now,
            "stages_reached": ["start"]
        }
        state["active_workflows"] = active
        state["total_started"] = state.get("total_started", 0) + 1
    else:
        # Update existing workflow
        # Find the most recent active workflow
        latest_wf = None
        latest_time = ""
        for wf_id, wf in active.items():
            if wf.get("last_activity", "") >= latest_time:
                latest_time = wf["last_activity"]
                latest_wf = wf_id

        if latest_wf:
            wf = active[latest_wf]
            stages = wf.get("stages_reached", [])
            if stage not in stages:
                stages.append(stage)
            wf["stages_reached"] = stages
            wf["last_activity"] = now

            # Track stage reach counts
            stage_counts = state.get("stage_reach_counts", {})
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            state["stage_reach_counts"] = stage_counts

            # Check for completion
            if stage == COMPLETION_STAGE:
                state["completed"] = state.get("completed", [])
                state["completed"].append({
                    "workflow_id": latest_wf,
                    "workflow_name": wf.get("name", "unknown"),
                    "stages_reached": stages,
                    "started_at": wf.get("started_at"),
                    "completed_at": now
                })
                state["completed"] = state["completed"][-100:]
                state["total_completed"] = state.get("total_completed", 0) + 1
                del active[latest_wf]

    state["active_workflows"] = active
    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
