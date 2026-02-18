#!/usr/bin/env python3
"""
Hook 60: workflow_success_predictor.py (PreToolUse on Bash)
Before execution scripts, checks historical success rate and warns if low.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "workflow_predictions.json"
PATTERNS_FILE = STATE_DIR / "workflow_patterns.json"

MIN_RUNS_FOR_PREDICTION = 3
LOW_SUCCESS_THRESHOLD = 50  # percent


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"predictions": [], "first_runs": 0, "low_success_warnings": 0}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def load_patterns():
    """Load workflow patterns from hook #18's state file."""
    try:
        if PATTERNS_FILE.exists():
            return json.loads(PATTERNS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def extract_script_name(command):
    """Extract execution script name from command."""
    match = re.search(r'execution/(\w+\.py)', command)
    if match:
        return match.group(1)
    # Also match python3 execution/script.py
    match = re.search(r'python3?\s+(?:\S+/)?execution/(\w+\.py)', command)
    if match:
        return match.group(1)
    return None


def show_status():
    state = load_state()
    patterns = load_patterns()
    print("=== Workflow Success Predictor ===")
    print(f"Predictions made: {len(state.get('predictions', []))}")
    print(f"First-run scripts: {state.get('first_runs', 0)}")
    print(f"Low success warnings: {state.get('low_success_warnings', 0)}")

    # Show script success rates from patterns
    scripts = patterns.get("scripts", patterns.get("workflows", {}))
    if isinstance(scripts, dict):
        print("\nScript success rates (from workflow_patterns.json):")
        for name, info in sorted(scripts.items()):
            if isinstance(info, dict):
                total = info.get("total", info.get("run_count", 0))
                success = info.get("success", info.get("success_count", 0))
                if total > 0:
                    rate = (success / total) * 100
                    print(f"  {name}: {rate:.0f}% ({success}/{total} runs)")
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
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Bash", "bash"):
        sys.exit(0)

    command = tool_input.get("command", "")
    script_name = extract_script_name(command)
    if not script_name:
        sys.exit(0)

    state = load_state()
    patterns = load_patterns()
    now = datetime.now().isoformat()

    # Look up success rate in patterns
    scripts = patterns.get("scripts", patterns.get("workflows", {}))
    script_info = None
    if isinstance(scripts, dict):
        script_info = scripts.get(script_name)

    prediction = {
        "timestamp": now,
        "script": script_name,
        "warning": False,
        "message": ""
    }

    if script_info is None or not isinstance(script_info, dict):
        state["first_runs"] = state.get("first_runs", 0) + 1
        prediction["message"] = "First run of this script"
        sys.stderr.write(f"[success-predictor] First run of {script_name}. No historical data.\n")
    else:
        total = script_info.get("total", script_info.get("run_count", 0))
        success = script_info.get("success", script_info.get("success_count", 0))

        if total >= MIN_RUNS_FOR_PREDICTION:
            rate = (success / total) * 100 if total > 0 else 0
            if rate < LOW_SUCCESS_THRESHOLD:
                prediction["warning"] = True
                prediction["message"] = f"{rate:.0f}% success rate over {total} runs"
                state["low_success_warnings"] = state.get("low_success_warnings", 0) + 1
                sys.stderr.write(
                    f"[success-predictor] {script_name} has a {rate:.0f}% success rate "
                    f"over {total} runs. Recent errors may recur.\n"
                )
            else:
                prediction["message"] = f"{rate:.0f}% success rate over {total} runs (OK)"
        else:
            prediction["message"] = f"Only {total} prior runs (need {MIN_RUNS_FOR_PREDICTION} for prediction)"

    state["predictions"].append(prediction)
    state["predictions"] = state["predictions"][-100:]
    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
