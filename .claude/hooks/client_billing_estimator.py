#!/usr/bin/env python3
"""
Hook 102: client_billing_estimator.py (PostToolUse on Bash)
Purpose: Estimate API costs per client based on script executions.
Logic: After execution scripts run, estimate token usage based on script type.
Map costs to client context if loaded. Track cumulative costs per client in state.

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
STATE_FILE = STATE_DIR / "client_billing.json"

# Cost estimates per script type (USD) - based on typical token usage
SCRIPT_COSTS = {
    "generate_complete_vsl_funnel": 0.15,
    "generate_vsl_script": 0.03,
    "generate_sales_page": 0.03,
    "generate_email_sequence": 0.03,
    "generate_blog_post": 0.03,
    "generate_linkedin_post": 0.02,
    "generate_newsletter": 0.03,
    "generate_funnel_copy": 0.03,
    "write_cold_emails": 0.03,
    "research_company_offer": 0.005,
    "research_market_deep": 0.005,
    "research_prospect_deep": 0.005,
    "scrape_linkedin_apify": 0.05,
    "create_google_doc": 0.001,
    "send_slack_notification": 0.0,
    "validate_emails": 0.001,
    "generate_image": 0.05,
}

# Prefix-based fallback costs
PREFIX_COSTS = {
    "generate_": 0.03,
    "research_": 0.005,
    "scrape_": 0.03,
    "write_": 0.03,
    "create_": 0.01,
    "send_": 0.001,
    "deploy_": 0.001,
    "validate_": 0.001,
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "clients": {},
        "unattributed_cost": 0.0,
        "total_cost": 0.0,
        "active_client": None,
        "runs": [],
        "daily_totals": {}
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def estimate_cost(script_name):
    """Estimate cost for a given script."""
    base = script_name.replace(".py", "")
    if base in SCRIPT_COSTS:
        return SCRIPT_COSTS[base]
    for prefix, cost in PREFIX_COSTS.items():
        if base.startswith(prefix):
            return cost
    return 0.01


def extract_script_name(command):
    """Extract execution script name from command."""
    match = re.search(r'execution/([a-zA-Z0-9_-]+\.py)', command)
    if match:
        return match.group(1)
    return None


def detect_active_client(command):
    """Try to detect client from command arguments."""
    # Check for --client arg
    match = re.search(r'--client[=\s]+["\']?([a-zA-Z0-9_-]+)', command)
    if match:
        return match.group(1)

    # Check for --company arg
    match = re.search(r'--company[=\s]+["\']?([a-zA-Z0-9_\s]+?)(?:["\']|$|\s--)', command)
    if match:
        return match.group(1).strip().replace(" ", "_").lower()

    return None


def show_status():
    state = load_state()
    clients = state.get("clients", {})

    print("=== Client Billing Estimator ===")
    print(f"Total estimated cost: ${state.get('total_cost', 0):.4f}")
    print(f"Unattributed cost: ${state.get('unattributed_cost', 0):.4f}")
    print(f"Active client: {state.get('active_client', 'None')}")
    print(f"Total runs: {len(state.get('runs', []))}")

    if clients:
        print("\nCost by client:")
        sorted_clients = sorted(clients.items(),
                                key=lambda x: x[1].get("total_cost", 0),
                                reverse=True)
        for name, cdata in sorted_clients:
            total = cdata.get("total_cost", 0)
            runs = cdata.get("run_count", 0)
            scripts = cdata.get("scripts_used", {})
            print(f"\n  {name}: ${total:.4f} ({runs} runs)")
            if scripts:
                for s, info in sorted(scripts.items(), key=lambda x: x[1].get("cost", 0), reverse=True)[:5]:
                    print(f"    {s}: ${info.get('cost', 0):.4f} ({info.get('count', 0)}x)")

    daily = state.get("daily_totals", {})
    if daily:
        print("\nDaily totals (last 7 days):")
        for date in sorted(daily.keys())[-7:]:
            print(f"  {date}: ${daily[date]:.4f}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Client billing estimator state reset.")
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
        # Check if loading client context to track active client
        if "clients/" in command:
            match = re.search(r'clients/([a-zA-Z0-9_-]+)/', command)
            if match:
                state = load_state()
                state["active_client"] = match.group(1)
                save_state(state)
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()
    today = now[:10]

    cost = estimate_cost(script_name)

    # Determine client
    client = detect_active_client(command) or state.get("active_client")

    # Update totals
    state["total_cost"] = state.get("total_cost", 0) + cost

    if client:
        clients = state.get("clients", {})
        if client not in clients:
            clients[client] = {"total_cost": 0, "run_count": 0, "scripts_used": {}, "first_seen": now}
        clients[client]["total_cost"] = clients[client].get("total_cost", 0) + cost
        clients[client]["run_count"] = clients[client].get("run_count", 0) + 1

        scripts_used = clients[client].get("scripts_used", {})
        if script_name not in scripts_used:
            scripts_used[script_name] = {"count": 0, "cost": 0}
        scripts_used[script_name]["count"] += 1
        scripts_used[script_name]["cost"] = scripts_used[script_name].get("cost", 0) + cost
        clients[client]["scripts_used"] = scripts_used
        state["clients"] = clients
    else:
        state["unattributed_cost"] = state.get("unattributed_cost", 0) + cost

    # Daily total
    daily = state.get("daily_totals", {})
    daily[today] = daily.get(today, 0) + cost
    state["daily_totals"] = daily

    # Log run
    state["runs"] = state.get("runs", [])
    state["runs"].append({
        "timestamp": now,
        "script": script_name,
        "cost": cost,
        "client": client or "unattributed"
    })
    state["runs"] = state["runs"][-200:]

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
