#!/usr/bin/env python3
"""
Hook 120: system_health_reporter.py (PostToolUse on Bash)
Purpose: Aggregate health metrics across all hooks into a single report.
Logic: Periodically read state files from all other hooks. Generate summary:
active hooks, error rates, workflow completions, API costs, quality scores.
Write to .tmp/hooks/system_health.json.

Protocol:
  - PostToolUse: prints JSON to stdout {"decision": "ALLOW"}
  - Supports --status and --reset CLI flags
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "system_health.json"
HEALTH_REPORT_FILE = STATE_DIR / "system_health_report.json"

# How often to regenerate the report (in number of triggers)
REPORT_INTERVAL = 10

# Hook state files and their metrics
HOOK_STATE_MAP = {
    "api_costs.json": {
        "name": "API Cost Estimator",
        "metrics": ["session_total", "by_script"],
    },
    "error_categories.json": {
        "name": "Error Categorizer",
        "metrics": ["total_errors", "error_free_runs", "category_counts"],
    },
    "workflow_completions.json": {
        "name": "Workflow Completion Tracker",
        "metrics": ["total_started", "total_completed", "total_abandoned"],
    },
    "client_billing.json": {
        "name": "Client Billing Estimator",
        "metrics": ["total_cost", "clients"],
    },
    "client_deliverables.json": {
        "name": "Client Deliverable Tracker",
        "metrics": ["total_deliverables", "clients"],
    },
    "quality_trends.json": {
        "name": "Quality Trend Analyzer",
        "metrics": ["total_analyzed", "quality_scores", "degradation_warnings"],
    },
    "script_benchmarks.json": {
        "name": "Script Execution Benchmarker",
        "metrics": ["total_benchmarked", "scripts"],
    },
    "directive_usage.json": {
        "name": "Directive Usage Frequency",
        "metrics": ["total_reads", "directives"],
    },
    "client_sla.json": {
        "name": "Client SLA Monitor",
        "metrics": ["total_workflows", "sla_breaches"],
    },
    "circular_deps.json": {
        "name": "Circular Dependency Detector",
        "metrics": ["detected_cycles", "total_checks"],
    },
    "dead_directives.json": {
        "name": "Dead Directive Detector",
        "metrics": ["dead_directives", "healthy_directives"],
    },
    "orphan_scripts.json": {
        "name": "Orphan Script Detector",
        "metrics": ["orphan_scripts", "matched_scripts"],
    },
    "phase_transitions.json": {
        "name": "Phase Transition Validator",
        "metrics": ["total_transitions", "current_phase"],
    },
    "anneal_commits.json": {
        "name": "Self-Anneal Commit Validator",
        "metrics": ["valid_commits", "invalid_commits"],
    },
    "workflow_bottlenecks.json": {
        "name": "Workflow Bottleneck Detector",
        "metrics": ["bottlenecks", "total_steps"],
    },
    "client_communications.json": {
        "name": "Client Communication Logger",
        "metrics": ["total_comms", "by_channel"],
    },
    "delivery_receipts.json": {
        "name": "Delivery Receipt Generator",
        "metrics": ["total_deliveries", "by_method"],
    },
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "trigger_count": 0,
        "last_report": None,
        "reports_generated": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def read_hook_state(filename):
    """Read a hook's state file."""
    state_path = STATE_DIR / filename
    try:
        if state_path.exists():
            return json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return None


