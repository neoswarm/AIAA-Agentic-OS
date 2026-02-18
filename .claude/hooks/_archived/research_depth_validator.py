#!/usr/bin/env python3
"""
Hook 23: Research Depth Validator (PostToolUse on Write)

When files matching *research*.md are written to .tmp/:
- Check for source citations (URLs, "Source:", "Reference:", "According to")
- Count distinct sources (min 5 for deep research)
- Check for data points (numbers, percentages, dollar amounts)
- Check for competitor mentions (at least 2 competitors)
- Check for market size or TAM mentions

Returns ALLOW always but includes warning if depth insufficient.
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "research_depth_log.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"validations": [], "stats": {"total_checked": 0, "warnings_issued": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def count_sources(content):
    """Count distinct source citations."""
    sources = set()

    # URLs
    urls = re.findall(r'https?://[^\s\)\"\']+', content)
    for url in urls:
        # Normalize: strip trailing punctuation
        url = url.rstrip(".,;:!?)")
        domain = re.search(r'https?://([^/]+)', url)
        if domain:
            sources.add(domain.group(1))

    # Citation patterns
    citation_patterns = [
        r'Source:\s*(.+)',
        r'Reference:\s*(.+)',
        r'According to\s+([^,\.]+)',
        r'per\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'reported by\s+([^,\.]+)',
        r'data from\s+([^,\.]+)',
        r'study by\s+([^,\.]+)',
        r'research by\s+([^,\.]+)',
    ]
    for pattern in citation_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for m in matches:
            sources.add(m.strip()[:50])

    return len(sources), list(sources)[:10]


def count_data_points(content):
    """Count quantitative data points."""
    data_points = 0

    # Percentages
    data_points += len(re.findall(r'\d+(?:\.\d+)?%', content))

    # Dollar amounts
    data_points += len(re.findall(r'\$[\d,]+(?:\.\d+)?(?:\s*(?:M|B|K|million|billion|thousand))?', content))

    # Large numbers with context
    data_points += len(re.findall(r'\b\d{1,3}(?:,\d{3})+\b', content))

    # Year references with data
    data_points += len(re.findall(r'(?:in|by|since)\s+20\d{2}', content))

    return data_points


def count_competitor_mentions(content):
    """Count likely competitor mentions."""
    competitor_patterns = [
        r'[Cc]ompetitor[s]?\s*(?:include|:)\s*(.+)',
        r'[Cc]ompeting\s+(?:with|against)\s+(.+)',
        r'[Vv]s\.?\s+(\S+)',
        r'[Aa]lternative[s]?\s*(?:include|:)\s*(.+)',
        r'[Rr]ival[s]?\s*(?:include|:)\s*(.+)',
    ]
    competitors = set()
    for pattern in competitor_patterns:
        matches = re.findall(pattern, content)
        for m in matches:
            competitors.add(m.strip()[:50])

    # Also look for "Competitor Analysis" or "Competitive Landscape" sections
    has_section = bool(re.search(
        r'(?:competitor|competitive|competition)\s*(?:analysis|landscape|overview)',
        content, re.IGNORECASE
    ))

    return len(competitors), has_section


def check_market_size(content):
    """Check for market size / TAM mentions."""
    market_patterns = [
        r'(?:market\s+size|TAM|total\s+addressable\s+market)',
        r'(?:market\s+(?:valued|worth|estimated))',
        r'(?:\$[\d,.]+\s*(?:billion|million|B|M)\s*market)',
        r'(?:CAGR|growth\s+rate)',
        r'(?:market\s+(?:share|opportunity|potential))',
    ]
    found = []
    for pattern in market_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            found.append(pattern)
    return len(found) > 0, found


def validate_research(content, filename):
    """Run all validation checks on research content."""
    issues = []
    scores = {}

    # 1. Source count
    source_count, sources = count_sources(content)
    scores["sources"] = source_count
    if source_count < 5:
        issues.append(f"Only {source_count} distinct sources found (minimum 5 for deep research)")

    # 2. Data points
    data_count = count_data_points(content)
    scores["data_points"] = data_count
    if data_count < 3:
        issues.append(f"Only {data_count} quantitative data points found (need more numbers/stats)")

    # 3. Competitor mentions
    comp_count, has_section = count_competitor_mentions(content)
    scores["competitors"] = comp_count
    scores["has_competitor_section"] = has_section
    if comp_count < 2 and not has_section:
        issues.append("Fewer than 2 competitor mentions and no competitive analysis section")

    # 4. Market size
    has_market, market_terms = check_market_size(content)
    scores["has_market_size"] = has_market
    if not has_market:
        issues.append("No market size or TAM information found")

    # 5. Content length
    word_count = len(content.split())
    scores["word_count"] = word_count
    if word_count < 500:
        issues.append(f"Research only {word_count} words (shallow for deep research)")

    return issues, scores


def handle_status():
    state = load_state()
    print("=== Research Depth Validator Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"Total files checked: {stats.get('total_checked', 0)}")
    print(f"Warnings issued: {stats.get('warnings_issued', 0)}")

    validations = state.get("validations", [])
    if validations:
        print(f"\nRecent validations:")
        for v in validations[-5:]:
            print(f"  File: {v.get('filename', 'unknown')}")
            print(f"    Sources: {v.get('scores', {}).get('sources', '?')}")
            print(f"    Data points: {v.get('scores', {}).get('data_points', '?')}")
            print(f"    Issues: {len(v.get('issues', []))}")
            print(f"    Time: {v.get('timestamp', 'unknown')}")
    else:
        print("\nNo research files validated yet.")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Research depth validator state reset.")
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

    # Only check research files in .tmp/
    if ".tmp" not in file_path or "research" not in file_path.lower():
        print(json.dumps({"decision": "ALLOW"}))
        return

    if not file_path.endswith(".md"):
        print(json.dumps({"decision": "ALLOW"}))
        return

    state = load_state()
    issues, scores = validate_research(content, file_path)

    validation_record = {
        "filename": Path(file_path).name,
        "filepath": file_path,
        "scores": scores,
        "issues": issues,
        "timestamp": datetime.now().isoformat()
    }

    state["validations"].append(validation_record)
    state["stats"]["total_checked"] = state["stats"].get("total_checked", 0) + 1

    if issues:
        state["stats"]["warnings_issued"] = state["stats"].get("warnings_issued", 0) + 1
        warning = f"Research depth issues in {Path(file_path).name}: " + "; ".join(issues)
        save_state(state)
        print(json.dumps({"decision": "ALLOW", "reason": warning}))
    else:
        save_state(state)
        print(json.dumps({"decision": "ALLOW"}))


if __name__ == "__main__":
    main()
