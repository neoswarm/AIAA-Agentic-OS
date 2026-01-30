#!/usr/bin/env python3
"""
Hook 112: self_anneal_commit_validator.py (PostToolUse on Bash)
Purpose: Ensure self-anneal git commits include meaningful changes.
Logic: After git commit with "self-anneal" in message, validate: commit touches
directives/execution/skills, has meaningful diff (not just whitespace),
includes description of what was learned.

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
STATE_FILE = STATE_DIR / "anneal_commits.json"

# Expected paths for self-anneal commits
ANNEAL_PATHS = ["directives/", "execution/", "skills/"]

# Minimum meaningful diff size (characters)
MIN_DIFF_SIZE = 20

# Keywords that indicate learning was documented
LEARNING_KEYWORDS = [
    "learn", "fix", "improv", "updat", "add", "correct", "refactor",
    "optimiz", "enhanc", "resolv", "discover", "edge case", "better",
    "cleanup", "debug", "artifact", "deployment"
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "anneal_commits": [],
        "valid_commits": 0,
        "invalid_commits": 0,
        "total_checked": 0,
        "quality_scores": []
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_anneal_commit(command):
    """Check if the command is a git commit with self-anneal in the message."""
    if "git commit" not in command:
        return False
    return "self-anneal" in command.lower() or "self_anneal" in command.lower() or "anneal" in command.lower()


def extract_commit_message(command):
    """Extract commit message from git commit command."""
    # Match -m "message" or -m 'message'
    match = re.search(r'-m\s+["\'](.+?)["\']', command, re.DOTALL)
    if match:
        return match.group(1)
    # Match heredoc pattern
    match = re.search(r'<<.*?EOF\s*\n(.+?)EOF', command, re.DOTALL)
    if match:
        return match.group(1)
    return ""


def assess_commit_quality(message, result_text):
    """Assess the quality of a self-anneal commit."""
    issues = []
    score = 100

    # Check 1: Message has learning description
    message_lower = message.lower()
    has_learning = any(kw in message_lower for kw in LEARNING_KEYWORDS)
    if not has_learning:
        issues.append("No learning description in commit message")
        score -= 20

    # Check 2: Message is descriptive enough
    # Strip "self-anneal:" prefix and check remaining length
    stripped = re.sub(r'(?i)self[_-]?anneal:?\s*', '', message).strip()
    if len(stripped) < 10:
        issues.append(f"Commit message too short ({len(stripped)} chars after prefix)")
        score -= 20

    # Check 3: Touches expected directories
    touches_anneal_path = False
    for path in ANNEAL_PATHS:
        if path in result_text:
            touches_anneal_path = True
            break
    if not touches_anneal_path and result_text:
        issues.append("Commit doesn't touch directives/, execution/, or skills/")
        score -= 30

    # Check 4: Has meaningful changes (not just whitespace)
    if result_text:
        # Count actual content changes
        diff_lines = [l for l in result_text.split("\n")
                      if l.startswith("+") or l.startswith("-")]
        meaningful_lines = [l for l in diff_lines
                           if len(l.strip()) > 3 and not l.strip() in ("+", "-", "+++", "---")]
        if len(meaningful_lines) < 2:
            issues.append("Changes appear to be trivial (whitespace only)")
            score -= 20

    # Check 5: Includes Co-Authored-By (good practice)
    if "co-authored-by" in message.lower():
        score = min(100, score + 5)  # Bonus for attribution

    return max(0, score), issues


def show_status():
    state = load_state()
    commits = state.get("anneal_commits", [])

    print("=== Self-Anneal Commit Validator ===")
    print(f"Total checked: {state.get('total_checked', 0)}")
    print(f"Valid commits: {state.get('valid_commits', 0)}")
    print(f"Invalid commits: {state.get('invalid_commits', 0)}")

    scores = state.get("quality_scores", [])
    if scores:
        avg_score = sum(scores) / len(scores)
        print(f"Average quality score: {avg_score:.0f}/100")

    if commits:
        print(f"\nRecent anneal commits (last {min(10, len(commits))}):")
        for c in commits[-10:]:
            ts = c.get("timestamp", "?")[:19]
            score = c.get("quality_score", "?")
            msg = c.get("message_summary", "?")[:60]
            issues = c.get("issues", [])
            status = "VALID" if not issues else "ISSUES"
            print(f"  [{ts}] [{status}] Score: {score}/100")
            print(f"    Message: {msg}")
            if issues:
                for issue in issues:
                    print(f"    Issue: {issue}")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Self-anneal commit validator state reset.")
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

    if tool_name not in ("Bash", "bash"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    command = tool_input.get("command", "")
    if not is_anneal_commit(command):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()
    state["total_checked"] = state.get("total_checked", 0) + 1

    message = extract_commit_message(command)
    result_text = str(tool_result) if tool_result else ""

    score, issues = assess_commit_quality(message, result_text)

    commit_entry = {
        "timestamp": now,
        "message_summary": message[:200],
        "quality_score": score,
        "issues": issues,
        "valid": len(issues) == 0
    }

    state["anneal_commits"] = state.get("anneal_commits", [])
    state["anneal_commits"].append(commit_entry)
    state["anneal_commits"] = state["anneal_commits"][-100:]

    state["quality_scores"] = state.get("quality_scores", [])
    state["quality_scores"].append(score)
    state["quality_scores"] = state["quality_scores"][-100:]

    if issues:
        state["invalid_commits"] = state.get("invalid_commits", 0) + 1
    else:
        state["valid_commits"] = state.get("valid_commits", 0) + 1

    save_state(state)

    if issues:
        issue_text = "; ".join(issues)
        output = {
            "decision": "ALLOW",
            "reason": f"[Anneal Validator] Quality score: {score}/100. Issues: {issue_text}"
        }
    else:
        output = {
            "decision": "ALLOW",
            "reason": f"[Anneal Validator] Good self-anneal commit (score: {score}/100)"
        }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
