#!/usr/bin/env python3
"""
doe_enforcer.py - DUAL MODE hook (PostToolUse/Read + PreToolUse/Bash)

Enforces the DOE (Directive-Orchestration-Execution) pattern by tracking which
directives and scripts have been read during a session. When an execution script
is about to run, checks that the corresponding directive was read first.

Dual Mode Detection:
  - If "tool_response" key exists in stdin JSON -> PostToolUse mode
  - If "tool_response" key does NOT exist -> PreToolUse mode

PostToolUse/Read mode:
  - Logs directive reads (directives/*.md) to session_reads["directives_read"]
  - Logs script reads (execution/*.py and .claude/skills/*/*.py) to session_reads["scripts_read"]
  - Always returns {"decision": "ALLOW"}

PreToolUse/Bash mode:
  - When command runs python3 execution/*.py or .claude/skills/*/*.py, checks for matching directive
  - Blocks if directives were read but none match the script
  - Warns (doesn't block) if no directives were read at all (fresh session)

State: .tmp/hooks/session_reads.json

CLI Flags:
  --status  Show what has been read this session
  --reset   Clear session reads
"""

import json
import sys
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = BASE_DIR / ".tmp" / "hooks" / "session_reads.json"

# Prefixes to strip from script names when deriving directive keywords
STRIP_PREFIXES = ["generate_", "create_", "deploy_", "run_"]


def load_state():
    """Load session reads state."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"directives_read": [], "scripts_read": []}


def save_state(state):
    """Save session reads state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def extract_script_name(command):
    """Extract script filename from a bash command like 'python3 execution/foo.py --args'."""
    match = re.search(r'python3?\s+(?:\S*/)?(?:execution|\.claude/skills/[^/\s]+)/(\S+\.py)', command)
    if match:
        return match.group(1)
    return None


def derive_keywords(script_name):
    """Derive keyword set from a script name for directive matching.

    Example: generate_vsl_funnel.py -> {'vsl', 'funnel'}
    """
    # Remove .py extension
    name = script_name.replace(".py", "")

    # Strip known prefixes
    for prefix in STRIP_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break

    # Split into keywords
    keywords = set(name.split("_"))
    # Remove very short/common words
    keywords = {k for k in keywords if len(k) > 2}
    return keywords


def check_directive_match(keywords, directives_read):
    """Check if any read directive matches the script keywords."""
    if not keywords:
        return True  # Can't determine, allow

    for directive in directives_read:
        directive_lower = directive.lower().replace(".md", "").replace("-", "_")
        directive_words = set(directive_lower.split("_"))
        # Match if at least one keyword overlaps
        if keywords & directive_words:
            return True
    return False


def handle_status():
    """Print session reads status and exit."""
    state = load_state()
    print("DOE Enforcer Status")
    print(f"  Directives read ({len(state.get('directives_read', []))}):")
    for d in state.get("directives_read", []):
        print(f"    - {d}")
    print(f"  Scripts read ({len(state.get('scripts_read', []))}):")
    for s in state.get("scripts_read", []):
        print(f"    - {s}")
    sys.exit(0)


def handle_reset():
    """Clear session reads and exit."""
    save_state({"directives_read": [], "scripts_read": []})
    print("DOE Enforcer: Session reads cleared.")
    sys.exit(0)


def handle_post_tool_use(data):
    """PostToolUse mode: track reads of directives and scripts."""
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()

    # Check if it's a directive
    if "directives/" in file_path:
        filename = Path(file_path).name
        if filename not in state["directives_read"]:
            state["directives_read"].append(filename)
            save_state(state)

    # Check if it's an execution script (legacy or v5.0 skills)
    if "execution/" in file_path or "/.claude/skills/" in file_path:
        filename = Path(file_path).name
        if filename not in state["scripts_read"]:
            state["scripts_read"].append(filename)
            save_state(state)

    print(json.dumps({"decision": "ALLOW"}))


def handle_pre_tool_use(data):
    """PreToolUse mode: check if directive was read before running script."""
    tool_input = data.get("tool_input", {})
    command = tool_input.get("command", "")

    # Only check commands that run execution scripts
    script_name = extract_script_name(command)
    if not script_name:
        sys.exit(0)

    state = load_state()
    directives_read = state.get("directives_read", [])

    # If no directives have been read at all (fresh session), just warn
    if not directives_read:
        sys.stderr.write(
            f"[DOE Enforcer] NOTE: Running {script_name} without reading any instructions first.\n"
            f"  For best results, review the instructions for this script before running it.\n"
            f"  Ask Claude: 'Show me the instructions for {script_name}' before running it.\n"
        )
        sys.exit(0)

    # Check if any read directive matches this script
    keywords = derive_keywords(script_name)
    if not check_directive_match(keywords, directives_read):
        sys.stderr.write(
            f"[DOE Enforcer] BLOCKED: No matching instructions found for {script_name}.\n"
            f"  Script keywords: {', '.join(sorted(keywords))}\n"
            f"  Instructions reviewed: {', '.join(directives_read)}\n"
            f"  Please review the relevant instructions before running this script.\n"
            f"  Ask Claude: 'Show me the instructions for {script_name}' before running it.\n"
        )
        sys.exit(2)

    sys.exit(0)


def main():
    # CLI flags
    if "--status" in sys.argv:
        handle_status()
    if "--reset" in sys.argv:
        handle_reset()

    # Read hook input from stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, IOError):
        sys.exit(0)

    # Detect mode: PostToolUse has "tool_result", PreToolUse does not
    if "tool_response" in data:
        handle_post_tool_use(data)
    else:
        handle_pre_tool_use(data)


if __name__ == "__main__":
    main()
