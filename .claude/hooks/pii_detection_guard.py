#!/usr/bin/env python3
"""
Hook 44: PII Detection Guard (PreToolUse on Write)

Before writing ANY file:
- Scan content for PII patterns:
  - Email addresses
  - Phone numbers
  - SSN patterns
  - Credit card patterns
  - IP addresses
- If PII found AND file is NOT in clients/ or .tmp/: WARN via stderr
- If SSN or credit card detected ANYWHERE: BLOCK (exit 2)
- Allow PII in client profiles and .tmp/ (expected there)
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / ".tmp" / "hooks"
STATE_FILE = STATE_DIR / "pii_detection_log.json"


def load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"detections": [], "stats": {"total_scans": 0, "warnings": 0, "blocks": 0}}


def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def detect_emails(content):
    """Detect email addresses in content."""
    # Match emails but exclude common false positives
    pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    matches = re.findall(pattern, content)
    # Filter out example/placeholder emails
    filtered = [
        m for m in matches
        if not any(x in m.lower() for x in [
            "example.com", "test.com", "placeholder", "your-email",
            "email@", "user@", "noreply@", "no-reply@",
            "sample.com", "domain.com", "company.com",
        ])
    ]
    return filtered


def detect_phone_numbers(content):
    """Detect phone number patterns."""
    patterns = [
        r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',          # XXX-XXX-XXXX
        r'\(\d{3}\)\s*\d{3}[-.\s]\d{4}',              # (XXX) XXX-XXXX
        r'\+1\s*\d{3}\s*\d{3}\s*\d{4}',               # +1XXXXXXXXXX
        r'\+1[-.\s]\d{3}[-.\s]\d{3}[-.\s]\d{4}',      # +1-XXX-XXX-XXXX
        r'\b1[-.\s]\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',    # 1-XXX-XXX-XXXX
    ]
    found = []
    for pattern in patterns:
        found.extend(re.findall(pattern, content))
    return found


def detect_ssn(content):
    """Detect SSN patterns (XXX-XX-XXXX)."""
    # SSN: 3 digits, dash, 2 digits, dash, 4 digits
    # Exclude patterns that look like dates or other numbers
    pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    matches = re.findall(pattern, content)
    # Filter: SSN first group is 001-899 (not 000, not 900+)
    ssn_like = []
    for m in matches:
        parts = m.split("-")
        first = int(parts[0])
        second = int(parts[1])
        if 1 <= first <= 899 and first != 666 and 1 <= second <= 99:
            ssn_like.append(m)
    return ssn_like


def detect_credit_cards(content):
    """Detect credit card number patterns (16 digit sequences)."""
    patterns = [
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # XXXX-XXXX-XXXX-XXXX
        r'\b\d{16}\b',                                     # 16 consecutive digits
    ]
    found = []
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for m in matches:
            # Basic Luhn check plausibility - just check length after stripping
            digits = re.sub(r'[\s\-]', '', m)
            if len(digits) == 16 and digits.isdigit():
                # Check if it starts with known card prefixes
                if digits[0] in ['3', '4', '5', '6']:
                    found.append(m)
    return found


def detect_ip_addresses(content):
    """Detect IP addresses."""
    pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    matches = re.findall(pattern, content)
    # Filter out common non-PII IPs
    filtered = []
    for ip in matches:
        parts = ip.split(".")
        if all(0 <= int(p) <= 255 for p in parts):
            # Exclude common non-sensitive patterns
            if ip not in ["0.0.0.0", "127.0.0.1", "255.255.255.0", "255.255.255.255"]:
                if not ip.startswith("192.168.") and not ip.startswith("10."):
                    filtered.append(ip)
    return filtered


def is_safe_location(file_path):
    """Check if the file is in a location where PII is expected."""
    return "clients/" in file_path or ".tmp/" in file_path


def handle_status():
    state = load_state()
    print("=== PII Detection Guard Status ===")
    print(f"State file: {STATE_FILE}")
    print(f"File exists: {STATE_FILE.exists()}")

    stats = state.get("stats", {})
    print(f"Total scans: {stats.get('total_scans', 0)}")
    print(f"Warnings: {stats.get('warnings', 0)}")
    print(f"Blocks: {stats.get('blocks', 0)}")

    print(f"\nPII types detected:")
    print(f"  - Critical (always block): SSN patterns, credit card numbers")
    print(f"  - Warn only (outside clients/.tmp/): emails, phone numbers, IP addresses")

    detections = state.get("detections", [])
    if detections:
        print(f"\nRecent detections:")
        for d in detections[-5:]:
            print(f"  [{d.get('action', '?').upper()}] {d.get('filename', '?')}")
            print(f"    Types: {', '.join(d.get('types_found', []))}")
            print(f"    Time: {d.get('timestamp', '?')}")
    else:
        print("\nNo PII detections yet.")


def handle_reset():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print("PII detection guard state reset.")
    else:
        print("No state file to reset.")


def main():
    if "--status" in sys.argv:
        handle_status()
        return
    if "--reset" in sys.argv:
        handle_reset()
        return

    # PreToolUse mode
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Write":
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "")

    if not content:
        sys.exit(0)

    state = load_state()
    state["stats"]["total_scans"] = state["stats"].get("total_scans", 0) + 1

    # Detect PII
    emails = detect_emails(content)
    phones = detect_phone_numbers(content)
    ssns = detect_ssn(content)
    credit_cards = detect_credit_cards(content)
    ips = detect_ip_addresses(content)

    types_found = []
    if emails:
        types_found.append(f"{len(emails)} email(s)")
    if phones:
        types_found.append(f"{len(phones)} phone(s)")
    if ssns:
        types_found.append(f"{len(ssns)} SSN(s)")
    if credit_cards:
        types_found.append(f"{len(credit_cards)} credit card(s)")
    if ips:
        types_found.append(f"{len(ips)} IP address(es)")

    if not types_found:
        save_state(state)
        sys.exit(0)

    detection_record = {
        "filename": Path(file_path).name,
        "filepath": file_path,
        "types_found": types_found,
        "timestamp": datetime.now().isoformat(),
    }

    # CRITICAL: SSN or credit card detected ANYWHERE -> BLOCK
    if ssns or credit_cards:
        detection_record["action"] = "block"
        state["stats"]["blocks"] = state["stats"].get("blocks", 0) + 1
        state["detections"].append(detection_record)
        state["detections"] = state["detections"][-50:]
        save_state(state)

        critical_types = []
        if ssns:
            critical_types.append(f"{len(ssns)} SSN pattern(s)")
        if credit_cards:
            critical_types.append(f"{len(credit_cards)} credit card pattern(s)")

        sys.stderr.write(
            f"[PII GUARD] BLOCKED: Critical PII detected in {Path(file_path).name}: "
            f"{', '.join(critical_types)}. Remove sensitive data before writing.\n"
        )
        sys.exit(2)

    # Non-critical PII in unsafe locations -> WARN
    safe = is_safe_location(file_path)
    if not safe and (emails or phones or ips):
        detection_record["action"] = "warn"
        state["stats"]["warnings"] = state["stats"].get("warnings", 0) + 1
        state["detections"].append(detection_record)
        state["detections"] = state["detections"][-50:]
        save_state(state)

        sys.stderr.write(
            f"[PII GUARD] Potential PII detected: {', '.join(types_found)}. "
            f"Verify this should be written to {Path(file_path).name} "
            f"(outside clients/ and .tmp/).\n"
        )
    else:
        detection_record["action"] = "allow"
        state["detections"].append(detection_record)
        state["detections"] = state["detections"][-50:]
        save_state(state)

    sys.exit(0)


if __name__ == "__main__":
    main()
