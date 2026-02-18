#!/usr/bin/env python3
"""
Hook 36: Execution Timeout Guard (PreToolUse on Bash)

Before running execution scripts, warn about known slow scripts:
- scrape_*.py scripts: may take several minutes
- generate_complete_vsl_funnel.py: multiple API calls
- research_market_deep.py: multiple Perplexity queries
- gmaps_parallel_pipeline.py: processes many locations
- full_campaign_pipeline.py: multiple steps

Brief INFO to stderr for known long-running scripts. Exit 0 always.
"""

import json
import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "timeout_guard_log.json"

# Known slow scripts with estimated duration and warning message
SLOW_SCRIPTS = {
    "scrape_linkedin_apify.py": {
        "estimate": "2-5 minutes",
        "reason": "LinkedIn scraping via Apify actors",
    },
    "scrape_google_maps.py": {
        "estimate": "3-10 minutes",
        "reason": "Google Maps data extraction",
    },
    "scrape_apify.py": {
        "estimate": "2-5 minutes",
        "reason": "Apify actor execution",
    },
    "generate_complete_vsl_funnel.py": {
        "estimate": "5-10 minutes",
        "reason": "Full funnel involves research + VSL + sales page + emails",
    },
    "research_market_deep.py": {
        "estimate": "3-5 minutes",
        "reason": "Multiple Perplexity API queries for deep research",
    },
    "research_company_offer.py": {
        "estimate": "1-3 minutes",
        "reason": "Perplexity research queries",
    },
    "gmaps_parallel_pipeline.py": {
        "estimate": "5-15 minutes",
        "reason": "Parallel processing of multiple map locations",
    },
    "full_campaign_pipeline.py": {
        "estimate": "10-20 minutes",
        "reason": "Full campaign runs scraping + validation + email writing + upload",
    },
    "generate_vsl_script.py": {
        "estimate": "1-3 minutes",
        "reason": "Long-form VSL generation via LLM",
    },
    "validate_emails.py": {
        "estimate": "2-10 minutes",
        "reason": "Email validation depends on list size",
    },
    "upload_leads_instantly.py": {
        "estimate": "1-5 minutes",
        "reason": "Bulk upload to Instantly API",
    },
}

# Pattern-based slow script detection
SLOW_PATTERNS = [
    {
        "pattern": r"scrape_\w+\.py",
        "estimate": "2-5 minutes",
        "reason": "Scraping scripts may take several minutes depending on data volume",
    },
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"warnings": [], "stats": {"total": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def find_slow_script(command):
    """Check if the command runs a known slow script."""
    script_match = re.search(r'(?:python3?\s+)?(?:execution/)?(\w+\.py)', command)
    if not script_match:
        return None

    script_name = script_match.group(1)

    # Check exact match first
    if script_name in SLOW_SCRIPTS:
        info = SLOW_SCRIPTS[script_name]
        return script_name, info["estimate"], info["reason"]

    # Check patterns
    for pattern_info in SLOW_PATTERNS:
        if re.match(pattern_info["pattern"], script_name):
            return script_name, pattern_info["estimate"], pattern_info["reason"]

    return None


def handle_status():
    state = load_state()
    print("=== Execution Timeout Guard Status ===")
    print(f"State file: {STATE_FILE}")

    print(f"\nKnown slow scripts:")
    for script, info in sorted(SLOW_SCRIPTS.items()):
        print(f"  {script}: ~{info['estimate']}")
        print(f"    {info['reason']}")

    stats = state.get("stats", {})
    print(f"\nWarnings issued: {stats.get('total', 0)}")

    warnings = state.get("warnings", [])
    if warnings:
        print(f"\nRecent warnings:")
        for w in warnings[-5:]:
            print(f"  {w.get('script', '?')} at {w.get('timestamp', '?')}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Execution timeout guard state reset.")
    else:
        print("No state file to reset.")


def main():
    if "--status" in sys.argv:
        handle_status()
        return
    if "--reset" in sys.argv:
        handle_reset()
        return

    # PreToolUse mode
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")
    result = find_slow_script(command)

    if result:
        script_name, estimate, reason = result

        state = load_state()
        state["warnings"].append({
            "script": script_name,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })
        state["warnings"] = state["warnings"][-50:]
        state["stats"]["total"] = state["stats"].get("total", 0) + 1
        save_state(state)

        sys.stderr.write(
            f"[TIMEOUT INFO] {script_name} estimated runtime: {estimate}. "
            f"{reason}\n"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
