#!/usr/bin/env python3
"""
Hook 25: Funnel Completeness Checker (PostToolUse on Write)

After writes to .tmp/vsl_funnel_* or .tmp/*funnel* directories:
- Check if all expected funnel components exist:
  - Research/avatar document
  - VSL script (2000+ words)
  - Sales/landing page
  - Email sequence (3+ emails)
  - Optional: Ad copy, retargeting sequence
- Track in .tmp/hooks/funnel_completeness.json
- Report completion percentage. ALLOW always.
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "funnel_completeness.json"
TMP_DIR = PROJECT_ROOT / ".tmp"

REQUIRED_COMPONENTS = {
    "research": {
        "patterns": ["*research*", "*avatar*", "*analysis*", "*01_*"],
        "description": "Research/Avatar document",
        "required": True,
    },
    "vsl_script": {
        "patterns": ["*vsl*script*", "*vsl*", "*02_*script*"],
        "description": "VSL Script",
        "required": True,
        "min_words": 2000,
    },
    "sales_page": {
        "patterns": ["*sales*page*", "*landing*page*", "*03_*page*"],
        "description": "Sales/Landing Page",
        "required": True,
    },
    "email_sequence": {
        "patterns": ["*email*sequence*", "*email*", "*04_*email*", "*nurture*"],
        "description": "Email Sequence (3+ emails)",
        "required": True,
        "min_emails": 3,
    },
    "ad_copy": {
        "patterns": ["*ad*copy*", "*ad*creative*", "*facebook*ad*", "*google*ad*"],
        "description": "Ad Copy",
        "required": False,
    },
    "retargeting": {
        "patterns": ["*retarget*", "*follow*up*", "*remarketing*"],
        "description": "Retargeting Sequence",
        "required": False,
    },
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"funnels": {}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def find_funnel_dir(file_path):
    """Determine which funnel directory this file belongs to."""
    path = Path(file_path)
    parts = path.parts

    # Look for funnel-related directory in path
    for i, part in enumerate(parts):
        if "funnel" in part.lower() or "vsl_funnel" in part.lower():
            return str(Path(*parts[:i + 1]))

    # If file is in .tmp/ and has funnel in name
    if ".tmp" in file_path and "funnel" in file_path.lower():
        # Return the parent directory
        return str(path.parent)

    return None


def matches_pattern(filename, patterns):
    """Check if filename matches any of the glob patterns."""
    import fnmatch
    filename_lower = filename.lower()
    for pattern in patterns:
        if fnmatch.fnmatch(filename_lower, pattern):
            return True
    return False


def count_emails_in_file(filepath):
    """Count number of distinct emails in an email sequence file."""
    try:
        content = Path(filepath).read_text()
        # Look for email separators
        separators = [
            r'(?:Email|Subject)\s*(?:#|\d+)',
            r'---+',
            r'##\s+Email',
            r'Subject\s*(?:Line)?:',
        ]
        max_count = 0
        for pattern in separators:
            matches = re.findall(pattern, content, re.IGNORECASE)
            max_count = max(max_count, len(matches))
        return max(max_count, 1)
    except OSError:
        return 0


def check_word_count(filepath, min_words):
    """Check if file has minimum word count."""
    try:
        content = Path(filepath).read_text()
        words = len(content.split())
        return words, words >= min_words
    except OSError:
        return 0, False


def scan_funnel_directory(funnel_dir):
    """Scan a funnel directory for components."""
    funnel_path = Path(funnel_dir)
    if not funnel_path.exists():
        return {}

    found_components = {}
    all_files = list(funnel_path.rglob("*"))

    for comp_name, comp_info in REQUIRED_COMPONENTS.items():
        found = False
        found_file = None
        for f in all_files:
            if f.is_file() and matches_pattern(f.name, comp_info["patterns"]):
                found = True
                found_file = str(f)
                break

        status = {
            "found": found,
            "file": found_file,
            "required": comp_info["required"],
            "description": comp_info["description"],
        }

        if found and found_file:
            if "min_words" in comp_info:
                words, meets_min = check_word_count(found_file, comp_info["min_words"])
                status["word_count"] = words
                status["meets_minimum"] = meets_min
            if "min_emails" in comp_info:
                email_count = count_emails_in_file(found_file)
                status["email_count"] = email_count
                status["meets_minimum"] = email_count >= comp_info["min_emails"]

        found_components[comp_name] = status

    return found_components


def calculate_completion(components):
    """Calculate completion percentage."""
    required_total = sum(1 for c in components.values() if c["required"])
    required_found = sum(1 for c in components.values() if c["required"] and c["found"])
    optional_total = sum(1 for c in components.values() if not c["required"])
    optional_found = sum(1 for c in components.values() if not c["required"] and c["found"])

    if required_total == 0:
        return 100.0

    # Required components are 80% of score, optional 20%
    required_pct = (required_found / required_total * 80) if required_total > 0 else 80
    optional_pct = (optional_found / optional_total * 20) if optional_total > 0 else 0

    return round(required_pct + optional_pct, 1)


def handle_status():
    state = load_state()
    print("=== Funnel Completeness Checker Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    funnels = state.get("funnels", {})
    if not funnels:
        print("No funnels tracked yet.")
    else:
        for name, data in funnels.items():
            print(f"\nFunnel: {name}")
            print(f"  Completion: {data.get('completion_pct', 0)}%")
            components = data.get("components", {})
            for comp_name, comp_data in components.items():
                status = "FOUND" if comp_data.get("found") else "MISSING"
                req = "required" if comp_data.get("required") else "optional"
                desc = comp_data.get("description", comp_name)
                extra = ""
                if comp_data.get("word_count"):
                    extra += f" ({comp_data['word_count']} words)"
                if comp_data.get("email_count"):
                    extra += f" ({comp_data['email_count']} emails)"
                print(f"    [{status}] {desc} ({req}){extra}")
            print(f"  Last updated: {data.get('last_updated', 'unknown')}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Funnel completeness state reset.")
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

    if tool_name != "Write":
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")

    # Only check funnel-related writes in .tmp/
    if ".tmp" not in file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    if "funnel" not in file_path.lower() and "vsl" not in file_path.lower():
        print(json.dumps({"decision": "ALLOW"}))
        return

    funnel_dir = find_funnel_dir(file_path)
    if not funnel_dir:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()

    # Scan the funnel directory
    components = scan_funnel_directory(funnel_dir)
    completion_pct = calculate_completion(components)

    funnel_key = Path(funnel_dir).name
    state["funnels"][funnel_key] = {
        "directory": funnel_dir,
        "components": components,
        "completion_pct": completion_pct,
        "last_updated": datetime.now().isoformat(),
    }
    save_state(state)

    # Build status message
    missing_required = [
        c["description"] for c in components.values()
        if c["required"] and not c["found"]
    ]

    if missing_required:
        reason = (
            f"Funnel completion: {completion_pct}%. "
            f"Missing required components: {', '.join(missing_required)}"
        )
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        print(json.dumps({
            "decision": "ALLOW",
            "reason": f"Funnel completion: {completion_pct}%. All required components present."
        }))


if __name__ == "__main__":
    main()
