#!/usr/bin/env python3
"""
Hook 89: social_media_format_validator.py - PostToolUse on Write

Validates social media posts meet platform format requirements:
  - LinkedIn: 3000 chars max
  - Twitter/X: 280 chars max
  - Instagram: 2200 chars max
Also checks hashtag count and mention format.

Protocol:
  - PostToolUse: reads JSON from stdin, prints JSON to stdout
  - Returns {"decision": "ALLOW"} with optional format warnings

CLI Flags:
  --status  Show format validation stats
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
STATE_FILE = STATE_DIR / "social_media_format.json"

# Platform configs
PLATFORMS = {
    "linkedin": {
        "patterns": ["*linkedin*", "*li_post*", "*li_*"],
        "max_chars": 3000,
        "max_hashtags": 10,
        "ideal_hashtags": (3, 5),
        "mention_format": r'@\w+',
    },
    "twitter": {
        "patterns": ["*twitter*", "*tweet*", "*x_post*"],
        "max_chars": 280,
        "max_hashtags": 5,
        "ideal_hashtags": (1, 3),
        "mention_format": r'@\w+',
    },
    "instagram": {
        "patterns": ["*instagram*", "*ig_post*", "*ig_*", "*insta*"],
        "max_chars": 2200,
        "max_hashtags": 30,
        "ideal_hashtags": (5, 15),
        "mention_format": r'@\w+',
    },
    "facebook": {
        "patterns": ["*facebook*", "*fb_post*", "*fb_*"],
        "max_chars": 63206,
        "max_hashtags": 5,
        "ideal_hashtags": (1, 3),
        "mention_format": r'@\w+',
    },
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "checks": [],
        "violations": 0,
        "clean": 0,
        "total_checks": 0,
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["checks"] = state["checks"][-30:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def detect_platform(file_path):
    """Detect which social platform the content is for."""
    filename_lower = Path(file_path).name.lower()
    for platform, config in PLATFORMS.items():
        if any(fnmatch(filename_lower, pat) for pat in config["patterns"]):
            return platform, config
    return None, None


def validate_content(content, platform, config):
    """Validate content against platform rules."""
    issues = []
    metrics = {}

    # Character count
    char_count = len(content)
    metrics["char_count"] = char_count
    max_chars = config["max_chars"]

    if char_count > max_chars:
        over = char_count - max_chars
        issues.append(f"Over character limit: {char_count}/{max_chars} ({over} over)")

    # Hashtag analysis
    hashtags = re.findall(r'#\w+', content)
    hashtag_count = len(hashtags)
    metrics["hashtag_count"] = hashtag_count
    metrics["hashtags"] = hashtags[:10]

    if hashtag_count > config["max_hashtags"]:
        issues.append(f"Too many hashtags: {hashtag_count} (max: {config['max_hashtags']})")

    ideal_min, ideal_max = config["ideal_hashtags"]
    if hashtag_count < ideal_min and char_count > 50:
        issues.append(f"Few hashtags: {hashtag_count} (ideal: {ideal_min}-{ideal_max})")
    elif hashtag_count > ideal_max:
        issues.append(f"Many hashtags: {hashtag_count} (ideal: {ideal_min}-{ideal_max})")

    # Mention format
    mentions = re.findall(config["mention_format"], content)
    metrics["mentions"] = len(mentions)

    # Platform-specific checks
    if platform == "twitter" and char_count > 250:
        # Check if URLs are included (they count as 23 chars on Twitter)
        urls = re.findall(r'https?://\S+', content)
        if urls:
            effective_chars = char_count - sum(len(u) for u in urls) + (23 * len(urls))
            if effective_chars > 280:
                issues.append(f"Exceeds limit even with URL shortening (~{effective_chars} chars)")

    if platform == "linkedin":
        # Check for hook (first line should be compelling)
        first_line = content.split("\n")[0].strip()
        if len(first_line) > 150:
            issues.append("First line too long for LinkedIn hook (keep under 150 chars)")

    if platform == "instagram":
        # Check for line breaks (Instagram strips multiple newlines)
        if "\n\n\n" in content:
            issues.append("Triple line breaks will be collapsed on Instagram")

    return issues, metrics


def handle_status():
    state = load_state()
    print("Social Media Format Validator Status")
    print(f"  Total checks: {state['total_checks']}")
    print(f"  Clean posts: {state['clean']}")
    print(f"  Violations: {state['violations']}")
    if state["checks"]:
        print("  Recent checks:")
        for c in state["checks"][-5:]:
            issues = c.get("issues", [])
            platform = c.get("platform", "?")
            status = f"{len(issues)} issues" if issues else "valid"
            print(f"    [{status}] {c.get('file', 'unknown')} ({platform})")
    sys.exit(0)


def handle_reset():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "checks": [], "violations": 0, "clean": 0, "total_checks": 0,
    }))
    print("Social Media Format Validator: State reset.")
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

    platform, config = detect_platform(file_path)
    if not platform or not content:
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    state["total_checks"] += 1

    issues, metrics = validate_content(content, platform, config)

    file_name = Path(file_path).name
    check_entry = {
        "file": file_name,
        "platform": platform,
        "issues": issues,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_entry)

    if issues:
        state["violations"] += 1
        save_state(state)
        reason = f"{platform.title()} format issues in {file_name}: " + "; ".join(issues[:4])
        print(json.dumps({"decision": "ALLOW", "reason": reason}))
    else:
        state["clean"] += 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
