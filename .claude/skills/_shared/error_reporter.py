#!/usr/bin/env python3
"""
AIAA Centralized Error Reporter

Standardized error reporting, success tracking, and alerting for all skills.
Import in any skill script:
    from _shared.error_reporter import report_error, report_success, report_warning

Usage:
    try:
        # skill logic
        report_success("skill-name", "Generated VSL script", {"word_count": 3500})
    except Exception as e:
        report_error("skill-name", e, {"company": "Acme Corp"})
        sys.exit(1)
"""

import os
import sys
import json
import traceback
import datetime
from pathlib import Path
from typing import Dict, Optional, Any

try:
    import requests
except ImportError:
    print("❌ Error: requests library not installed")
    print("   Install with: pip install requests")
    sys.exit(1)


# Configuration from environment
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "")
LOG_DIR = Path(".tmp/logs")


def _ensure_log_dir() -> None:
    """Create log directory if it doesn't exist"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _log_to_file(data: Dict[str, Any], event_type: str) -> None:
    """Append event to JSONL log file"""
    _ensure_log_dir()
    log_file = LOG_DIR / "skill_executions.jsonl"
    
    log_entry = {
        "type": event_type,
        **data
    }
    
    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"⚠️  Failed to write to log file: {e}")


def _send_slack_alert(skill_name: str, message: str, severity: str, details: Optional[Dict] = None) -> None:
    """Send formatted Slack alert with severity colors"""
    if not SLACK_WEBHOOK:
        return
    
    # Color coding by severity
    color_map = {
        "error": "#FF0000",      # Red
        "warning": "#FFA500",    # Orange
        "success": "#00FF00"     # Green
    }
    
    emoji_map = {
        "error": "❌",
        "warning": "⚠️",
        "success": "✅"
    }
    
    color = color_map.get(severity, "#808080")
    emoji = emoji_map.get(severity, "ℹ️")
    
    # Build message blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {skill_name.upper()}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Message:* {message}"
            }
        }
    ]
    
    # Add details if provided
    if details:
        details_text = "\n".join([f"• *{k}:* {v}" for k, v in details.items()])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Details:*\n{details_text}"
            }
        })
    
    payload = {
        "text": f"{emoji} {skill_name}: {message}",
        "blocks": blocks,
        "attachments": [{
            "color": color,
            "footer": f"AIAA Agentic OS • {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }]
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK, json=payload, timeout=5)
        if response.status_code != 200:
            print(f"⚠️  Slack alert failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Failed to send Slack alert: {e}")


def _log_to_dashboard(data: Dict[str, Any], event_type: str) -> None:
    """Log event to dashboard API (best-effort, non-blocking)"""
    if not DASHBOARD_URL:
        return
    
    endpoint = f"{DASHBOARD_URL}/api/skill-logs"
    payload = {
        "type": event_type,
        **data
    }
    
    try:
        response = requests.post(endpoint, json=payload, timeout=3)
        # Don't fail if dashboard is down - just log locally
        if response.status_code not in [200, 201]:
            print(f"⚠️  Dashboard logging failed (non-fatal): {response.status_code}")
    except Exception as e:
        # Best effort - don't break skill execution if dashboard is unavailable
        print(f"⚠️  Dashboard unavailable (non-fatal): {e}")


def report_error(skill_name: str, error: Exception, context: Optional[Dict] = None) -> None:
    """
    Report an error from any skill.
    
    Args:
        skill_name: Name of the skill (e.g., "vsl-funnel")
        error: The exception that occurred
        context: Additional context (company name, input args, etc.)
    
    Example:
        try:
            generate_vsl()
        except Exception as e:
            report_error("vsl-funnel", e, {"company": "Acme Corp"})
            sys.exit(1)
    """
    error_data = {
        "skill": skill_name,
        "error": str(error),
        "error_type": type(error).__name__,
        "traceback": traceback.format_exc(),
        "timestamp": datetime.datetime.now().isoformat(),
        "context": context or {}
    }
    
    # Log locally
    _log_to_file(error_data, "error")
    
    # Send Slack alert
    details = {
        "Error Type": error_data["error_type"],
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    if context:
        details.update(context)
    
    _send_slack_alert(skill_name, str(error), "error", details)
    
    # Log to dashboard API (if available)
    _log_to_dashboard(error_data, "error")
    
    # Also print to console for immediate visibility
    print(f"\n❌ ERROR in {skill_name}:")
    print(f"   {error}")
    print(f"\n💾 Error logged to: {LOG_DIR / 'skill_executions.jsonl'}")


def report_success(skill_name: str, summary: str, outputs: Optional[Dict] = None) -> None:
    """
    Report successful skill execution.
    
    Args:
        skill_name: Name of the skill
        summary: Brief success message
        outputs: Key outputs (file paths, URLs, metrics)
    
    Example:
        report_success(
            "vsl-funnel",
            "Generated complete VSL funnel",
            {
                "script_word_count": 3500,
                "sales_page_url": "https://docs.google.com/...",
                "email_sequence_count": 6
            }
        )
    """
    data = {
        "skill": skill_name,
        "summary": summary,
        "outputs": outputs or {},
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # Log locally
    _log_to_file(data, "success")
    
    # Send Slack notification
    _send_slack_alert(skill_name, summary, "success", outputs)
    
    # Log to dashboard
    _log_to_dashboard(data, "success")
    
    # Print to console
    print(f"\n✅ SUCCESS: {summary}")
    if outputs:
        print("\n📊 Outputs:")
        for key, value in outputs.items():
            print(f"   • {key}: {value}")


def report_warning(skill_name: str, message: str, context: Optional[Dict] = None) -> None:
    """
    Report a non-fatal warning.
    
    Args:
        skill_name: Name of the skill
        message: Warning message
        context: Additional context
    
    Example:
        report_warning(
            "cold-email-campaign",
            "API rate limit approaching",
            {"requests_remaining": 50}
        )
    """
    data = {
        "skill": skill_name,
        "warning": message,
        "timestamp": datetime.datetime.now().isoformat(),
        "context": context or {}
    }
    
    # Log locally
    _log_to_file(data, "warning")
    
    # Send Slack alert (warnings go to same channel)
    _send_slack_alert(skill_name, message, "warning", context)
    
    # Log to dashboard
    _log_to_dashboard(data, "warning")
    
    # Print to console
    print(f"\n⚠️  WARNING: {message}")


if __name__ == "__main__":
    """Test the error reporter"""
    print("Testing AIAA Error Reporter...")
    
    # Test success
    report_success(
        "test-skill",
        "Test success message",
        {"test_metric": 100}
    )
    
    # Test warning
    report_warning(
        "test-skill",
        "Test warning message",
        {"test_context": "example"}
    )
    
    # Test error
    try:
        raise ValueError("Test error for validation")
    except Exception as e:
        report_error(
            "test-skill",
            e,
            {"test_arg": "value"}
        )
    
    print(f"\n✅ Test complete. Check logs at: {LOG_DIR / 'skill_executions.jsonl'}")
