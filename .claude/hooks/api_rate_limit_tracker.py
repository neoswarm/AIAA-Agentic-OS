#!/usr/bin/env python3
"""
Hook 33: API Rate Limit Tracker (PostToolUse on Bash)

Track API-calling execution scripts to prevent rate limiting:
- After research_*.py runs: log Perplexity API call
- After generate_*.py runs: log OpenRouter API call
- After scrape_*.py runs: log Apify API call
- Track calls per minute per API
- If >10 calls/minute to same API: warn about rate limiting

State: .tmp/hooks/api_rate_tracker.json. ALLOW always.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "api_rate_tracker.json"

# Script prefix -> API name mapping
SCRIPT_API_MAP = [
    (r"research_\w+\.py", "perplexity"),
    (r"generate_\w+\.py", "openrouter"),
    (r"write_\w+\.py", "openrouter"),
    (r"scrape_\w+\.py", "apify"),
    (r"gmaps_\w+\.py", "apify"),
    (r"send_slack\w*\.py", "slack"),
    (r"create_google_doc\w*\.py", "google"),
    (r"(?:read|append_to|update)_sheet\w*\.py", "google"),
    (r"instantly_\w*\.py", "instantly"),
    (r"upload_leads_\w*\.py", "instantly"),
    (r"validate_emails\w*\.py", "email_validation"),
    (r"generate_image\w*\.py", "fal"),
    (r"generate_thumbnail\w*\.py", "fal"),
    (r"deploy_\w+\.py", "railway"),
]

# Rate limits per API (calls per minute threshold for warning)
RATE_LIMITS = {
    "perplexity": 10,
    "openrouter": 15,
    "apify": 5,
    "slack": 20,
    "google": 10,
    "instantly": 10,
    "email_validation": 10,
    "fal": 5,
    "railway": 5,
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"api_calls": {}, "warnings": [], "stats": {"total_calls": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def identify_api(command):
    """Identify which API a command uses."""
    script_match = re.search(r'(?:python3?\s+)?(?:execution/)?(\w+\.py)', command)
    if not script_match:
        return None

    script_name = script_match.group(1)
    for pattern, api_name in SCRIPT_API_MAP:
        if re.match(pattern, script_name):
            return api_name

    return None


def count_recent_calls(api_calls, api_name, window_minutes=1):
    """Count calls to an API within the time window."""
    now = datetime.now()
    cutoff = now - timedelta(minutes=window_minutes)
    calls = api_calls.get(api_name, [])
    recent = [c for c in calls if datetime.fromisoformat(c) > cutoff]
    return len(recent)


def cleanup_old_calls(api_calls, max_age_minutes=10):
    """Remove calls older than max_age_minutes."""
    now = datetime.now()
    cutoff = now - timedelta(minutes=max_age_minutes)
    for api_name in api_calls:
        api_calls[api_name] = [
            c for c in api_calls[api_name]
            if datetime.fromisoformat(c) > cutoff
        ]
    return api_calls


def handle_status():
    state = load_state()
    print("=== API Rate Limit Tracker Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"Total API calls tracked: {stats.get('total_calls', 0)}")

    api_calls = state.get("api_calls", {})
    if api_calls:
        print(f"\nAPI call rates (last minute):")
        for api_name, calls in api_calls.items():
            recent = count_recent_calls(api_calls, api_name)
            limit = RATE_LIMITS.get(api_name, 10)
            status = "HIGH" if recent > limit else "OK"
            print(f"  [{status}] {api_name}: {recent} calls/min (limit: {limit})")
            print(f"    Total recorded: {len(calls)}")
    else:
        print("\nNo API calls tracked yet.")

    warnings = state.get("warnings", [])
    if warnings:
        print(f"\nRecent rate warnings:")
        for w in warnings[-5:]:
            print(f"  {w}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("API rate limit tracker state reset.")
    else:
        print("No state file to reset.")


def main():
    if "--status" in sys.argv:
        handle_status()
        return
    if "--reset" in sys.argv:
        handle_reset()
        return

    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Bash":
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    api_name = identify_api(command)

    if not api_name:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()

    # Record the call
    if api_name not in state["api_calls"]:
        state["api_calls"][api_name] = []
    state["api_calls"][api_name].append(now)
    state["stats"]["total_calls"] = state["stats"].get("total_calls", 0) + 1

    # Cleanup old entries
    state["api_calls"] = cleanup_old_calls(state["api_calls"])

    # Check rate
    recent_count = count_recent_calls(state["api_calls"], api_name)
    limit = RATE_LIMITS.get(api_name, 10)

    if recent_count > limit:
        warning = (
            f"High API call rate for {api_name}: {recent_count} calls in last minute "
            f"(threshold: {limit}). Risk of rate limiting."
        )
        state["warnings"].append(warning)
        state["warnings"] = state["warnings"][-20:]
        save_state(state)
        print(json.dumps({"decision": "ALLOW", "reason": warning}))
    else:
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
