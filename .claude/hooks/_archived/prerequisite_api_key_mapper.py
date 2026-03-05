#!/usr/bin/env python3
"""
Hook 28: Prerequisite API Key Mapper (PreToolUse on Bash)

Maps specific execution scripts to their required API keys:
- research_*.py -> PERPLEXITY_API_KEY
- generate_*.py -> OPENROUTER_API_KEY
- scrape_apify*.py, scrape_linkedin*.py -> APIFY_API_TOKEN
- create_google_doc*.py -> GOOGLE_APPLICATION_CREDENTIALS or token.pickle
- send_slack*.py -> SLACK_WEBHOOK_URL
- generate_image*.py, generate_thumbnail*.py -> FAL_KEY
- deploy_*.py -> RAILWAY_API_TOKEN
- validate_emails.py -> email validation API key
- instantly_*.py -> INSTANTLY_API_KEY
- scrape_google_maps.py -> SERP_API_KEY or APIFY_API_TOKEN

Only warn if the SPECIFIC key is missing. Exit 0 always.
"""

import json
import sys
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "api_key_mapper_log.json"

# Script pattern -> required API key(s)
SCRIPT_KEY_MAP = [
    {
        "pattern": r"research_\w+\.py",
        "keys": ["PERPLEXITY_API_KEY"],
        "description": "Research scripts require Perplexity API",
    },
    {
        "pattern": r"generate_(?!image|thumbnail)\w+\.py",
        "keys": ["OPENROUTER_API_KEY"],
        "description": "Generation scripts require OpenRouter API",
    },
    {
        "pattern": r"generate_image\w*\.py",
        "keys": ["FAL_KEY"],
        "description": "Image generation requires FAL API",
    },
    {
        "pattern": r"generate_thumbnail\w*\.py",
        "keys": ["FAL_KEY"],
        "description": "Thumbnail generation requires FAL API",
    },
    {
        "pattern": r"scrape_(?:apify|linkedin)\w*\.py",
        "keys": ["APIFY_API_TOKEN"],
        "description": "Apify/LinkedIn scraping requires Apify token",
    },
    {
        "pattern": r"scrape_google_maps\w*\.py",
        "keys": ["SERP_API_KEY", "APIFY_API_TOKEN"],
        "description": "Google Maps scraping requires SERP or Apify API",
        "any_of": True,
    },
    {
        "pattern": r"create_google_doc\w*\.py",
        "keys": ["GOOGLE_APPLICATION_CREDENTIALS"],
        "description": "Google Docs requires credentials",
        "check_files": ["token.pickle", "credentials.json"],
    },
    {
        "pattern": r"(?:read|append_to|update)_sheet\w*\.py",
        "keys": ["GOOGLE_APPLICATION_CREDENTIALS"],
        "description": "Google Sheets requires credentials",
        "check_files": ["token.pickle", "credentials.json"],
    },
    {
        "pattern": r"send_slack\w*\.py",
        "keys": ["SLACK_WEBHOOK_URL"],
        "description": "Slack notifications require webhook URL",
    },
    {
        "pattern": r"deploy_\w+\.py",
        "keys": ["RAILWAY_API_TOKEN"],
        "description": "Deployment scripts require Railway API token",
        "check_files": [str(Path.home() / ".railway" / "config.json")],
    },
    {
        "pattern": r"validate_emails\w*\.py",
        "keys": ["EMAIL_VALIDATION_API_KEY", "NEVERBOUNCE_API_KEY"],
        "description": "Email validation requires validation API key",
        "any_of": True,
    },
    {
        "pattern": r"instantly_\w*\.py",
        "keys": ["INSTANTLY_API_KEY"],
        "description": "Instantly scripts require Instantly API key",
    },
    {
        "pattern": r"upload_leads_instantly\w*\.py",
        "keys": ["INSTANTLY_API_KEY"],
        "description": "Instantly upload requires API key",
    },
    {
        "pattern": r"write_\w+\.py",
        "keys": ["OPENROUTER_API_KEY"],
        "description": "Writing scripts require OpenRouter API",
    },
    {
        "pattern": r"gmaps_\w+\.py",
        "keys": ["SERP_API_KEY", "APIFY_API_TOKEN"],
        "description": "Google Maps pipeline requires SERP or Apify",
        "any_of": True,
    },
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": [], "missing_keys": {}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def check_env_key(key):
    """Check if an environment variable is set."""
    return bool(os.environ.get(key, ""))


def check_file_exists(filepath):
    """Check if a file exists."""
    if filepath.startswith("/") or filepath.startswith("~"):
        return Path(os.path.expanduser(filepath)).exists()
    return (PROJECT_ROOT / filepath).exists()


def find_matching_script(command):
    """Find which script pattern matches the command."""
    # Extract script name from command
    script_match = re.search(r'(?:python3?\s+)?(?:execution/)?(\w+\.py)', command)
    if not script_match:
        return None

    script_name = script_match.group(1)

    for mapping in SCRIPT_KEY_MAP:
        if re.match(mapping["pattern"], script_name):
            return mapping, script_name

    return None


def check_keys(mapping):
    """Check if required keys are available."""
    keys = mapping["keys"]
    any_of = mapping.get("any_of", False)
    check_files = mapping.get("check_files", [])

    missing = []
    found_any = False

    for key in keys:
        if check_env_key(key):
            found_any = True
        else:
            missing.append(key)

    # Check alternative file-based credentials
    for filepath in check_files:
        if check_file_exists(filepath):
            found_any = True

    if any_of:
        # Only need one of the keys
        if not found_any:
            return missing, False
        return [], True
    else:
        # Need all keys (but file alternatives count)
        if found_any and check_files:
            return [], True
        return missing, len(missing) == 0


def handle_status():
    state = load_state()
    print("=== Prerequisite API Key Mapper Status ===")
    print(f"State file: {STATE_FILE}")

    print(f"\nEnvironment key status:")
    all_keys = set()
    for mapping in SCRIPT_KEY_MAP:
        all_keys.update(mapping["keys"])

    for key in sorted(all_keys):
        status = "SET" if check_env_key(key) else "MISSING"
        print(f"  {key}: {status}")

    print(f"\nFile credentials:")
    for f in ["token.pickle", "credentials.json"]:
        exists = check_file_exists(f)
        print(f"  {f}: {'EXISTS' if exists else 'MISSING'}")

    railway_config = Path.home() / ".railway" / "config.json"
    print(f"  Railway config: {'EXISTS' if railway_config.exists() else 'MISSING'}")

    missing = state.get("missing_keys", {})
    if missing:
        print(f"\nRecent missing key warnings:")
        for script, keys in list(missing.items())[-10:]:
            print(f"  {script}: {', '.join(keys)}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("API key mapper state reset.")
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

    # Check if running an execution script
    if "execution/" not in command and not re.search(r'\b\w+\.py\b', command):
        sys.exit(0)

    result = find_matching_script(command)
    if not result:
        sys.exit(0)

    mapping, script_name = result
    missing, all_good = check_keys(mapping)

    if missing:
        state = load_state()
        state["missing_keys"][script_name] = missing
        state["checks"].append({
            "script": script_name,
            "missing": missing,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })
        state["checks"] = state["checks"][-50:]
        save_state(state)

        any_of = mapping.get("any_of", False)
        if any_of:
            sys.stderr.write(
                f"[API KEY MAPPER] {mapping['description']}. "
                f"None of these keys found: {', '.join(missing)}\n"
            )
        else:
            sys.stderr.write(
                f"[API KEY MAPPER] {mapping['description']}. "
                f"Missing: {', '.join(missing)}\n"
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
