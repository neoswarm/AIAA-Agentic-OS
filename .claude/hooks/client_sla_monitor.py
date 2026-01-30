#!/usr/bin/env python3
"""
Hook 103: client_sla_monitor.py (PostToolUse on Bash)
Purpose: Track delivery timelines against expected SLAs.
Logic: When a client workflow starts (client context loaded), start timer.
Track progress through phases. Warn if approaching SLA deadline.
Default SLA: 24 hours for standard deliverables.

Protocol:
  - PostToolUse: prints JSON to stdout {"decision": "ALLOW"}
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "client_sla.json"

# SLA defaults in hours by deliverable type
SLA_HOURS = {
    "vsl_funnel": 24,
    "vsl_script": 12,
    "sales_page": 12,
    "email_sequence": 12,
    "cold_email": 8,
    "blog_post": 8,
    "linkedin_post": 4,
    "newsletter": 8,
    "research": 6,
    "proposal": 16,
    "meeting_prep": 2,
    "default": 24,
}

# Workflow phase indicators
PHASE_INDICATORS = {
    "research": ["research_company", "research_market", "research_prospect"],
    "generation": ["generate_", "write_"],
    "review": ["quality", "review", "validate"],
    "delivery": ["create_google_doc", "send_slack", "send_email"],
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "active_workflows": {},
        "completed_workflows": [],
        "sla_breaches": [],
        "total_workflows": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def detect_workflow_type(command):
    """Detect workflow type from command."""
    for wf_type in SLA_HOURS:
        if wf_type in command.lower():
            return wf_type
    return None


def detect_phase(command):
    """Detect current workflow phase from command."""
    for phase, indicators in PHASE_INDICATORS.items():
        for indicator in indicators:
            if indicator in command.lower():
                return phase
    return None


def detect_client(command):
    """Detect client from command context."""
    match = re.search(r'clients/([a-zA-Z0-9_-]+)/', command)
    if match:
        return match.group(1)
    match = re.search(r'--company[=\s]+["\']?([a-zA-Z0-9_\s]+?)(?:["\']|$|\s--)', command)
    if match:
        return match.group(1).strip().replace(" ", "_").lower()
    return None


def check_sla_status(workflow):
    """Check if workflow is within SLA."""
    start_time = datetime.fromisoformat(workflow["start_time"])
    sla_hours = workflow.get("sla_hours", 24)
    deadline = start_time + timedelta(hours=sla_hours)
    now = datetime.now()
    remaining = (deadline - now).total_seconds() / 3600

    if remaining <= 0:
        return "breached", remaining
    elif remaining <= sla_hours * 0.25:  # Last 25% of SLA
        return "critical", remaining
    elif remaining <= sla_hours * 0.50:  # Last 50% of SLA
        return "warning", remaining
    return "ok", remaining


def show_status():
    state = load_state()
    active = state.get("active_workflows", {})
    completed = state.get("completed_workflows", [])
    breaches = state.get("sla_breaches", [])

    print("=== Client SLA Monitor ===")
    print(f"Total workflows tracked: {state.get('total_workflows', 0)}")
    print(f"Active workflows: {len(active)}")
    print(f"Completed: {len(completed)}")
    print(f"SLA breaches: {len(breaches)}")

    print("\nSLA Defaults (hours):")
    for wf_type, hours in sorted(SLA_HOURS.items()):
        print(f"  {wf_type}: {hours}h")

    if active:
        print("\nActive Workflows:")
        for wf_id, wf in active.items():
            client = wf.get("client", "unknown")
            wf_type = wf.get("workflow_type", "unknown")
            phases = wf.get("phases_completed", [])
            status, remaining = check_sla_status(wf)
            status_icon = {"ok": "OK", "warning": "WARN", "critical": "CRIT", "breached": "BREACH"}
            print(f"\n  [{status_icon.get(status, '?')}] {wf_id}")
            print(f"    Client: {client} | Type: {wf_type}")
            print(f"    Phases: {', '.join(phases) if phases else 'none'}")
            print(f"    Remaining: {remaining:.1f}h")

    if breaches:
        print(f"\nRecent SLA Breaches (last {min(5, len(breaches))}):")
        for b in breaches[-5:]:
            print(f"  {b.get('workflow_id', '?')}: {b.get('client', '?')} - {b.get('breach_time', '?')[:19]}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Client SLA monitor state reset.")
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

    # Only track execution script activity
    if "execution/" not in command and "clients/" not in command:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()

    client = detect_client(command)
    wf_type = detect_workflow_type(command)
    phase = detect_phase(command)

    # Start new workflow if client context is being loaded
    if client and "clients/" in command:
        wf_id = f"{client}_{wf_type or 'workflow'}_{now[:10]}"
        active = state.get("active_workflows", {})

        # Check if this client already has an active workflow
        existing = None
        for wid, wf in active.items():
            if wf.get("client") == client:
                existing = wid
                break

        if not existing:
            sla_hours = SLA_HOURS.get(wf_type, SLA_HOURS["default"])
            active[wf_id] = {
                "client": client,
                "workflow_type": wf_type or "unknown",
                "start_time": now,
                "sla_hours": sla_hours,
                "phases_completed": [],
                "last_activity": now
            }
            state["active_workflows"] = active
            state["total_workflows"] = state.get("total_workflows", 0) + 1

    # Update phase progress for active workflows
    if phase and client:
        active = state.get("active_workflows", {})
        for wid, wf in active.items():
            if wf.get("client") == client:
                phases = wf.get("phases_completed", [])
                if phase not in phases:
                    phases.append(phase)
                wf["phases_completed"] = phases
                wf["last_activity"] = now

                # Check SLA status
                status, remaining = check_sla_status(wf)
                if status == "breached":
                    state["sla_breaches"] = state.get("sla_breaches", [])
                    state["sla_breaches"].append({
                        "workflow_id": wid,
                        "client": client,
                        "breach_time": now,
                        "sla_hours": wf.get("sla_hours", 24)
                    })
                    state["sla_breaches"] = state["sla_breaches"][-50:]

                # Check for completion (delivery phase reached)
                if phase == "delivery":
                    completed = state.get("completed_workflows", [])
                    completed.append({
                        "workflow_id": wid,
                        "client": client,
                        "start_time": wf.get("start_time"),
                        "end_time": now,
                        "phases": phases,
                        "within_sla": status != "breached"
                    })
                    state["completed_workflows"] = completed[-100:]
                    del active[wid]

                break
        state["active_workflows"] = active

    # Check all active workflows for SLA warnings
    for wid, wf in state.get("active_workflows", {}).items():
        status, remaining = check_sla_status(wf)
        if status in ("critical", "breached"):
            client_name = wf.get("client", "unknown")
            wf_type_name = wf.get("workflow_type", "unknown")
            output = {
                "decision": "ALLOW",
                "reason": f"[SLA Monitor] {status.upper()}: {client_name}/{wf_type_name} - {remaining:.1f}h remaining"
            }
            save_state(state)
            print(json.dumps(output))
            return

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
