#!/usr/bin/env python3
"""
Hook 22: Cold Email Workflow Enforcer (PostToolUse on Bash)

Enforces cold email workflow ordering:
- write_cold_emails.py should have research done first
- personalize_emails_ai.py should have base emails first
- validate_emails.py should come before sending
- upload_leads_instantly.py should have validated emails first

Tracks state in .tmp/hooks/cold_email_state.json. Warns if steps out of order.
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "cold_email_state.json"

COLD_EMAIL_SCRIPTS = {
    "research_company_offer.py": {
        "step": "research",
        "requires": [],
        "description": "Research company/offer"
    },
    "research_prospect_deep.py": {
        "step": "prospect_research",
        "requires": [],
        "description": "Deep prospect research"
    },
    "scrape_linkedin_apify.py": {
        "step": "lead_scraping",
        "requires": [],
        "description": "LinkedIn lead scraping"
    },
    "scrape_google_maps.py": {
        "step": "lead_scraping",
        "requires": [],
        "description": "Google Maps lead scraping"
    },
    "write_cold_emails.py": {
        "step": "email_writing",
        "requires": ["research"],
        "description": "Cold email writing"
    },
    "personalize_emails_ai.py": {
        "step": "email_personalization",
        "requires": ["email_writing"],
        "description": "AI email personalization"
    },
    "validate_emails.py": {
        "step": "email_validation",
        "requires": ["lead_scraping"],
        "description": "Email validation"
    },
    "upload_leads_instantly.py": {
        "step": "lead_upload",
        "requires": ["email_validation"],
        "description": "Upload leads to Instantly"
    },
    "send_cold_emails.py": {
        "step": "sending",
        "requires": ["email_writing", "email_validation"],
        "description": "Send cold emails"
    },
    "full_campaign_pipeline.py": {
        "step": "full_pipeline",
        "requires": [],
        "description": "Full campaign pipeline (all-in-one)"
    }
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"campaigns": {}, "global_steps": [], "warnings": []}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_campaign_name(command):
    """Try to extract campaign/company name from command arguments."""
    patterns = [
        r'--company\s+"([^"]+)"',
        r"--company\s+'([^']+)'",
        r'--company\s+(\S+)',
        r'--campaign\s+"([^"]+)"',
        r"--campaign\s+'([^']+)'",
        r'--sender\s+"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            return match.group(1).lower().replace(" ", "_")
    return "default"


def check_prerequisites(script_name, campaign_name, state):
    """Check if prerequisites for a script are met."""
    if script_name not in COLD_EMAIL_SCRIPTS:
        return []

    config = COLD_EMAIL_SCRIPTS[script_name]
    missing = []
    completed = state.get("campaigns", {}).get(campaign_name, {}).get("completed_steps", [])
    global_steps = state.get("global_steps", [])
    all_completed = set(completed + global_steps)

    for req in config["requires"]:
        if req not in all_completed:
            missing.append(req)

    return missing


def record_step(script_name, campaign_name, state):
    """Record a completed workflow step."""
    if script_name not in COLD_EMAIL_SCRIPTS:
        return state

    config = COLD_EMAIL_SCRIPTS[script_name]
    step = config["step"]

    if campaign_name not in state.get("campaigns", {}):
        state.setdefault("campaigns", {})[campaign_name] = {
            "completed_steps": [],
            "history": []
        }

    campaign = state["campaigns"][campaign_name]
    if step not in campaign["completed_steps"]:
        campaign["completed_steps"].append(step)

    if step not in state.get("global_steps", []):
        state.setdefault("global_steps", []).append(step)

    campaign.setdefault("history", []).append({
        "step": step,
        "script": script_name,
        "timestamp": datetime.now().isoformat()
    })

    return state


def handle_status():
    state = load_state()
    print("=== Cold Email Workflow Enforcer Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    campaigns = state.get("campaigns", {})
    if not campaigns:
        print("No cold email campaigns tracked yet.")
    else:
        for name, data in campaigns.items():
            print(f"\nCampaign: {name}")
            print(f"  Completed steps: {', '.join(data.get('completed_steps', []))}")
            history = data.get("history", [])
            if history:
                print(f"  Last activity: {history[-1].get('timestamp', 'unknown')}")

    global_steps = state.get("global_steps", [])
    if global_steps:
        print(f"\nGlobal completed steps: {', '.join(global_steps)}")

    warnings = state.get("warnings", [])
    if warnings:
        print(f"\nRecent warnings ({len(warnings)}):")
        for w in warnings[-5:]:
            print(f"  - {w}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Cold email workflow state reset.")
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

    # Check if this is a cold-email-related script
    detected_script = None
    for script_name in COLD_EMAIL_SCRIPTS:
        if script_name in command:
            detected_script = script_name
            break

    if not detected_script:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    campaign_name = extract_campaign_name(command)

    # Check prerequisites
    missing = check_prerequisites(detected_script, campaign_name, state)

    # Record the step
    state = record_step(detected_script, campaign_name, state)

    if missing:
        warning = (
            f"Cold email workflow order: '{detected_script}' ran but prerequisite steps "
            f"not detected: {', '.join(missing)}. Recommended order: research -> "
            f"email_writing -> personalization, lead_scraping -> validation -> upload/sending"
        )
        state.setdefault("warnings", []).append(warning)
        save_state(state)
        print(json.dumps({"decision": "ALLOW", "reason": warning}))
    else:
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
