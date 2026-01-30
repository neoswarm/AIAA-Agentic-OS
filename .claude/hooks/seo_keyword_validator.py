#!/usr/bin/env python3
"""
Hook 85: seo_keyword_validator.py - PostToolUse on Write

For blog content, checks keyword density, SEO basics (title tag, meta description,
H1/H2 structure, keyword density 1-3%, internal links).

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional SEO warnings

CLI Flags:
  --status  Show SEO validation stats
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
STATE_FILE = STATE_DIR / "seo_validation.json"

# File patterns for SEO checking
SEO_PATTERNS = ["*blog*", "*article*", "*post*", "*seo*", "*content*"]

IDEAL_KEYWORD_DENSITY_MIN = 0.01  # 1%
IDEAL_KEYWORD_DENSITY_MAX = 0.03  # 3%
IDEAL_TITLE_LENGTH = (30, 60)     # Characters
IDEAL_META_LENGTH = (120, 160)    # Characters


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


def is_seo_content(file_path):
    filename_lower = Path(file_path).name.lower()
    return any(fnmatch(filename_lower, pat) for pat in SEO_PATTERNS)


def check_heading_structure(content):
    """Check for proper H1/H2/H3 heading structure."""
    issues = []
    h1_count = len(re.findall(r'^#\s+', content, re.MULTILINE))
    h2_count = len(re.findall(r'^##\s+', content, re.MULTILINE))
    h3_count = len(re.findall(r'^###\s+', content, re.MULTILINE))

    if h1_count == 0:
        issues.append("Missing H1 heading (title)")
    elif h1_count > 1:
        issues.append(f"Multiple H1 headings ({h1_count}) - should have exactly 1")

    if h2_count == 0:
        issues.append("No H2 subheadings - content needs structure")
    elif h2_count < 3 and len(content) > 2000:
        issues.append(f"Only {h2_count} H2 headings for long content - consider adding more")

    return issues, {"h1": h1_count, "h2": h2_count, "h3": h3_count}


def check_meta_elements(content):
    """Check for title and meta description hints."""
    issues = []
    lines = content.split("\n")

    # Check first H1 as title
    h1_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
    if h1_match:
        title = h1_match.group(1).strip()
        if len(title) < IDEAL_TITLE_LENGTH[0]:
            issues.append(f"Title too short ({len(title)} chars, ideal: {IDEAL_TITLE_LENGTH[0]}-{IDEAL_TITLE_LENGTH[1]})")
        elif len(title) > IDEAL_TITLE_LENGTH[1]:
            issues.append(f"Title too long ({len(title)} chars, ideal: {IDEAL_TITLE_LENGTH[0]}-{IDEAL_TITLE_LENGTH[1]})")
    else:
        issues.append("No title (H1) found")

    # Check for meta description (usually in frontmatter or first paragraph)
    has_meta = bool(re.search(r'(?:meta|description|excerpt|summary)\s*:', content[:500], re.IGNORECASE))
    if not has_meta:
        issues.append("No meta description detected - add frontmatter or summary")

    return issues


def check_keyword_density(content):
    """Analyze potential keyword density."""
    issues = []
    # Extract words
    text = re.sub(r'[#*_\[\](){}]', '', content)
    words = text.lower().split()
    total_words = len(words)

    if total_words < 100:
        return issues, {}

    # Find most common 2-3 word phrases as potential keywords
    from collections import Counter
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)
               if len(words[i]) > 3 and len(words[i+1]) > 3]
    common = Counter(bigrams).most_common(5)

    keyword_info = {}
    for phrase, count in common:
        density = count / (total_words / 2)  # Approximate
        keyword_info[phrase] = {"count": count, "density": round(density, 4)}
        if density > IDEAL_KEYWORD_DENSITY_MAX:
            issues.append(f"Keyword '{phrase}' may be over-optimized ({density:.1%} density)")

    return issues, keyword_info


def check_internal_links(content):
    """Check for presence of internal links."""
    issues = []
    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)

    if not links and len(content) > 1000:
        issues.append("No links found in content - consider adding internal/external links")

    return issues, len(links)


def handle_status():
    state = load_state()
    print("SEO Keyword Validator Status")
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
    print("SEO Keyword Validator: State reset.")
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

    if not is_seo_content(file_path) or not content:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    all_issues = []

    heading_issues, heading_stats = check_heading_structure(content)
    all_issues.extend(heading_issues)

    meta_issues = check_meta_elements(content)
    all_issues.extend(meta_issues)

    kw_issues, kw_info = check_keyword_density(content)
    all_issues.extend(kw_issues)

    link_issues, link_count = check_internal_links(content)
    all_issues.extend(link_issues)

    file_name = Path(file_path).name
    check_entry = {
        "file": file_name,
        "issues": all_issues,
        "heading_stats": heading_stats,
        "link_count": link_count,
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_entry)

    if all_issues:
        state["issues_found"] += 1
        save_state(state)
        reason = f"SEO issues in {file_name}: " + "; ".join(all_issues[:5])
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        state["clean_writes"] += 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
