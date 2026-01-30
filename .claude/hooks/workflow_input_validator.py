#!/usr/bin/env python3
"""
Hook 30: Workflow Input Validator (PreToolUse on Bash)

When execution scripts run, validate that required arguments are present:
- Scripts with --company in their argparse should have --company provided
- Scripts with --website should have --website provided
- Scripts with --offer should have --offer provided
- Scripts with --topic should have --topic provided

If a likely-required argument is missing: WARN via stderr. Exit 0 always.
"""

import json
import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "input_validation_log.json"

# Known script -> required arguments mapping
KNOWN_SCRIPTS = {
    "generate_complete_vsl_funnel.py": ["--company", "--website", "--offer"],
    "generate_vsl_script.py": ["--company"],
    "generate_sales_page.py": ["--company"],
    "generate_email_sequence.py": ["--company"],
    "research_company_offer.py": ["--company", "--website"],
    "research_market_deep.py": ["--company"],
    "research_prospect_deep.py": ["--name"],
    "write_cold_emails.py": ["--company", "--offer"],
    "generate_blog_post.py": ["--topic"],
    "generate_linkedin_post.py": ["--topic"],
    "generate_newsletter.py": ["--topic"],
    "generate_case_study.py": ["--company"],
    "generate_youtube_script.py": ["--topic"],
    "generate_webinar_funnel.py": ["--topic"],
    "generate_ad_copy.py": ["--company", "--offer"],
    "create_google_doc.py": ["--file", "--title"],
    "send_slack_notification.py": ["--message"],
    "scrape_linkedin_apify.py": ["--url"],
    "validate_emails.py": ["--file"],
    "personalize_emails_ai.py": ["--file"],
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"validations": [], "stats": {"total": 0, "warnings": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_script_name(command):
    """Extract the Python script name from a command."""
    match = re.search(r'(?:python3?\s+)?(?:execution/)?(\w+\.py)', command)
    if match:
        return match.group(1)
    return None


def extract_provided_args(command):
    """Extract all --argument flags from the command."""
    return set(re.findall(r'(--\w+)', command))


def check_args(script_name, command):
    """Check if required arguments are present."""
    if script_name not in KNOWN_SCRIPTS:
        # For unknown scripts, try to infer from the script file
        return try_infer_args(script_name, command)

    required = KNOWN_SCRIPTS[script_name]
    provided = extract_provided_args(command)
    missing = [arg for arg in required if arg not in provided]

    return missing


def try_infer_args(script_name, command):
    """Try to infer required args by reading the script file."""
    script_path = PROJECT_ROOT / "execution" / script_name
    if not script_path.exists():
        return []

    try:
        content = script_path.read_text()
        # Look for argparse required=True arguments
        required_args = []
        for match in re.finditer(
            r'add_argument\(\s*["\'](--%s)["\'].*?required\s*=\s*True' % r'\w+',
            content, re.DOTALL
        ):
            required_args.append(match.group(1))

        if not required_args:
            # Look for add_argument with no default (likely required)
            for match in re.finditer(
                r'add_argument\(\s*["\'](--\w+)["\'](?:(?!default).)*?\)',
                content, re.DOTALL
            ):
                arg = match.group(1)
                if arg not in ["--help", "--verbose", "--debug", "--output", "--dry-run"]:
                    required_args.append(arg)

        provided = extract_provided_args(command)
        return [arg for arg in required_args if arg not in provided]

    except OSError:
        return []


def handle_status():
    state = load_state()
    print("=== Workflow Input Validator Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"Total validations: {stats.get('total', 0)}")
    print(f"Warnings issued: {stats.get('warnings', 0)}")

    print(f"\nKnown script mappings: {len(KNOWN_SCRIPTS)}")
    for script, args in sorted(KNOWN_SCRIPTS.items()):
        print(f"  {script}: {', '.join(args)}")

    validations = state.get("validations", [])
    if validations:
        print(f"\nRecent validations:")
        for v in validations[-10:]:
            status = "WARN" if v.get("missing") else "OK"
            print(f"  [{status}] {v.get('script', '?')}")
            if v.get("missing"):
                print(f"    Missing: {', '.join(v['missing'])}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Workflow input validator state reset.")
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

    # Only check execution script invocations
    if "execution/" not in command and ".py" not in command:
        sys.exit(0)

    script_name = extract_script_name(command)
    if not script_name:
        sys.exit(0)

    missing = check_args(script_name, command)

    state = load_state()
    validation = {
        "script": script_name,
        "missing": missing,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }
    state["validations"].append(validation)
    state["validations"] = state["validations"][-50:]
    state["stats"]["total"] = state["stats"].get("total", 0) + 1

    if missing:
        state["stats"]["warnings"] = state["stats"].get("warnings", 0) + 1
        save_state(state)
        sys.stderr.write(
            f"[INPUT VALIDATOR] Possible missing arguments for {script_name}: "
            f"{', '.join(missing)}\n"
        )
    else:
        save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
