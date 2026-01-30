#!/usr/bin/env python3
"""
Hook 70: hook_health_monitor.py (PostToolUse on Bash)
Meta-hook: monitors the health of other hooks.
Checks every 50th bash command.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "hook_health.json"
HOOKS_DIR = Path(".claude/hooks")

CHECK_INTERVAL = 50  # Check every N bash commands
MAX_STATE_SIZE = 1_048_576  # 1MB

EXPECTED_HOOKS = [
    # Original hooks (1-20)
    "agent_limiter.py", "api_key_validator.py", "checkpoint_enforcer.py",
    "context_budget_guard.py", "context_loader_enforcer.py",
    "delivery_pipeline_validator.py", "doe_enforcer.py",
    "error_pattern_detector.py", "execution_logger.py",
    "google_docs_format_guard.py", "large_file_read_blocker.py",
    "output_quality_gate.py", "railway_deploy_guard.py",
    "script_exists_guard.py", "secrets_guard.py",
    "self_anneal_reminder.py", "session_activity_logger.py",
    "skill_bible_reminder.py", "tmp_cleanup_monitor.py",
    "workflow_pattern_tracker.py",
    # Hooks 46-70
    "tmp_directory_organizer.py", "git_commit_message_validator.py",
    "concurrent_write_guard.py", "dependency_chain_validator.py",
    "railway_project_guard.py", "railway_env_var_completeness.py",
    "cron_schedule_validator.py", "deployment_rollback_tracker.py",
    "service_name_convention_guard.py", "webhook_slug_validator.py",
    "dashboard_health_checker.py", "railway_token_expiry_checker.py",
    "deployment_config_validator.py", "production_safety_guard.py",
    "workflow_success_predictor.py", "context_efficiency_tracker.py",
    "skill_bible_usage_tracker.py", "directive_coverage_tracker.py",
    "output_word_count_tracker.py", "session_productivity_scorer.py",
    "api_cost_estimator.py", "workflow_dependency_mapper.py",
    "self_anneal_effectiveness_tracker.py", "daily_summary_generator.py",
    "hook_health_monitor.py",
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "bash_count": 0,
        "health_checks": [],
        "last_check": "",
        "issues_found": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def run_health_check():
    """Run comprehensive health check on hooks and state files."""
    issues = []
    info = {}

    # Check hook files exist
    existing_hooks = []
    missing_hooks = []
    if HOOKS_DIR.exists():
        for hook in EXPECTED_HOOKS:
            hook_path = HOOKS_DIR / hook
            if hook_path.exists():
                existing_hooks.append(hook)
            else:
                missing_hooks.append(hook)
                issues.append(f"Missing hook: {hook}")
    else:
        issues.append(f"Hooks directory does not exist: {HOOKS_DIR}")

    info["hooks_found"] = len(existing_hooks)
    info["hooks_missing"] = len(missing_hooks)
    info["missing_hooks"] = missing_hooks

    # Check state directory
    if not STATE_DIR.exists():
        issues.append(f"State directory does not exist: {STATE_DIR}")
        info["state_dir_exists"] = False
    else:
        info["state_dir_exists"] = True

        # Check state files
        state_files = {}
        oversized = []
        corrupted = []

        try:
            for f in STATE_DIR.iterdir():
                if f.suffix == ".json" and f.name != "hook_health.json":
                    size = f.stat().st_size
                    state_files[f.name] = size

                    if size > MAX_STATE_SIZE:
                        oversized.append(f.name)
                        issues.append(f"State file exceeds 1MB: {f.name} ({size / 1024:.0f}KB)")

                    # Validate JSON
                    try:
                        json.loads(f.read_text())
                    except json.JSONDecodeError:
                        corrupted.append(f.name)
                        issues.append(f"Corrupted JSON: {f.name}")
        except OSError as e:
            issues.append(f"Error reading state directory: {e}")

        info["state_files"] = len(state_files)
        info["state_file_sizes"] = state_files
        info["oversized_files"] = oversized
        info["corrupted_files"] = corrupted
        info["total_state_size_kb"] = sum(state_files.values()) / 1024

    return issues, info


def show_status():
    state = load_state()
    issues, info = run_health_check()

    print("=== Hook Health Monitor ===")
    print(f"Bash commands tracked: {state.get('bash_count', 0)}")
    print(f"Health checks performed: {len(state.get('health_checks', []))}")
    print(f"Last check: {state.get('last_check', 'never')}")
    print(f"Total issues found: {state.get('issues_found', 0)}")

    print(f"\nCurrent Health Check:")
    print(f"  Hooks found: {info.get('hooks_found', 0)}/{len(EXPECTED_HOOKS)}")
    if info.get("missing_hooks"):
        print(f"  Missing hooks:")
        for h in info["missing_hooks"]:
            print(f"    - {h}")

    if info.get("state_dir_exists"):
        print(f"  State files: {info.get('state_files', 0)}")
        total_kb = info.get("total_state_size_kb", 0)
        print(f"  Total state size: {total_kb:.1f}KB")

        if info.get("oversized_files"):
            print(f"  Oversized files:")
            for f in info["oversized_files"]:
                size = info.get("state_file_sizes", {}).get(f, 0)
                print(f"    - {f} ({size / 1024:.0f}KB)")

        if info.get("corrupted_files"):
            print(f"  Corrupted files:")
            for f in info["corrupted_files"]:
                print(f"    - {f}")

        # Show state file sizes
        sizes = info.get("state_file_sizes", {})
        if sizes:
            print(f"\n  State file sizes:")
            for name, size in sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:15]:
                print(f"    {name}: {size / 1024:.1f}KB")

    if issues:
        print(f"\nIssues ({len(issues)}):")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"\nNo issues found.")

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
    if tool_name not in ("Bash", "bash"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["bash_count"] = state.get("bash_count", 0) + 1

    # Only run health check every N commands
    if state["bash_count"] % CHECK_INTERVAL != 0:
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Run health check
    now = datetime.now().isoformat()
    issues, info = run_health_check()
    state["last_check"] = now

    check_entry = {
        "timestamp": now,
        "hooks_found": info.get("hooks_found", 0),
        "hooks_expected": len(EXPECTED_HOOKS),
        "state_files": info.get("state_files", 0),
        "issues": issues,
        "total_state_kb": info.get("total_state_size_kb", 0)
    }
    state["health_checks"] = state.get("health_checks", [])
    state["health_checks"].append(check_entry)
    state["health_checks"] = state["health_checks"][-50:]

    if issues:
        state["issues_found"] = state.get("issues_found", 0) + len(issues)

    save_state(state)

    if issues:
        reason = f"Hook health check found {len(issues)} issue(s): {'; '.join(issues[:3])}"
        if len(issues) > 3:
            reason += f" ... and {len(issues) - 3} more"
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
