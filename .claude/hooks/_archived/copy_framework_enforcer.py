#!/usr/bin/env python3
"""
Hook 90: copy_framework_enforcer.py - PostToolUse on Write

Ensures marketing copy follows proper frameworks (AIDA, PAS, BAB, etc.).
Detects framework elements and warns if a framework is incomplete.

  AIDA: Attention -> Interest -> Desire -> Action
  PAS:  Problem -> Agitate -> Solve
  BAB:  Before -> After -> Bridge
  FAB:  Features -> Advantages -> Benefits

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional framework warnings

CLI Flags:
  --status  Show framework compliance stats
  --reset   Clear state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime
from fnmatch import fnmatch

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "copy_framework.json"

# File patterns for marketing/sales content
MARKETING_PATTERNS = [
    "*vsl*", "*sales*", "*landing*", "*email*", "*funnel*",
    "*pitch*", "*offer*", "*copy*", "*outreach*",
]

# Framework detection rules
FRAMEWORKS = {
    "AIDA": {
        "elements": {
            "Attention": [
                r"(?:attention|hook|headline|opening|grab)",
                r"(?:did you know|imagine|what if|picture this)",
            ],
            "Interest": [
                r"(?:interest|curious|learn|discover|consider)",
                r"(?:here\'?s (?:what|why|how)|the (?:truth|problem|secret))",
            ],
            "Desire": [
                r"(?:desire|want|need|wish|dream|imagine having)",
                r"(?:transform|achieve|unlock|gain|enjoy)",
            ],
            "Action": [
                r"(?:action|cta|call.to.action|click|sign.up|register|buy|order)",
                r"(?:get started|join now|book|schedule|claim|grab)",
            ],
        },
    },
    "PAS": {
        "elements": {
            "Problem": [
                r"(?:problem|struggle|pain|challenge|frustrat|difficult|stuck)",
                r"(?:tired of|sick of|fed up|can\'t seem to|failing to)",
            ],
            "Agitate": [
                r"(?:agitate|worse|even more|on top of|not only|imagine if)",
                r"(?:what happens|without|missing out|losing|wasting)",
            ],
            "Solve": [
                r"(?:solution|solve|answer|fix|remedy|introducing|meet)",
                r"(?:here\'?s how|that\'?s why|the good news|finally)",
            ],
        },
    },
    "BAB": {
        "elements": {
            "Before": [
                r"(?:before|currently|right now|today you|situation|status quo)",
                r"(?:where you are|your current|as things stand)",
            ],
            "After": [
                r"(?:after|imagine|picture|envision|what if|future|transform)",
                r"(?:new reality|instead|better way|different story)",
            ],
            "Bridge": [
                r"(?:bridge|how to get|the path|the way|here\'?s how|all you need)",
                r"(?:introducing|the solution|our approach|the method)",
            ],
        },
    },
}

MIN_FRAMEWORK_COVERAGE = 0.6  # Need 60% of elements to count


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "checks": [],
        "frameworks_detected": {},
        "incomplete_frameworks": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["checks"] = state["checks"][-30:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_marketing_content(file_path):
    filename_lower = Path(file_path).name.lower()
    return any(fnmatch(filename_lower, pat) for pat in MARKETING_PATTERNS)


def detect_framework_elements(content):
    """Detect which framework elements are present in content."""
    content_lower = content.lower()
    results = {}

    for fw_name, fw_config in FRAMEWORKS.items():
        elements_found = {}
        for element_name, patterns in fw_config["elements"].items():
            found = False
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    found = True
                    break
            elements_found[element_name] = found

        total = len(elements_found)
        present = sum(1 for v in elements_found.values() if v)
        coverage = present / total if total > 0 else 0

        results[fw_name] = {
            "elements": elements_found,
            "coverage": round(coverage, 2),
            "present": present,
            "total": total,
        }

    return results


def find_best_framework(results):
    """Find the framework with the best coverage."""
    best = None
    best_coverage = 0
    for fw_name, info in results.items():
        if info["coverage"] > best_coverage:
            best = fw_name
            best_coverage = info["coverage"]
    return best, best_coverage


def handle_status():
    state = load_state()
    print("Copy Framework Enforcer Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Incomplete frameworks: {state['incomplete_frameworks']}")
    if state["frameworks_detected"]:
        print("  Frameworks detected:")
        for fw, count in state["frameworks_detected"].items():
            print(f"    {fw}: {count} times")
    if state["checks"]:
        print("  Recent checks:")
        for c in state["checks"][-5:]:
            fw = c.get("best_framework", "none")
            cov = c.get("coverage", 0)
            print(f"    [{fw} {cov:.0%}] {c.get('file', 'unknown')}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "checks": [], "frameworks_detected": {},
        "incomplete_frameworks": 0, "total_checks": 0,
    }))
    print("Copy Framework Enforcer: State reset.")
    sys.exit(0)


def main():
    if "--status" in sys.argv:
        handle_status()
    if "--reset" in sys.argv:
        handle_reset()

    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, IOError):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Write" or "tool_result" not in data:
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    if not is_marketing_content(file_path) or not content or len(content) < 200:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    results = detect_framework_elements(content)
    best_fw, best_coverage = find_best_framework(results)

    file_name = Path(file_path).name
    check_entry = {
        "file": file_name,
        "best_framework": best_fw,
        "coverage": best_coverage,
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_entry)

    if best_fw:
        fw_counts = state.get("frameworks_detected", {})
        fw_counts[best_fw] = fw_counts.get(best_fw, 0) + 1
        state["frameworks_detected"] = fw_counts

    if best_fw and best_coverage < MIN_FRAMEWORK_COVERAGE:
        state["incomplete_frameworks"] += 1
        save_state(state)
        fw_info = results[best_fw]
        missing = [k for k, v in fw_info["elements"].items() if not v]
        reason = (
            f"Incomplete {best_fw} framework in {file_name} "
            f"({fw_info['present']}/{fw_info['total']} elements, {best_coverage:.0%}). "
            f"Missing: {', '.join(missing)}."
        )
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    elif not best_fw or best_coverage < 0.3:
        state["incomplete_frameworks"] += 1
        save_state(state)
        reason = (
            f"Marketing content {file_name} doesn't follow a clear copy framework "
            f"(AIDA, PAS, or BAB). Consider structuring with a proven framework."
        )
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
