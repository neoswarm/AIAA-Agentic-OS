#!/usr/bin/env python3
"""
Hook 99: memory_usage_estimator.py (PreToolUse on Bash)
Purpose: Warn when scripts might use excessive memory.
Logic: Check if command involves processing large files, batch operations,
or known memory-heavy scripts. Estimate memory impact and warn if problematic.

Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages to user via sys.stderr.write()
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
import os
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "memory_estimates.json"

# Memory thresholds in MB
WARN_THRESHOLD_MB = 512
BLOCK_THRESHOLD_MB = 2048

# Known memory-heavy patterns and their estimated MB usage
HEAVY_PATTERNS = {
    r'--batch[-_]size\s+(\d+)': lambda m: int(m.group(1)) * 10,
    r'--all[-_]clients': lambda m: 500,
    r'--bulk': lambda m: 300,
    r'--no[-_]limit': lambda m: 1000,
    r'--full[-_]scan': lambda m: 800,
}

# Scripts with known memory profiles (name_pattern -> estimated MB)
SCRIPT_MEMORY_MAP = {
    "generate_complete_vsl_funnel": 200,
    "research_market_deep": 150,
    "research_company_offer": 100,
    "generate_vsl_script": 120,
    "generate_sales_page": 120,
    "generate_email_sequence": 100,
    "scrape_linkedin": 250,
    "generate_blog_post": 100,
    "generate_newsletter": 80,
    "write_cold_emails": 80,
    "validate_emails": 50,
    "convert_n8n": 60,
    "parse_vtt": 40,
}

# File size thresholds that indicate large processing
LARGE_FILE_INDICATORS = [
    r'--input\s+\S+\.csv',
    r'--input\s+\S+\.json',
    r'--file\s+\S+\.csv',
    r'xargs.*-P\s*(\d+)',  # parallel processing
    r'cat\s+.*\|\s*while',  # streaming large files
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "warnings_issued": 0,
        "blocks_issued": 0,
        "estimates": [],
        "peak_estimate_mb": 0,
        "total_checks": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def estimate_memory(command):
    """Estimate memory usage in MB for a given command."""
    total_mb = 0
    reasons = []

    # Check script memory profiles
    for script_pattern, mb in SCRIPT_MEMORY_MAP.items():
        if script_pattern in command:
            total_mb += mb
            reasons.append(f"{script_pattern}: ~{mb}MB")
            break

    # Check heavy patterns
    for pattern, calc_fn in HEAVY_PATTERNS.items():
        match = re.search(pattern, command)
        if match:
            mb = calc_fn(match)
            total_mb += mb
            reasons.append(f"Pattern '{match.group(0)}': ~{mb}MB")

    # Check for large file indicators
    for pattern in LARGE_FILE_INDICATORS:
        match = re.search(pattern, command)
        if match:
            total_mb += 100
            reasons.append(f"Large file processing: ~100MB")

    # Check for piped commands (cumulative memory)
    pipe_count = command.count("|")
    if pipe_count >= 3:
        overhead = pipe_count * 20
        total_mb += overhead
        reasons.append(f"Piped commands ({pipe_count} pipes): ~{overhead}MB overhead")

    # Check for multiple python processes
    python_count = len(re.findall(r'python3?\s+', command))
    if python_count > 1:
        overhead = (python_count - 1) * 80
        total_mb += overhead
        reasons.append(f"Multiple Python processes ({python_count}): ~{overhead}MB")

    # If no specific estimate, use a small default for execution scripts
    if total_mb == 0 and "execution/" in command:
        total_mb = 50
        reasons.append("Default execution script estimate: ~50MB")

    return total_mb, reasons


def show_status():
    state = load_state()
    print("=== Memory Usage Estimator ===")
    print(f"Total checks: {state.get('total_checks', 0)}")
    print(f"Warnings issued: {state.get('warnings_issued', 0)}")
    print(f"Blocks issued: {state.get('blocks_issued', 0)}")
    print(f"Peak estimate: {state.get('peak_estimate_mb', 0)}MB")
    print(f"Warn threshold: {WARN_THRESHOLD_MB}MB")
    print(f"Block threshold: {BLOCK_THRESHOLD_MB}MB")

    estimates = state.get("estimates", [])
    if estimates:
        print(f"\nRecent estimates (last {min(10, len(estimates))}):")
        for entry in estimates[-10:]:
            mb = entry.get("estimated_mb", 0)
            script = entry.get("script", "unknown")
            level = entry.get("level", "ok")
            ts = entry.get("timestamp", "?")[:19]
            print(f"  [{level.upper()}] {script}: {mb}MB ({ts})")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Memory usage estimator state reset.")
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
    if not command:
        sys.exit(0)

    # Only estimate for execution-related commands
    if "execution/" not in command and "python" not in command:
        sys.exit(0)

    state = load_state()
    state["total_checks"] = state.get("total_checks", 0) + 1
    now = datetime.now().isoformat()

    estimated_mb, reasons = estimate_memory(command)

    # Determine level
    if estimated_mb >= BLOCK_THRESHOLD_MB:
        level = "block"
    elif estimated_mb >= WARN_THRESHOLD_MB:
        level = "warn"
    else:
        level = "ok"

    # Extract script name for tracking
    script_match = re.search(r'execution/([a-zA-Z0-9_-]+\.py)', command)
    script_name = script_match.group(1) if script_match else "unknown"

    # Update state
    entry = {
        "timestamp": now,
        "script": script_name,
        "estimated_mb": estimated_mb,
        "level": level,
        "reasons": reasons
    }
    state["estimates"] = state.get("estimates", [])
    state["estimates"].append(entry)
    state["estimates"] = state["estimates"][-100:]

    if estimated_mb > state.get("peak_estimate_mb", 0):
        state["peak_estimate_mb"] = estimated_mb

    if level == "block":
        state["blocks_issued"] = state.get("blocks_issued", 0) + 1
        save_state(state)
        reason_text = "\n".join(f"    - {r}" for r in reasons)
        sys.stderr.write(
            f"[Memory Estimator] BLOCKED: Estimated {estimated_mb}MB exceeds {BLOCK_THRESHOLD_MB}MB limit.\n"
            f"  Command: {command[:100]}...\n"
            f"  Breakdown:\n{reason_text}\n"
            f"  Consider: reducing batch size, processing in chunks, or limiting scope.\n"
        )
        sys.exit(2)

    if level == "warn":
        state["warnings_issued"] = state.get("warnings_issued", 0) + 1
        save_state(state)
        reason_text = "\n".join(f"    - {r}" for r in reasons)
        sys.stderr.write(
            f"[Memory Estimator] WARNING: Estimated {estimated_mb}MB approaches threshold.\n"
            f"  Breakdown:\n{reason_text}\n"
            f"  Monitor memory usage during execution.\n"
        )

    save_state(state)
    sys.exit(0)


if __name__ == "__main__":
    main()
