#!/usr/bin/env python3
"""
Hook 119: quality_trend_analyzer.py (PostToolUse on Write)
Purpose: Detect quality degradation over time.
Logic: Track quality metrics (word count, section count, completeness) per
deliverable type. Compare against historical averages. Warn if current
output is below trend.

Protocol:
  - PostToolUse: prints JSON to stdout {"decision": "ALLOW"}
  - Supports --status and --reset CLI flags
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

STATE_DIR = Path(".tmp/hooks")
STATE_FILE = STATE_DIR / "quality_trends.json"

# Quality metrics weights
QUALITY_WEIGHTS = {
    "word_count_ratio": 0.3,    # vs historical average
    "section_count_ratio": 0.2,  # vs historical average
    "has_headings": 0.15,
    "has_structure": 0.15,
    "completeness": 0.2,
}

# Deliverable type detection
DELIVERABLE_PATTERNS = {
    "vsl_script": r'vsl[_\s]script',
    "sales_page": r'sales[_\s]page',
    "email_sequence": r'email[_\s]sequence',
    "cold_email": r'cold[_\s]email',
    "blog_post": r'blog[_\s]post',
    "research": r'research',
    "proposal": r'proposal',
    "newsletter": r'newsletter',
}


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "deliverable_types": {},
        "quality_scores": [],
        "degradation_warnings": [],
        "total_analyzed": 0
    }


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def detect_deliverable_type(file_path):
    """Detect deliverable type from path."""
    path_lower = file_path.lower()
    for dtype, pattern in DELIVERABLE_PATTERNS.items():
        if re.search(pattern, path_lower):
            return dtype
    return "general"


def compute_metrics(content):
    """Compute quality metrics from content."""
    if not content:
        return {"word_count": 0, "section_count": 0, "has_headings": False,
                "has_structure": False, "completeness_score": 0}

    words = content.split()
    word_count = len(words)

    # Count markdown headings
    headings = re.findall(r'^#+\s', content, re.MULTILINE)
    section_count = len(headings)

    # Check for structural elements
    has_headings = section_count > 0
    has_bullets = bool(re.search(r'^[\s]*[-*]\s', content, re.MULTILINE))
    has_numbered = bool(re.search(r'^[\s]*\d+[\.\)]\s', content, re.MULTILINE))
    has_bold = "**" in content
    has_structure = has_headings and (has_bullets or has_numbered or has_bold)

    # Completeness: check for common incomplete markers
    incomplete_markers = ["TODO", "TBD", "PLACEHOLDER", "[INSERT", "[FILL",
                          "DRAFT", "NEEDS REVIEW", "INCOMPLETE"]
    incomplete_count = sum(1 for m in incomplete_markers if m.upper() in content.upper())
    completeness_score = max(0, 100 - (incomplete_count * 15))

    return {
        "word_count": word_count,
        "section_count": section_count,
        "has_headings": has_headings,
        "has_structure": has_structure,
        "completeness_score": completeness_score,
        "incomplete_markers": incomplete_count
    }


def compute_quality_score(metrics, historical_avg):
    """Compute overall quality score (0-100) compared to historical average."""
    score = 0

    # Word count ratio
    if historical_avg.get("avg_word_count", 0) > 0:
        ratio = min(metrics["word_count"] / historical_avg["avg_word_count"], 1.5)
        score += ratio * 100 * QUALITY_WEIGHTS["word_count_ratio"]
    else:
        score += (50 if metrics["word_count"] > 100 else 20) * QUALITY_WEIGHTS["word_count_ratio"]

    # Section count ratio
    if historical_avg.get("avg_section_count", 0) > 0:
        ratio = min(metrics["section_count"] / historical_avg["avg_section_count"], 1.5)
        score += ratio * 100 * QUALITY_WEIGHTS["section_count_ratio"]
    else:
        score += (50 if metrics["section_count"] > 2 else 20) * QUALITY_WEIGHTS["section_count_ratio"]

    # Headings
    score += (100 if metrics["has_headings"] else 0) * QUALITY_WEIGHTS["has_headings"]

    # Structure
    score += (100 if metrics["has_structure"] else 0) * QUALITY_WEIGHTS["has_structure"]

    # Completeness
    score += metrics["completeness_score"] * QUALITY_WEIGHTS["completeness"]

    return round(min(100, score), 1)


def get_historical_average(dtype_data):
    """Calculate historical averages for a deliverable type."""
    entries = dtype_data.get("entries", [])
    if not entries:
        return {"avg_word_count": 0, "avg_section_count": 0}

    avg_words = sum(e.get("word_count", 0) for e in entries) / len(entries)
    avg_sections = sum(e.get("section_count", 0) for e in entries) / len(entries)

    return {
        "avg_word_count": avg_words,
        "avg_section_count": avg_sections
    }


def show_status():
    state = load_state()
    types = state.get("deliverable_types", {})
    scores = state.get("quality_scores", [])
    warnings = state.get("degradation_warnings", [])

    print("=== Quality Trend Analyzer ===")
    print(f"Total analyzed: {state.get('total_analyzed', 0)}")
    print(f"Degradation warnings: {len(warnings)}")

    if scores:
        recent_avg = sum(s.get("score", 0) for s in scores[-10:]) / min(10, len(scores))
        overall_avg = sum(s.get("score", 0) for s in scores) / len(scores)
        print(f"Overall avg quality: {overall_avg:.1f}/100")
        print(f"Recent avg quality: {recent_avg:.1f}/100")

        if recent_avg < overall_avg * 0.8:
            print(f"  WARNING: Recent quality is {((overall_avg - recent_avg)/overall_avg)*100:.0f}% below historical average")

    if types:
        print("\nQuality by deliverable type:")
        for dtype, data in sorted(types.items()):
            entries = data.get("entries", [])
            if not entries:
                continue
            avg_score = sum(e.get("quality_score", 0) for e in entries) / len(entries)
            avg_words = sum(e.get("word_count", 0) for e in entries) / len(entries)
            print(f"\n  {dtype} ({len(entries)} deliverables)")
            print(f"    Avg quality: {avg_score:.1f}/100")
            print(f"    Avg words: {avg_words:.0f}")

            # Trend
            if len(entries) >= 3:
                first_half = entries[:len(entries)//2]
                second_half = entries[len(entries)//2:]
                first_avg = sum(e.get("quality_score", 0) for e in first_half) / len(first_half)
                second_avg = sum(e.get("quality_score", 0) for e in second_half) / len(second_half)
                trend = "IMPROVING" if second_avg > first_avg else ("DECLINING" if second_avg < first_avg * 0.9 else "STABLE")
                print(f"    Trend: {trend}")

    if warnings:
        print(f"\nRecent warnings (last {min(5, len(warnings))}):")
        for w in warnings[-5:]:
            ts = w.get("timestamp", "?")[:19]
            dtype = w.get("type", "?")
            score = w.get("score", "?")
            avg = w.get("average", "?")
            print(f"  [{ts}] {dtype}: score {score} (avg: {avg})")

    sys.exit(0)


def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("Quality trend analyzer state reset.")
    sys.exit(0)


def main():
    if "--status" in sys.argv:
        show_status()
    if "--reset" in sys.argv:
        reset_state()

    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        print(json.dumps({"decision": "ALLOW"}))
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Write", "write"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    # Only analyze deliverable files
    if not file_path or ".tmp/hooks/" in file_path:
        print(json.dumps({"decision": "ALLOW"}))
        return

    # Must be a markdown or text deliverable
    if not any(file_path.endswith(ext) for ext in [".md", ".txt", ".html"]):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    now = datetime.now().isoformat()
    state["total_analyzed"] = state.get("total_analyzed", 0) + 1

    dtype = detect_deliverable_type(file_path)
    metrics = compute_metrics(content)

    # Get or create type data
    types = state.get("deliverable_types", {})
    if dtype not in types:
        types[dtype] = {"entries": []}

    historical = get_historical_average(types[dtype])
    quality_score = compute_quality_score(metrics, historical)

    # Record entry
    entry = {
        "timestamp": now,
        "file": Path(file_path).name,
        "word_count": metrics["word_count"],
        "section_count": metrics["section_count"],
        "completeness_score": metrics["completeness_score"],
        "quality_score": quality_score
    }
    types[dtype]["entries"].append(entry)
    types[dtype]["entries"] = types[dtype]["entries"][-50:]
    state["deliverable_types"] = types

    # Track overall scores
    scores = state.get("quality_scores", [])
    scores.append({"timestamp": now, "score": quality_score, "type": dtype})
    state["quality_scores"] = scores[-200:]

    # Check for degradation
    entries = types[dtype]["entries"]
    if len(entries) >= 3:
        avg_score = sum(e.get("quality_score", 0) for e in entries[:-1]) / (len(entries) - 1)
        if quality_score < avg_score * 0.7:
            warnings = state.get("degradation_warnings", [])
            warnings.append({
                "timestamp": now,
                "type": dtype,
                "score": quality_score,
                "average": round(avg_score, 1),
                "file": Path(file_path).name
            })
            state["degradation_warnings"] = warnings[-50:]

            save_state(state)
            output = {
                "decision": "ALLOW",
                "reason": f"[Quality Trend] WARNING: {dtype} quality ({quality_score}/100) is below average ({avg_score:.0f}/100). Words: {metrics['word_count']}, Sections: {metrics['section_count']}"
            }
            print(json.dumps(output))
            return

    save_state(state)
    print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