def generate_report():
    """Generate a comprehensive health report."""
    now = datetime.now().isoformat()
    report = {
        "generated_at": now,
        "hooks_status": {},
        "summary": {},
    }

    active_hooks = 0
    total_hooks = len(HOOK_STATE_MAP)

    # Collect data from each hook
    for state_file, hook_info in HOOK_STATE_MAP.items():
        hook_name = hook_info["name"]
        state = read_hook_state(state_file)

        if state is None:
            report["hooks_status"][hook_name] = {"status": "inactive", "state_file": state_file}
            continue

        active_hooks += 1
        hook_summary = {"status": "active", "state_file": state_file}

        for metric in hook_info["metrics"]:
            value = state.get(metric)
            if isinstance(value, (int, float, str, bool)):
                hook_summary[metric] = value
            elif isinstance(value, dict):
                hook_summary[f"{metric}_count"] = len(value)
            elif isinstance(value, list):
                hook_summary[f"{metric}_count"] = len(value)

        report["hooks_status"][hook_name] = hook_summary

    # Generate summary
    report["summary"]["active_hooks"] = active_hooks
    report["summary"]["total_hooks"] = total_hooks
    report["summary"]["health_score"] = round((active_hooks / total_hooks) * 100, 1) if total_hooks > 0 else 0

    # Error rate
    error_state = read_hook_state("error_categories.json")
    if error_state:
        total_checked = error_state.get("total_checked", 0)
        total_errors = error_state.get("total_errors", 0)
        report["summary"]["error_rate"] = round((total_errors / total_checked) * 100, 1) if total_checked > 0 else 0
        report["summary"]["total_errors"] = total_errors

    # Workflow completion rate
    wf_state = read_hook_state("workflow_completions.json")
    if wf_state:
        started = wf_state.get("total_started", 0)
        completed = wf_state.get("total_completed", 0)
        report["summary"]["workflow_completion_rate"] = round((completed / started) * 100, 1) if started > 0 else 0

    # API costs
    cost_state = read_hook_state("client_billing.json") or read_hook_state("api_costs.json")
    if cost_state:
        report["summary"]["estimated_api_cost"] = cost_state.get("total_cost", cost_state.get("session_total", 0))

    # Quality
    quality_state = read_hook_state("quality_trends.json")
    if quality_state:
        scores = quality_state.get("quality_scores", [])
        if scores:
            recent = scores[-10:]
            report["summary"]["avg_quality_score"] = round(sum(s.get("score", 0) for s in recent) / len(recent), 1)
            report["summary"]["degradation_warnings"] = len(quality_state.get("degradation_warnings", []))

    # SLA
    sla_state = read_hook_state("client_sla.json")
    if sla_state:
        report["summary"]["sla_breaches"] = len(sla_state.get("sla_breaches", []))

    # Write report
    try:
        HEALTH_REPORT_FILE.write_text(json.dumps(report, indent=2))
    except OSError:
        pass

    return report


def show_status():
    state = load_state()
    print("=== System Health Reporter ===")
    print(f"Triggers: {state.get('trigger_count', 0)}")
    print(f"Reports generated: {state.get('reports_generated', 0)}")
    print(f"Report interval: every {REPORT_INTERVAL} triggers")
    print(f"Last report: {state.get('last_report', 'Never')}")

    # Generate fresh report for display
    report = generate_report()
    summary = report.get("summary", {})

    print(f"\n--- System Health Summary ---")
    print(f"Active hooks: {summary.get('active_hooks', 0)}/{summary.get('total_hooks', 0)}")
    print(f"Health score: {summary.get('health_score', 0)}%")

    if "error_rate" in summary:
        print(f"Error rate: {summary['error_rate']}% ({summary.get('total_errors', 0)} errors)")

    if "workflow_completion_rate" in summary:
        print(f"Workflow completion: {summary['workflow_completion_rate']}%")

    if "estimated_api_cost" in summary:
        print(f"Estimated API cost: ${summary['estimated_api_cost']:.4f}")

    if "avg_quality_score" in summary:
        print(f"Avg quality score: {summary['avg_quality_score']}/100")
        if summary.get("degradation_warnings", 0) > 0:
            print(f"Quality warnings: {summary['degradation_warnings']}")

    if "sla_breaches" in summary:
        print(f"SLA breaches: {summary['sla_breaches']}")

    # Hook details
    hooks = report.get("hooks_status", {})
    active = {k: v for k, v in hooks.items() if v.get("status") == "active"}
    inactive = {k: v for k, v in hooks.items() if v.get("status") != "active"}

    if active:
        print(f"\nActive hooks ({len(active)}):")
        for name, info in sorted(active.items()):
            extras = {k: v for k, v in info.items() if k not in ("status", "state_file")}
            extra_str = ", ".join(f"{k}={v}" for k, v in list(extras.items())[:3])
            print(f"  {name}: {extra_str}")

    if inactive:
        print(f"\nInactive hooks ({len(inactive)}):")
        for name in sorted(inactive.keys()):
            print(f"  {name}")

    print(f"\nReport file: {HEALTH_REPORT_FILE}")
    sys.exit(0)


def reset_state():
    for f in [STATE_FILE, HEALTH_REPORT_FILE]:
        if f.exists():
            f.unlink()
    print("System health reporter state reset.")
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
    if tool_name not in ("Bash", "bash"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["trigger_count"] = state.get("trigger_count", 0) + 1

    # Only generate report every N triggers
    if state["trigger_count"] % REPORT_INTERVAL == 0:
        report = generate_report()
        state["last_report"] = datetime.now().isoformat()
        state["reports_generated"] = state.get("reports_generated", 0) + 1

        summary = report.get("summary", {})
        health_score = summary.get("health_score", 0)

        save_state(state)

        if health_score < 50:
            output = {
                "decision": "ALLOW",
                "reason": f"[System Health] Health score: {health_score}%. Check .tmp/hooks/system_health_report.json for details."
            }
        else:
            output = {"decision": "ALLOW"}

        print(json.dumps(output))
        return

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
