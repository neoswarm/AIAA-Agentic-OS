#!/usr/bin/env python3
"""
Hook 66: api_cost_estimator.py (PostToolUse on Bash)
Estimates API costs after execution scripts run.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "api_costs.json"

# Cost estimates per script type (USD)
COST_MAP = {
    # Research scripts (Perplexity)
    "research_company_offer.py": 0.005,
    "research_market_deep.py": 0.005,
    "research_prospect_deep.py": 0.005,
    "research_": 0.005,  # prefix match

    # Generation scripts (OpenRouter/Claude)
    "generate_vsl_script.py": 0.03,
    "generate_sales_page.py": 0.03,
    "generate_email_sequence.py": 0.03,
    "generate_blog_post.py": 0.03,
    "generate_linkedin_post.py": 0.02,
    "generate_newsletter.py": 0.03,
    "generate_funnel_copy.py": 0.03,
    "generate_sales_page_copy.py": 0.03,
    "generate_complete_vsl_funnel.py": 0.15,
    "generate_": 0.03,  # prefix match

    # Scraping scripts (Apify)
    "scrape_linkedin_apify.py": 0.05,
    "scrape_": 0.03,  # prefix match

    # Image generation (FAL)
    "generate_image": 0.05,

    # Writing scripts (OpenRouter)
    "write_cold_emails.py": 0.03,
    "write_": 0.03,  # prefix match

    # Other
    "create_google_doc.py": 0.001,
    "send_slack_notification.py": 0.0,
    "validate_emails.py": 0.001,
    "instantly_": 0.001,
    "calendly_": 0.001,
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "session_total": 0.0,
        "by_script": {},
        "runs": [],
        "daily_totals": {}
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def estimate_cost(script_name):
    """Estimate cost for a given script."""
    # Exact match first
    if script_name in COST_MAP:
        return COST_MAP[script_name]
    # Prefix match
    for prefix, cost in COST_MAP.items():
        if prefix.endswith("_") and script_name.startswith(prefix):
            return cost
    return 0.01  # Default estimate for unknown scripts


def extract_script_name(command):
    """Extract execution script name from command."""
    match = re.search(r'execution/(\w+\.py)', command)
    if match:
        return match.group(1)
    return None


def show_status():
    state = load_state()
    session_total = state.get("session_total", 0)
    by_script = state.get("by_script", {})

    print("=== API Cost Estimator ===")
    print(f"\nSession total (estimated): ${session_total:.4f}")
    print(f"Total script runs tracked: {len(state.get('runs', []))}")

    if by_script:
        print("\nCost by script:")
        sorted_scripts = sorted(by_script.items(), key=lambda x: x[1].get("total_cost", 0), reverse=True)
        for name, info in sorted_scripts[:15]:
            runs = info.get("run_count", 0)
            cost = info.get("total_cost", 0)
            print(f"  {name}: ${cost:.4f} ({runs} runs)")

    daily = state.get("daily_totals", {})
    if daily:
        print("\nDaily totals:")
        for date in sorted(daily.keys())[-7:]:
            print(f"  {date}: ${daily[date]:.4f}")

    runs = state.get("runs", [])
    if runs:
        print("\nRecent runs:")
        for r in runs[-5:]:
            print(f"  {r.get('script', '?')}: ${r.get('cost', 0):.4f} ({r.get('timestamp', '?')[:19]})")
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
    today = now[:10]

    cost = estimate_cost(script_name)

    # Update session total
    state["session_total"] = state.get("session_total", 0) + cost

    # Update by script
    by_script = state.get("by_script", {})
    if script_name not in by_script:
        by_script[script_name] = {"run_count": 0, "total_cost": 0}
    by_script[script_name]["run_count"] = by_script[script_name].get("run_count", 0) + 1
    by_script[script_name]["total_cost"] = by_script[script_name].get("total_cost", 0) + cost
    state["by_script"] = by_script

    # Update daily totals
    daily = state.get("daily_totals", {})
    daily[today] = daily.get(today, 0) + cost
    state["daily_totals"] = daily

    # Log run
    run_entry = {
        "timestamp": now,
        "script": script_name,
        "cost": cost
    }
    state["runs"] = state.get("runs", [])
    state["runs"].append(run_entry)
    state["runs"] = state["runs"][-200:]

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
