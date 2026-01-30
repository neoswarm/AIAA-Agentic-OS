#!/usr/bin/env python3
"""
output_quality_gate.py - PostToolUse hook on Write tool

Validates quality of files written to the .tmp/ directory by checking word count,
section count, and required keywords based on the file pattern.

Quality rules by file pattern:
  *vsl*.md:      min 2000 words, 8 sections, Hook/Problem/Solution/Offer/CTA
  *email*.md:    min 300 words, 3 sections, Subject/CTA
  *research*.md: min 1500 words, 5 sections, Summary/Sources/Findings
  *report*.md:   min 2000 words, 5 sections, Summary/Recommendations
  *blog*.md:     min 1000 words, 4 sections, Introduction/Conclusion
  *sales*.md:    min 1500 words, 6 sections, Headline/Problem/Solution/CTA
  *.md (default): min 500 words, 3 sections

Hook Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} or {"decision": "BLOCK", "reason": "..."}

CLI Flags:
  --status  Show quality rules
  --reset   N/A (stateless hook)
"""

import json
import sys
import os
import re
from pathlib import Path
from fnmatch import fnmatch

BASE_DIR = Path(os.path.expanduser("/Users/lucasnolan/Agentic OS"))
TMP_DIR = BASE_DIR / ".tmp"

# Quality rules: (pattern, min_words, min_sections, required_keywords)
QUALITY_RULES = [
    ("*vsl*.md", 2000, 8, ["Hook", "Problem", "Solution", "Offer", "CTA"]),
    ("*email*.md", 300, 3, ["Subject", "CTA"]),
    ("*research*.md", 1500, 5, ["Summary", "Sources", "Findings"]),
    ("*report*.md", 2000, 5, ["Summary", "Recommendations"]),
    ("*blog*.md", 1000, 4, ["Introduction", "Conclusion"]),
    ("*sales*.md", 1500, 6, ["Headline", "Problem", "Solution", "CTA"]),
]

# Default rule for any .md in .tmp/
DEFAULT_RULE = ("*.md", 500, 3, [])


def strip_markdown(text):
    """Strip markdown syntax for word counting."""
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code
    text = re.sub(r'`[^`]+`', '', text)
    # Remove links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove images
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove markdown emphasis markers
    text = re.sub(r'[*_~]+', '', text)
    # Remove header markers
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    return text


def count_words(text):
    """Count words in text after stripping markdown."""
    cleaned = strip_markdown(text)
    words = cleaned.split()
    return len(words)


def count_sections(text):
    """Count markdown sections (lines starting with #)."""
    lines = text.split('\n')
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            count += 1
    return count


def check_keywords(text, keywords):
    """Check which required keywords are present (case-insensitive)."""
    text_lower = text.lower()
    missing = []
    for kw in keywords:
        if kw.lower() not in text_lower:
            missing.append(kw)
    return missing


def get_rule(filename):
    """Get the quality rule for a filename."""
    filename_lower = filename.lower()
    for pattern, min_words, min_sections, keywords in QUALITY_RULES:
        if fnmatch(filename_lower, pattern):
            return (pattern, min_words, min_sections, keywords)
    # Default for .md files
    if filename_lower.endswith(".md"):
        return DEFAULT_RULE
    return None


def validate_content(content, rule):
    """Validate content against a quality rule. Returns list of issues."""
    pattern, min_words, min_sections, required_keywords = rule
    issues = []

    # Word count
    word_count = count_words(content)
    if word_count < min_words:
        issues.append(
            f"Word count: {word_count} (minimum: {min_words})"
        )

    # Section count
    section_count = count_sections(content)
    if section_count < min_sections:
        issues.append(
            f"Section count: {section_count} (minimum: {min_sections})"
        )

    # Required keywords
    if required_keywords:
        missing = check_keywords(content, required_keywords)
        if missing:
            issues.append(
                f"Missing keywords: {', '.join(missing)}"
            )

    return issues


def handle_status():
    """Print quality rules and exit."""
    print("Output Quality Gate Status")
    print("  Quality rules for .tmp/ files:")
    for pattern, min_words, min_sections, keywords in QUALITY_RULES:
        kw_str = ", ".join(keywords) if keywords else "(none)"
        print(f"    {pattern}:")
        print(f"      min_words={min_words}, min_sections={min_sections}")
        print(f"      keywords: {kw_str}")
    pattern, min_words, min_sections, keywords = DEFAULT_RULE
    print(f"    {pattern} (default):")
    print(f"      min_words={min_words}, min_sections={min_sections}")
    sys.exit(0)


def handle_reset():
    """Stateless hook, nothing to reset."""
    print("Output Quality Gate: Stateless hook, nothing to reset.")
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
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only act on Write tool
    if tool_name != "Write":
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")

    # Only check files in .tmp/ directory
    try:
        file_p = Path(file_path)
        if not str(file_p).startswith(str(TMP_DIR)):
            print(json.dumps({"decision": "ALLOW"}))
            return
    except (TypeError, ValueError):
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Skip non-md files
    if not file_path.endswith(".md"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Get the quality rule for this file
    filename = Path(file_path).name
    rule = get_rule(filename)
    if not rule:
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Get content - from tool_result if available, otherwise from tool_input
    content = data.get("tool_result", "")
    if not content:
        content = tool_input.get("content", "")

    if not content:
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Validate
    issues = validate_content(content, rule)

    if issues:
        pattern = rule[0]
        reason = (
            f"Quality gate failed for {filename} (rule: {pattern}):\n"
            + "\n".join(f"  - {issue}" for issue in issues)
            + "\n  Improve the content and try again."
        )
        print(json.dumps({"decision": "BLOCK", "reason": reason}))
    else:
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
