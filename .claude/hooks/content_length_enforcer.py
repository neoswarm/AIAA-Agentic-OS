#!/usr/bin/env python3
"""
Hook 26: Content Length Enforcer (PostToolUse on Write)

Enforces minimum content lengths by deliverable type:
- VSL scripts: 3000+ words
- Sales pages: 2000+ words
- Blog posts: 1200+ words
- Case studies: 1500+ words
- LinkedIn posts: 150-3000 chars
- Email sequences: 300+ words per email
- Newsletter: 800+ words
- YouTube scripts: 1500+ words
- Press releases: 500+ words

Only checks files in .tmp/. ALLOW always but warn if under minimum.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "content_length_log.json"

# Content type detection and minimum lengths
CONTENT_TYPES = {
    "vsl_script": {
        "patterns": [r"vsl.*script", r"vsl", r"video.*sales.*letter"],
        "min_words": 3000,
        "unit": "words",
        "description": "VSL Script",
    },
    "sales_page": {
        "patterns": [r"sales.*page", r"landing.*page", r"sales.*copy"],
        "min_words": 2000,
        "unit": "words",
        "description": "Sales Page",
    },
    "blog_post": {
        "patterns": [r"blog.*post", r"blog", r"article"],
        "min_words": 1200,
        "unit": "words",
        "description": "Blog Post",
    },
    "case_study": {
        "patterns": [r"case.*study", r"case_study", r"success.*story"],
        "min_words": 1500,
        "unit": "words",
        "description": "Case Study",
    },
    "linkedin_post": {
        "patterns": [r"linkedin.*post", r"linkedin", r"li_post"],
        "min_chars": 150,
        "max_chars": 3000,
        "unit": "chars",
        "description": "LinkedIn Post",
    },
    "email_sequence": {
        "patterns": [r"email.*sequence", r"email.*nurture", r"cold.*email", r"email"],
        "min_words_per_email": 300,
        "unit": "words_per_email",
        "description": "Email Sequence",
    },
    "newsletter": {
        "patterns": [r"newsletter", r"news.*letter"],
        "min_words": 800,
        "unit": "words",
        "description": "Newsletter",
    },
    "youtube_script": {
        "patterns": [r"youtube.*script", r"yt.*script", r"video.*script"],
        "min_words": 1500,
        "unit": "words",
        "description": "YouTube Script",
    },
    "press_release": {
        "patterns": [r"press.*release", r"pr_release"],
        "min_words": 500,
        "unit": "words",
        "description": "Press Release",
    },
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": [], "stats": {"total": 0, "warnings": 0, "passed": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def detect_content_type(filename):
    """Detect content type from filename."""
    filename_lower = filename.lower()
    for type_name, config in CONTENT_TYPES.items():
        for pattern in config["patterns"]:
            if re.search(pattern, filename_lower):
                return type_name, config
    return None, None


def count_emails(content):
    """Count number of emails in a sequence."""
    separators = [
        r'(?:Email|Subject)\s*(?:#|:)?\s*\d+',
        r'^##\s+Email\s+\d+',
        r'^Subject\s*(?:Line)?:',
    ]
    max_count = 0
    for pattern in separators:
        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
        max_count = max(max_count, len(matches))
    return max(max_count, 1)


def check_content_length(content, content_type, config):
    """Check if content meets length requirements."""
    issues = []
    metrics = {}

    word_count = len(content.split())
    char_count = len(content)
    metrics["word_count"] = word_count
    metrics["char_count"] = char_count

    unit = config.get("unit", "words")

    if unit == "words":
        min_words = config.get("min_words", 0)
        metrics["min_required"] = min_words
        if word_count < min_words:
            deficit = min_words - word_count
            issues.append(
                f"{config['description']}: {word_count} words "
                f"(minimum {min_words}, needs {deficit} more)"
            )

    elif unit == "chars":
        min_chars = config.get("min_chars", 0)
        max_chars = config.get("max_chars", float("inf"))
        metrics["min_chars"] = min_chars
        metrics["max_chars"] = max_chars if max_chars != float("inf") else None
        if char_count < min_chars:
            issues.append(
                f"{config['description']}: {char_count} chars "
                f"(minimum {min_chars})"
            )
        if char_count > max_chars:
            issues.append(
                f"{config['description']}: {char_count} chars "
                f"(maximum {max_chars}, too long by {char_count - max_chars})"
            )

    elif unit == "words_per_email":
        email_count = count_emails(content)
        words_per_email = word_count / email_count if email_count > 0 else word_count
        min_per = config.get("min_words_per_email", 0)
        metrics["email_count"] = email_count
        metrics["words_per_email"] = round(words_per_email)
        metrics["min_per_email"] = min_per
        if words_per_email < min_per:
            issues.append(
                f"{config['description']}: ~{round(words_per_email)} words/email "
                f"across {email_count} emails (minimum {min_per}/email)"
            )

    return issues, metrics


def handle_status():
    state = load_state()
    print("=== Content Length Enforcer Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"Total checks: {stats.get('total', 0)}")
    print(f"Passed: {stats.get('passed', 0)}")
    print(f"Warnings: {stats.get('warnings', 0)}")

    checks = state.get("checks", [])
    if checks:
        print(f"\nRecent checks:")
        for c in checks[-5:]:
            status = "PASS" if not c.get("issues") else "WARN"
            print(f"  [{status}] {c.get('filename', '?')} ({c.get('content_type', '?')})")
            print(f"    Words: {c.get('metrics', {}).get('word_count', '?')}")
            if c.get("issues"):
                for issue in c["issues"]:
                    print(f"    Issue: {issue}")
    else:
        print("\nNo content checked yet.")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Content length enforcer state reset.")
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

    # Only check files in .tmp/
    if ".tmp" not in file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    filename = Path(file_path).name
    content_type, config = detect_content_type(filename)

    if not content_type:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    issues, metrics = check_content_length(content, content_type, config)

    check_record = {
        "filename": filename,
        "filepath": file_path,
        "content_type": content_type,
        "metrics": metrics,
        "issues": issues,
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_record)
    # Keep last 50 checks
    state["checks"] = state["checks"][-50:]
    state["stats"]["total"] = state["stats"].get("total", 0) + 1

    if issues:
        state["stats"]["warnings"] = state["stats"].get("warnings", 0) + 1
        save_state(state)
        print(json.dumps({
            "decision": "ALLOW",
            "reason": "Content length issues: " + "; ".join(issues)
        }))
    else:
        state["stats"]["passed"] = state["stats"].get("passed", 0) + 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
