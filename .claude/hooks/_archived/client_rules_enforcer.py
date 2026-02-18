#!/usr/bin/env python3
"""
Hook 43: Client Rules Enforcer (PostToolUse on Write)

After writing ANY file to clients/{name}/ or .tmp/ when client context is loaded:
- Load the client's rules.md if it exists
- Scan the written content for violations of known rule patterns:
  - "words to avoid" -> check if any appear in content
  - "always include" -> check if required elements present
  - Case-insensitive matching
- Track rules checking in .tmp/hooks/client_rules_log.json

ALLOW always but warn about potential rule violations.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "client_rules_log.json"
CONTEXT_STATE_FILE = STATE_DIR / "context_state.json"
CLIENTS_DIR = PROJECT_ROOT / "clients"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": [], "stats": {"total": 0, "violations": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def load_context_state():
    try:
        if CONTEXT_STATE_FILE.exists():
            return json.loads(CONTEXT_STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def get_active_client():
    """Determine the currently active client from context state."""
    context_state = load_context_state()
    loaded_files = context_state.get("loaded_files", []) + context_state.get("loaded_contexts", [])

    for entry in loaded_files:
        path = entry if isinstance(entry, str) else entry.get("path", "")
        match = re.search(r'clients/([^/]+)/', path)
        if match:
            return match.group(1)

    return None


def extract_client_from_path(file_path):
    """Extract client name from file path."""
    match = re.search(r'clients/([^/]+)/', file_path)
    if match:
        return match.group(1)
    return None


def load_client_rules(client_name):
    """Load and parse client rules.md."""
    rules_file = CLIENTS_DIR / client_name / "rules.md"
    if not rules_file.exists():
        return None

    try:
        content = rules_file.read_text()
    except OSError:
        return None

    rules = {
        "words_to_avoid": [],
        "always_include": [],
        "raw_content": content,
    }

    # Extract "words to avoid" section
    avoid_section = re.search(
        r'(?:words?\s+to\s+avoid|avoid\s+(?:using|these|words)|don\'t\s+use|never\s+use)[:\s]*\n((?:[-*]\s+.+\n?)+)',
        content, re.IGNORECASE
    )
    if avoid_section:
        items = re.findall(r'[-*]\s+(.+)', avoid_section.group(1))
        rules["words_to_avoid"] = [item.strip().strip('"\'') for item in items]

    # Also look for inline avoid patterns
    inline_avoid = re.findall(
        r'(?:avoid|don\'t use|never use)[:\s]+["\']([^"\']+)["\']',
        content, re.IGNORECASE
    )
    rules["words_to_avoid"].extend(inline_avoid)

    # Extract "always include" section
    include_section = re.search(
        r'(?:always\s+include|must\s+include|required\s+elements?)[:\s]*\n((?:[-*]\s+.+\n?)+)',
        content, re.IGNORECASE
    )
    if include_section:
        items = re.findall(r'[-*]\s+(.+)', include_section.group(1))
        rules["always_include"] = [item.strip().strip('"\'') for item in items]

    # Also look for inline include patterns
    inline_include = re.findall(
        r'(?:always include|must include)[:\s]+["\']([^"\']+)["\']',
        content, re.IGNORECASE
    )
    rules["always_include"].extend(inline_include)

    return rules


def check_rules(content, rules):
    """Check content against client rules."""
    violations = []

    # Check words to avoid
    for word in rules.get("words_to_avoid", []):
        if re.search(re.escape(word), content, re.IGNORECASE):
            violations.append(f"Uses avoided word/phrase: '{word}'")

    # Check always include elements
    for required in rules.get("always_include", []):
        if not re.search(re.escape(required), content, re.IGNORECASE):
            violations.append(f"Missing required element: '{required}'")

    return violations


def handle_status():
    state = load_state()
    print("=== Client Rules Enforcer Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    active_client = get_active_client()
    print(f"Active client: {active_client or 'None detected'}")

    if active_client:
        rules = load_client_rules(active_client)
        if rules:
            print(f"\nLoaded rules for '{active_client}':")
            if rules["words_to_avoid"]:
                print(f"  Words to avoid: {', '.join(rules['words_to_avoid'][:10])}")
            if rules["always_include"]:
                print(f"  Always include: {', '.join(rules['always_include'][:10])}")
        else:
            print(f"  No rules.md found for '{active_client}'")

    stats = state.get("stats", {})
    print(f"\nTotal checks: {stats.get('total', 0)}")
    print(f"Violations found: {stats.get('violations', 0)}")

    checks = state.get("checks", [])
    if checks:
        print(f"\nRecent checks:")
        for c in checks[-5:]:
            status = "VIOLATION" if c.get("violations") else "OK"
            print(f"  [{status}] {c.get('filename', '?')} (client: {c.get('client', '?')})")
            for v in c.get("violations", [])[:3]:
                print(f"    - {v}")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Client rules enforcer state reset.")
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
    content = tool_input.get("content", "")

    # Determine which client to check rules for
    client_name = extract_client_from_path(file_path)
    if not client_name:
        # Check if writing to .tmp/ with an active client
        if ".tmp" in file_path:
            client_name = get_active_client()

    if not client_name:
        print(json.dumps({"decision": "ALLOW"}))
        return

    rules = load_client_rules(client_name)
    if not rules:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["stats"]["total"] = state["stats"].get("total", 0) + 1

    violations = check_rules(content, rules)

    check_record = {
        "filename": Path(file_path).name,
        "filepath": file_path,
        "client": client_name,
        "violations": violations,
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_record)
    state["checks"] = state["checks"][-50:]

    if violations:
        state["stats"]["violations"] = state["stats"].get("violations", 0) + 1
        save_state(state)
        violation_summary = "; ".join(violations[:5])
        if len(violations) > 5:
            violation_summary += f"; ...and {len(violations) - 5} more"
        print(json.dumps({
            "decision": "ALLOW",
            "reason": f"Client '{client_name}' rule violations: {violation_summary}"
        }))
    else:
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
