#!/usr/bin/env python3
"""
Hook 38: Markdown Lint Validator (PostToolUse on Write)

After writing .md files to .tmp/:
- Check for common markdown issues:
  - Unclosed bold/italic markers (odd number of ** or *)
  - Headers without space after # (#No space)
  - Broken links [text]( without closing )
  - Empty sections (header followed immediately by another header)
  - Lines exceeding 500 chars (likely unformatted content dump)

ALLOW always but warn about issues found.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "markdown_lint_log.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"checks": [], "stats": {"total": 0, "warnings": 0, "clean": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def check_unclosed_bold(content):
    """Check for unclosed bold markers (**)."""
    issues = []
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        # Skip code blocks
        if line.strip().startswith("```"):
            continue
        # Count ** occurrences (not inside code spans)
        # Remove inline code first
        clean_line = re.sub(r'`[^`]+`', '', line)
        bold_count = clean_line.count("**")
        if bold_count % 2 != 0:
            issues.append(f"Line {i}: Unclosed bold marker (**)")
    return issues


def check_unclosed_italic(content):
    """Check for unclosed italic markers (single *)."""
    issues = []
    lines = content.split("\n")
    in_code_block = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        # Remove inline code and bold markers
        clean_line = re.sub(r'`[^`]+`', '', line)
        clean_line = re.sub(r'\*\*[^*]+\*\*', '', clean_line)
        # Remove list markers
        clean_line = re.sub(r'^\s*\*\s', '', clean_line)
        # Remove horizontal rules
        if re.match(r'^\s*\*\s*\*\s*\*', clean_line):
            continue
        # Count remaining single *
        single_stars = len(re.findall(r'(?<!\*)\*(?!\*)', clean_line))
        if single_stars % 2 != 0:
            issues.append(f"Line {i}: Possible unclosed italic marker (*)")
    return issues


def check_headers(content):
    """Check for headers without space after #."""
    issues = []
    lines = content.split("\n")
    in_code_block = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        # Check for # without space (but not ## patterns or #! shebang)
        if re.match(r'^#{1,6}[^\s#]', line.strip()):
            issues.append(f"Line {i}: Header missing space after # ({line.strip()[:40]})")
    return issues


def check_broken_links(content):
    """Check for broken markdown links."""
    issues = []
    lines = content.split("\n")
    in_code_block = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        # Check for [text]( without closing )
        opens = re.findall(r'\[([^\]]*)\]\(', line)
        closes = re.findall(r'\[([^\]]*)\]\([^\)]*\)', line)
        if len(opens) > len(closes):
            issues.append(f"Line {i}: Possible broken link (unclosed parenthesis)")
    return issues


def check_empty_sections(content):
    """Check for empty sections (header immediately followed by another header)."""
    issues = []
    lines = content.split("\n")
    prev_header = None
    prev_header_line = 0
    in_code_block = False

    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        is_header = bool(re.match(r'^#{1,6}\s', line.strip()))
        is_blank = line.strip() == ""

        if is_header:
            if prev_header and (i - prev_header_line <= 2):
                issues.append(
                    f"Line {prev_header_line}: Empty section "
                    f"({prev_header.strip()[:40]})"
                )
            prev_header = line
            prev_header_line = i
        elif not is_blank:
            prev_header = None

    return issues


def check_long_lines(content):
    """Check for very long lines (likely unformatted dumps)."""
    issues = []
    lines = content.split("\n")
    long_count = 0
    in_code_block = False

    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        if len(line) > 500:
            long_count += 1
            if long_count <= 3:
                issues.append(
                    f"Line {i}: {len(line)} chars (may be unformatted content)"
                )

    if long_count > 3:
        issues.append(f"...and {long_count - 3} more long lines")

    return issues


def lint_markdown(content, filename):
    """Run all markdown lint checks."""
    all_issues = []

    all_issues.extend(check_unclosed_bold(content))
    all_issues.extend(check_headers(content))
    all_issues.extend(check_broken_links(content))
    all_issues.extend(check_empty_sections(content))
    all_issues.extend(check_long_lines(content))

    # Only check italic if there are very few issues (it's noisy)
    if len(all_issues) < 5:
        italic_issues = check_unclosed_italic(content)
        all_issues.extend(italic_issues[:2])  # Limit italic warnings

    return all_issues


def handle_status():
    state = load_state()
    print("=== Markdown Lint Validator Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"Total checks: {stats.get('total', 0)}")
    print(f"Clean files: {stats.get('clean', 0)}")
    print(f"Files with warnings: {stats.get('warnings', 0)}")

    checks = state.get("checks", [])
    if checks:
        print(f"\nRecent checks:")
        for c in checks[-10:]:
            issue_count = len(c.get("issues", []))
            status = "CLEAN" if issue_count == 0 else f"{issue_count} issues"
            print(f"  [{status}] {c.get('filename', '?')}")
            for issue in c.get("issues", [])[:3]:
                print(f"    - {issue}")
    else:
        print("\nNo markdown files checked yet.")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Markdown lint validator state reset.")
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

    # Only check .md files in .tmp/
    if not file_path.endswith(".md") or ".tmp" not in file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    filename = Path(file_path).name
    state = load_state()
    state["stats"]["total"] = state["stats"].get("total", 0) + 1

    issues = lint_markdown(content, filename)

    check_record = {
        "filename": filename,
        "filepath": file_path,
        "issues": issues,
        "timestamp": datetime.now().isoformat(),
    }
    state["checks"].append(check_record)
    state["checks"] = state["checks"][-50:]

    if issues:
        state["stats"]["warnings"] = state["stats"].get("warnings", 0) + 1
        save_state(state)
        # Limit warning message length
        issue_summary = "; ".join(issues[:5])
        if len(issues) > 5:
            issue_summary += f"; ...and {len(issues) - 5} more"
        print(json.dumps({
            "decision": "ALLOW",
            "reason": f"Markdown issues in {filename}: {issue_summary}"
        }))
    else:
        state["stats"]["clean"] = state["stats"].get("clean", 0) + 1
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
