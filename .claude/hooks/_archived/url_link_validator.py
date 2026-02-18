#!/usr/bin/env python3
"""
Hook 83: url_link_validator.py - PostToolUse on Write

Checks URLs in generated content for proper formatting, placeholder URLs,
and broken markdown link syntax.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional URL warnings

CLI Flags:
  --status  Show URL validation stats
  --reset   Clear state
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/Users/lucasnolan/Agentic OS")
STATE_DIR = BASE_DIR / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "url_validation.json"

# Placeholder URL patterns
PLACEHOLDER_PATTERNS = [
    r'example\.com',
    r'yoursite\.com',
    r'yourdomain\.com',
    r'your-?website\.com',
    r'placeholder\.com',
    r'acme\.com',
    r'company\.com',
    r'test\.com',
    r'sample\.com',
    r'xxx+\.com',
    r'https?://\[',
    r'https?://\{',
    r'https?://INSERT',
    r'https?://TODO',
    r'https?://REPLACE',
    r'https?://your-',
]

# URL regex
URL_REGEX = re.compile(
    r'https?://[^\s\)>\]"\'`]+',
    re.IGNORECASE
)

# Markdown link regex
MD_LINK_REGEX = re.compile(r'\[([^\]]*)\]\(([^)]*)\)')

# Broken markdown link patterns
BROKEN_LINK_PATTERNS = [
    r'\[[^\]]*\]\s+\(',           # Space between ] and (
    r'\[[^\]]*\]\([^)]*$',        # Missing closing paren
    r'\[\]\(',                     # Empty link text
    r'\[[^\]]*\]\(\)',             # Empty URL
    r'\[[^\]]*\]\(#?\)',           # Only hash or empty
]


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "checks": [],
        "issues_found": 0,
        "clean_writes": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["checks"] = state["checks"][-30:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def find_placeholder_urls(content):
    """Find placeholder/dummy URLs in content."""
    found = []
    urls = URL_REGEX.findall(content)
    for url in urls:
        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                found.append(url[:80])
                break
    return list(set(found))


def find_malformed_urls(content):
    """Find malformed URLs."""
    issues = []
    urls = URL_REGEX.findall(content)
    for url in urls:
        # Check for common malformations
        if url.count('//') > 1 and '://' not in url[url.index('//')+2:]:
            pass  # Some URLs legitimately have //
        if url.endswith(('.', ',', ';', ':')):
            issues.append(f"URL ends with punctuation: {url[:60]}")
        if ' ' in url:
            issues.append(f"URL contains space: {url[:60]}")
        if url.count('(') != url.count(')'):
            issues.append(f"URL has unbalanced parens: {url[:60]}")
    return issues


def find_broken_md_links(content):
    """Find broken markdown link syntax."""
    issues = []
    for pattern in BROKEN_LINK_PATTERNS:
        matches = re.findall(pattern, content, re.MULTILINE)
        if matches:
            for m in matches[:3]:
                if isinstance(m, str):
                    issues.append(f"Broken markdown link syntax: {m[:60]}")
                else:
                    issues.append("Broken markdown link syntax detected")
    return issues


def handle_status():
    state = load_state()
    print("URL/Link Validator Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Clean writes: {state['clean_writes']}")
    print(f"  Issues found: {state['issues_found']}")
    if state["checks"]:
        print("  Recent checks:")
        for c in state["checks"][-5:]:
            issues = c.get("issues", [])
            status = f"{len(issues)} issues" if issues else "clean"
            print(f"    [{status}] {c.get('file', 'unknown')}")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "checks": [], "issues_found": 0,
        "clean_writes": 0, "total_checks": 0,
    }))
    print("URL/Link Validator: State reset.")
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

    if not content:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    all_issues = []

    # Check for placeholder URLs
    placeholders = find_placeholder_urls(content)
    if placeholders:
        all_issues.append(f"Placeholder URLs: {', '.join(placeholders[:3])}")

    # Check for malformed URLs
    malformed = find_malformed_urls(content)
    all_issues.extend(malformed[:3])

    # Check for broken markdown links
    broken_links = find_broken_md_links(content)
    all_issues.extend(broken_links[:3])

    file_name = Path(file_path).name
    check_entry = {
        "file": file_name,
        "issues": all_issues,
        "url_count": len(URL_REGEX.findall(content)),
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_entry)

    if all_issues:
        state["issues_found"] += 1
        save_state(state)
        reason = f"URL/Link issues in {file_name}: " + "; ".join(all_issues[:5])
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        state["clean_writes"] += 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
