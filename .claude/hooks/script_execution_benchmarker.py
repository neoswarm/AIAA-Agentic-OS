#!/usr/bin/env python3
"""
Hook 115: script_execution_benchmarker.py (PostToolUse on Bash)
Purpose: Benchmark execution script performance.
Logic: Track execution start/end times for each script. Store benchmarks in state.
Warn if a script takes significantly longer than its average.
Track P50, P90, P99 times.

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
STATE_FILE = STATE_DIR / "script_benchmarks.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "scripts": {},
        "pending_starts": {},
        "total_benchmarked": 0,
        "slowest_runs": []
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_script_name(command):
    """Extract script name from command."""
    match = re.search(r'execution/([a-zA-Z0-9_-]+\.py)', command)
    if match:
        return match.group(1)
    return None


def calculate_percentiles(times):
    """Calculate P50, P90, P99 from a list of times."""
    if not times:
        return {"p50": 0, "p90": 0, "p99": 0}

    sorted_times = sorted(times)
    n = len(sorted_times)

    def percentile(p):
        idx = int(n * p / 100)
        idx = min(idx, n - 1)
        return sorted_times[idx]

    return {
        "p50": round(percentile(50), 2),
        "p90": round(percentile(90), 2),
        "p99": round(percentile(99), 2)
    }


def show_status():
    state = load_state()
    scripts = state.get("scripts", {})

    print("=== Script Execution Benchmarker ===")
    print(f"Total benchmarked runs: {state.get('total_benchmarked', 0)}")
    print(f"Scripts tracked: {len(scripts)}")

    if scripts:
        print("\nPerformance by script:")
        sorted_scripts = sorted(scripts.items(),
                                key=lambda x: x[1].get("run_count", 0),
                                reverse=True)

        for name, data in sorted_scripts[:15]:
            run_count = data.get("run_count", 0)
            times = data.get("run_times", [])
            percentiles = calculate_percentiles(times)
            avg = sum(times) / len(times) if times else 0

            print(f"\n  {name} ({run_count} runs)")
            print(f"    Avg: {avg:.1f}s | P50: {percentiles['p50']}s | P90: {percentiles['p90']}s | P99: {percentiles['p99']}s")

            if times:
                last_time = times[-1]
                if avg > 0 and last_time > avg * 2:
                    print(f"    WARNING: Last run ({last_time:.1f}s) was {last_time/avg:.1f}x slower than average")

    slowest = state.get("slowest_runs", [])
    if slowest:
        print(f"\nSlowest runs ever (top {min(5, len(slowest))}):")
        for run in sorted(slowest, key=lambda x: x.get("duration", 0), reverse=True)[:5]:
            name = run.get("script", "?")
            dur = run.get("duration", 0)
            ts = run.get("timestamp", "?")[:19]
            print(f"  {name}: {dur:.1f}s ({ts})")

    pending = state.get("pending_starts", {})
    if pending:
        print(f"\nPending (started, no result yet): {len(pending)}")
        for script, info in pending.items():
            print(f"  {script} (started: {info.get('start_time', '?')[:19]})")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Script execution benchmarker state reset.")
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
    is_post = "tool_result" in data

    if tool_name not in ("Bash", "bash"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    script_name = extract_script_name(command)
    if not script_name:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()
    now_ts = time.time()

    # PostToolUse - record completion and calculate duration
    pending = state.get("pending_starts", {})

    if script_name in pending:
        # We have a start time - calculate duration
        start_ts = pending[script_name].get("start_timestamp", now_ts)
        duration = now_ts - start_ts

        # Update script benchmarks
        scripts = state.get("scripts", {})
        if script_name not in scripts:
            scripts[script_name] = {"run_count": 0, "run_times": []}

        scripts[script_name]["run_count"] += 1
        scripts[script_name]["run_times"].append(round(duration, 2))
        scripts[script_name]["run_times"] = scripts[script_name]["run_times"][-50:]
        scripts[script_name]["last_run"] = now
        state["scripts"] = scripts

        state["total_benchmarked"] = state.get("total_benchmarked", 0) + 1

        # Track slowest runs
        slowest = state.get("slowest_runs", [])
        slowest.append({
            "script": script_name,
            "duration": round(duration, 2),
            "timestamp": now
        })
        slowest.sort(key=lambda x: x["duration"], reverse=True)
        state["slowest_runs"] = slowest[:20]

        # Check if significantly slower than average
        times = scripts[script_name]["run_times"]
        if len(times) > 3:
            avg = sum(times[:-1]) / len(times[:-1])
            if avg > 0 and duration > avg * 3:
                output = {
                    "decision": "ALLOW",
                    "reason": f"[Benchmark] {script_name} took {duration:.1f}s ({duration/avg:.1f}x slower than avg of {avg:.1f}s)"
                }
                del pending[script_name]
                state["pending_starts"] = pending
                save_state(state)
                print(json.dumps(output))
                return

        del pending[script_name]
        state["pending_starts"] = pending
    else:
        # First time seeing this script - record start
        pending[script_name] = {
            "start_time": now,
            "start_timestamp": now_ts
        }
        state["pending_starts"] = pending

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
