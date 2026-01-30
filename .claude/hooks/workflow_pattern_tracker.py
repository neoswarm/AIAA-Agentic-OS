#!/usr/bin/env python3
"""
Hook 18: Workflow Pattern Tracker
Type: PostToolUse on Bash tool
Tier: Passive (always allows, tracks patterns)

After any bash command containing 'python3 execution/', tracks workflow
usage patterns including execution counts, last run time, success rates,
daily counts, and most-used scripts.

Protocol:
  - Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {...}, "tool_result": "..."}
  - Prints JSON to stdout: {"decision": "ALLOW"}
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


STATE_DIR = Path("/Users/lucasnolan/Agentic OS/.tmp/hooks")
PATTERNS_FILE = STATE_DIR / "workflow_patterns.json"


def load_patterns():
    """Load workflow pattern data."""
    try:
        if PATTERNS_FILE.exists():
            with open(PATTERNS_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "scripts": {},
        "daily_counts": {},
        "total_executions": 0,
    }


def save_patterns(data):
    """Save workflow pattern data."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(PATTERNS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def extract_script_name(command: str) -> str:
    """Extract script filename from command."""
    match = re.search(r'python3?\s+(?:.*?/)?execution/(\S+\.py)', command)
    if match:
        return match.group(1)
    return "unknown.py"


def is_execution_script(command: str) -> bool:
    """Check if command runs an execution script."""
    return "python3 execution/" in command or "python execution/" in command


def detect_success(tool_result: str) -> bool:
    """Detect if execution was successful."""
    if not tool_result:
        return True

    result_str = str(tool_result)

    # Check for explicit exit code
    exit_match = re.search(r'exit\s+code[:\s]+(\d+)', result_str, re.IGNORECASE)
    if exit_match and int(exit_match.group(1)) != 0:
        return False

    # Check for error indicators
    error_indicators = ["Traceback", "Error:", "Exception:", "FAILED"]
    for indicator in error_indicators:
        if indicator in result_str:
            return False

    return True


def prune_daily_counts(daily_counts: dict) -> dict:
    """Keep only the last 30 days of daily counts."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    return {k: v for k, v in daily_counts.items() if k >= cutoff}


def get_top_scripts(scripts: dict, n: int = 5) -> list:
    """Get top N most-used scripts."""
    items = [(name, info.get("count", 0)) for name, info in scripts.items()]
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:n]


def check_status():
    """Show workflow pattern summary."""
    print("Workflow Pattern Tracker - Status")
    print("=" * 50)
    data = load_patterns()
    scripts = data.get("scripts", {})
    daily = data.get("daily_counts", {})
    total = data.get("total_executions", 0)

    print(f"\nTotal executions tracked: {total}")
    print(f"Unique scripts tracked: {len(scripts)}")

    # Top 5 most used
    top = get_top_scripts(scripts, 5)
    if top:
        print(f"\nTop 5 Most-Used Workflows:")
        for i, (name, count) in enumerate(top, 1):
            info = scripts[name]
            rate = info.get("success_rate", 0)
            last = info.get("last_run", "?")[:19]
            print(f"  {i}. {name}: {count} runs ({rate:.0f}% success) - last: {last}")

    # Per-script success rates
    if scripts:
        print(f"\nAll Script Success Rates:")
        for name, info in sorted(scripts.items()):
            count = info.get("count", 0)
            rate = info.get("success_rate", 0)
            print(f"  {name}: {count} runs, {rate:.0f}% success")

    # Daily activity (last 7 days)
    if daily:
        print(f"\nDaily Activity (last 7 days):")
        today = datetime.now(timezone.utc).date()
        for i in range(6, -1, -1):
            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            count = daily.get(day, 0)
            bar = "#" * min(count, 40)
            print(f"  {day}: {count:3d} {bar}")

    sys.exit(0)


def check_reset():
    """Clear all pattern data."""
    print("Workflow Pattern Tracker - Reset")
    if PATTERNS_FILE.exists():
        os.remove(PATTERNS_FILE)
        print("Pattern data cleared.")
    else:
        print("No pattern file to clear.")
    sys.exit(0)


def main():
    # Handle CLI flags
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            check_status()
        elif sys.argv[1] == "--reset":
            check_reset()

    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")
    tool_result = data.get("tool_result", "")

    # Only track execution scripts
    if not is_execution_script(command):
        print(json.dumps({"decision": "ALLOW"}))
        sys.exit(0)

    script_name = extract_script_name(command)
    success = detect_success(str(tool_result))
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # Load and update patterns
    patterns = load_patterns()

    # Update script entry
    scripts = patterns.setdefault("scripts", {})
    if script_name not in scripts:
        scripts[script_name] = {
            "count": 0,
            "successes": 0,
            "failures": 0,
            "success_rate": 0.0,
            "last_run": "",
            "first_run": now.isoformat(),
        }

    entry = scripts[script_name]
    entry["count"] += 1
    entry["last_run"] = now.isoformat()
    if success:
        entry["successes"] = entry.get("successes", 0) + 1
    else:
        entry["failures"] = entry.get("failures", 0) + 1

    total_runs = entry.get("successes", 0) + entry.get("failures", 0)
    if total_runs > 0:
        entry["success_rate"] = (entry.get("successes", 0) / total_runs) * 100

    # Update daily counts
    daily = patterns.setdefault("daily_counts", {})
    daily[today] = daily.get(today, 0) + 1
    patterns["daily_counts"] = prune_daily_counts(daily)

    # Update total
    patterns["total_executions"] = patterns.get("total_executions", 0) + 1

    save_patterns(patterns)

    print(json.dumps({"decision": "ALLOW"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
