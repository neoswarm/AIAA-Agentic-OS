#!/usr/bin/env python3
"""
secrets_guard.py - PreToolUse hook on Write and Edit tools

Prevents accidental writes or edits to sensitive files (.env, credentials.json,
token.pickle, etc.) and scans content being written for API key patterns.

Protected files:
  - .env, .env.local, .env.production
  - credentials.json
  - token.pickle
  - Any path containing 'secrets' or 'private_key'

Allowed exceptions:
  - .env.example (template file)

Content scanning patterns:
  - sk-, key-, AKIA, ghp_, ghu_, xoxb-, xoxp-

Hook Protocol:
  - PreToolUse: reads JSON from stdin, exits 0 (allow) or 2 (block)
  - Messages to user via sys.stderr.write()
  - NEVER prints to stdout in PreToolUse mode

CLI Flags:
  --status  Show protected file patterns
  --reset   N/A (stateless hook)
"""

import json
import sys
import os
import re
from pathlib import Path

# Files blocked by exact filename
BLOCKED_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "token.pickle",
}

# Allowed exceptions (exact filenames)
ALLOWED_FILENAMES = {
    ".env.example",
}

# Path substrings that trigger blocking
BLOCKED_PATH_PATTERNS = [
    "secrets",
    "private_key",
]

# API key patterns to scan for in content
API_KEY_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', "OpenAI/Stripe-style API key (sk-...)"),
    (r'key-[a-zA-Z0-9]{20,}', "Generic API key (key-...)"),
    (r'AKIA[A-Z0-9]{16}', "AWS Access Key ID (AKIA...)"),
    (r'ghp_[a-zA-Z0-9]{36,}', "GitHub Personal Access Token (ghp_...)"),
    (r'ghu_[a-zA-Z0-9]{36,}', "GitHub User Token (ghu_...)"),
    (r'xoxb-[a-zA-Z0-9\-]+', "Slack Bot Token (xoxb-...)"),
    (r'xoxp-[a-zA-Z0-9\-]+', "Slack User Token (xoxp-...)"),
]


def is_blocked_path(file_path):
    """Check if the file path refers to a protected file."""
    if not file_path:
        return False, ""

    p = Path(file_path)
    filename = p.name

    # Allow exceptions first
    if filename in ALLOWED_FILENAMES:
        return False, ""

    # Check exact filenames
    if filename in BLOCKED_FILENAMES:
        return True, f"Protected file: {filename}"

    # Check path patterns
    path_lower = file_path.lower()
    for pattern in BLOCKED_PATH_PATTERNS:
        if pattern in path_lower:
            return True, f"Path contains '{pattern}'"

    return False, ""


def scan_content(content):
    """Scan content for API key patterns. Returns list of findings."""
    if not content:
        return []

    findings = []
    for pattern, description in API_KEY_PATTERNS:
        if re.search(pattern, content):
            findings.append(description)
    return findings


def handle_status():
    """Print protected file info and exit."""
    print("Secrets Guard Status")
    print("  Protected filenames:")
    for f in sorted(BLOCKED_FILENAMES):
        print(f"    - {f}")
    print("  Allowed exceptions:")
    for f in sorted(ALLOWED_FILENAMES):
        print(f"    - {f}")
    print("  Blocked path patterns:")
    for p in BLOCKED_PATH_PATTERNS:
        print(f"    - *{p}*")
    print("  Content scan patterns:")
    for _, desc in API_KEY_PATTERNS:
        print(f"    - {desc}")
    sys.exit(0)


def handle_reset():
    """Stateless hook, nothing to reset."""
    print("Secrets Guard: Stateless hook, nothing to reset.")
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

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only act on Write and Edit tools
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    # Get file path from tool input
    file_path = tool_input.get("file_path", "")

    # Check if file is protected
    blocked, reason = is_blocked_path(file_path)
    if blocked:
        sys.stderr.write(
            f"[Secrets Guard] BLOCKED: Cannot write to {file_path}\n"
            f"  Reason: {reason}\n"
            f"  This file may contain sensitive credentials.\n"
            f"  To safely set API keys, use the Settings page in your dashboard or ask Claude to help you configure them.\n"
            f"  To create a template, write to .env.example instead.\n"
        )
        sys.exit(2)

    # Scan content for API key patterns (Write tool only)
    if tool_name == "Write":
        content = tool_input.get("content", "")
        findings = scan_content(content)
        if findings:
            sys.stderr.write(
                f"[Secrets Guard] BLOCKED: Content contains API key patterns:\n"
            )
            for finding in findings:
                sys.stderr.write(f"    - {finding}\n")
            sys.stderr.write(
                f"  Do not write secrets directly into files.\n"
                f"  To safely set API keys, use the Settings page in your dashboard or ask Claude to help you configure them.\n"
                f"  File: {file_path}\n"
            )
            sys.exit(2)

    # Also scan Edit tool's new_string content
    if tool_name == "Edit":
        new_string = tool_input.get("new_string", "")
        findings = scan_content(new_string)
        if findings:
            sys.stderr.write(
                f"[Secrets Guard] BLOCKED: Edit content contains API key patterns:\n"
            )
            for finding in findings:
                sys.stderr.write(f"    - {finding}\n")
            sys.stderr.write(
                f"  Do not write secrets directly into files.\n"
                f"  To safely set API keys, use the Settings page in your dashboard or ask Claude to help you configure them.\n"
                f"  File: {file_path}\n"
            )
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
