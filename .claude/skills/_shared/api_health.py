#!/usr/bin/env python3
"""
AIAA API Key Health Checker

Validates all configured API keys by hitting test endpoints.
Run standalone: python3 .claude/skills/_shared/api_health.py
Or import: from _shared.api_health import check_all_keys

Outputs a JSON health report and sends Slack alerts for unhealthy keys.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Tuple, Optional

try:
    import requests
except ImportError:
    print("❌ Error: requests library not installed")
    print("   Install with: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# API test endpoints and validation functions
API_TESTS = {
    "OPENROUTER_API_KEY": {
        "url": "https://openrouter.ai/api/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "success_codes": [200]
    },
    "PERPLEXITY_API_KEY": {
        "url": "https://api.perplexity.ai/chat/completions",
        "method": "POST",
        "headers": lambda key: {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        "body": {
            "model": "sonar",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 1
        },
        "success_codes": [200]
    },
    "ANTHROPIC_API_KEY": {
        "url": "https://api.anthropic.com/v1/models",
        "method": "GET",
        "headers": lambda key: {
            "x-api-key": key,
            "anthropic-version": "2023-06-01"
        },
        "success_codes": [200]
    },
    "OPENAI_API_KEY": {
        "url": "https://api.openai.com/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "success_codes": [200]
    },
    "FAL_KEY": {
        "url": "https://fal.run/status",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Key {key}"},
        "success_codes": [200, 404]  # 404 is ok, means API is reachable
    },
    "APIFY_API_TOKEN": {
        "url": "https://api.apify.com/v2/acts",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "success_codes": [200]
    }
}


def check_api_key(key_name: str, api_key: str, config: Dict) -> Dict:
    """
    Test a single API key by hitting its health endpoint.
    
    Returns:
        {
            "key_name": "OPENROUTER_API_KEY",
            "status": "active" | "expired" | "invalid" | "error",
            "response_time_ms": 250,
            "last_checked": "2026-02-18T10:30:00",
            "error_message": "Optional error details"
        }
    """
    start_time = time.time()
    
    try:
        # Build request
        url = config["url"]
        method = config["method"]
        headers = config["headers"](api_key)
        body = config.get("body")
        
        # Make request with timeout
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=body, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Check status code
        if response.status_code in config["success_codes"]:
            status = "active"
            error_message = None
        elif response.status_code == 401:
            status = "invalid"
            error_message = "Authentication failed - key may be invalid or expired"
        elif response.status_code == 403:
            status = "expired"
            error_message = "Access forbidden - key may be expired or lacks permissions"
        elif response.status_code == 429:
            status = "rate_limited"
            error_message = "Rate limit exceeded"
        else:
            status = "error"
            error_message = f"Unexpected status code: {response.status_code}"
        
        return {
            "key_name": key_name,
            "status": status,
            "response_time_ms": response_time_ms,
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "error_message": error_message,
            "http_status": response.status_code
        }
        
    except requests.Timeout:
        return {
            "key_name": key_name,
            "status": "error",
            "response_time_ms": int((time.time() - start_time) * 1000),
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "error_message": "Request timeout - API may be down"
        }
    except requests.ConnectionError:
        return {
            "key_name": key_name,
            "status": "error",
            "response_time_ms": int((time.time() - start_time) * 1000),
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "error_message": "Connection error - check network or API endpoint"
        }
    except Exception as e:
        return {
            "key_name": key_name,
            "status": "error",
            "response_time_ms": int((time.time() - start_time) * 1000),
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "error_message": str(e)
        }


def check_slack_webhook(webhook_url: str) -> Dict:
    """Test Slack webhook with a test message (opt-in)"""
    start_time = time.time()
    
    try:
        payload = {
            "text": "🔍 AIAA API Health Check - Testing Slack webhook",
            "blocks": [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Webhook validation in progress. This is a test message."
                }
            }]
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response_time_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            status = "active"
            error_message = None
        else:
            status = "error"
            error_message = f"Webhook returned status {response.status_code}"
        
        return {
            "key_name": "SLACK_WEBHOOK_URL",
            "status": status,
            "response_time_ms": response_time_ms,
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "error_message": error_message
        }
        
    except Exception as e:
        return {
            "key_name": "SLACK_WEBHOOK_URL",
            "status": "error",
            "response_time_ms": int((time.time() - start_time) * 1000),
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "error_message": str(e)
        }


def check_all_keys(test_slack: bool = False) -> Dict:
    """
    Check all configured API keys.
    
    Args:
        test_slack: If True, sends a test message to Slack webhook
    
    Returns:
        {
            "timestamp": "2026-02-18T10:30:00",
            "summary": {
                "total": 7,
                "active": 6,
                "unhealthy": 1
            },
            "keys": [
                {"key_name": "...", "status": "active", ...},
                ...
            ]
        }
    """
    results = []
    
    # Check each API key
    for key_name, config in API_TESTS.items():
        api_key = os.getenv(key_name)
        
        if not api_key:
            results.append({
                "key_name": key_name,
                "status": "missing",
                "response_time_ms": 0,
                "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "error_message": "Key not configured in environment"
            })
            print(f"⚠️  {key_name}: MISSING")
        else:
            print(f"🔍 Checking {key_name}...")
            result = check_api_key(key_name, api_key, config)
            results.append(result)
            
            # Print result
            status_emoji = {
                "active": "✅",
                "invalid": "❌",
                "expired": "⏰",
                "error": "❌",
                "rate_limited": "⚠️"
            }.get(result["status"], "❓")
            
            print(f"   {status_emoji} {result['status'].upper()} ({result['response_time_ms']}ms)")
            if result.get("error_message"):
                print(f"      {result['error_message']}")
    
    # Optionally test Slack webhook
    if test_slack:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if webhook_url:
            print(f"🔍 Testing Slack webhook...")
            result = check_slack_webhook(webhook_url)
            results.append(result)
            
            status_emoji = "✅" if result["status"] == "active" else "❌"
            print(f"   {status_emoji} {result['status'].upper()}")
        else:
            results.append({
                "key_name": "SLACK_WEBHOOK_URL",
                "status": "missing",
                "response_time_ms": 0,
                "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "error_message": "Webhook not configured"
            })
            print(f"⚠️  SLACK_WEBHOOK_URL: MISSING")
    
    # Build summary
    total = len(results)
    active = sum(1 for r in results if r["status"] == "active")
    unhealthy = total - active
    
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "summary": {
            "total": total,
            "active": active,
            "unhealthy": unhealthy
        },
        "keys": results
    }
    
    return report


def save_report(report: Dict, output_path: Path) -> None:
    """Save health report to file"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n💾 Report saved to: {output_path}")


def send_slack_summary(report: Dict) -> None:
    """Send Slack summary if any keys are unhealthy"""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return
    
    summary = report["summary"]
    
    # Only send if there are issues
    if summary["unhealthy"] == 0:
        print("\n✅ All API keys healthy - no Slack alert needed")
        return
    
    # Build alert
    unhealthy_keys = [k for k in report["keys"] if k["status"] != "active"]
    issues_text = "\n".join([
        f"• *{k['key_name']}*: {k['status'].upper()} - {k.get('error_message', 'No details')}"
        for k in unhealthy_keys
    ])
    
    payload = {
        "text": f"⚠️ API Health Alert: {summary['unhealthy']} unhealthy keys",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ API Health Alert"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{summary['unhealthy']}* of *{summary['total']}* API keys are unhealthy:\n\n{issues_text}"
                }
            },
            {
                "type": "context",
                "elements": [{
                    "type": "mrkdwn",
                    "text": f"Checked at: {report['timestamp']}"
                }]
            }
        ]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            print("\n✅ Slack alert sent")
        else:
            print(f"\n⚠️  Slack alert failed: {response.status_code}")
    except Exception as e:
        print(f"\n⚠️  Failed to send Slack alert: {e}")


if __name__ == "__main__":
    """Run API health check"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check API key health")
    parser.add_argument("--test-slack", action="store_true", help="Send test message to Slack")
    parser.add_argument("--output", default=".tmp/api_health.json", help="Output file path")
    args = parser.parse_args()
    
    print("🔍 AIAA API Health Check\n")
    
    # Run checks
    report = check_all_keys(test_slack=args.test_slack)
    
    # Save report
    output_path = Path(args.output)
    save_report(report, output_path)
    
    # Send Slack summary if issues found
    send_slack_summary(report)
    
    # Print summary
    print("\n" + "="*50)
    print(f"📊 SUMMARY")
    print("="*50)
    print(f"Total keys: {report['summary']['total']}")
    print(f"Active: {report['summary']['active']} ✅")
    print(f"Unhealthy: {report['summary']['unhealthy']} {'❌' if report['summary']['unhealthy'] > 0 else ''}")
    
    # Exit with error code if any keys are unhealthy
    sys.exit(0 if report['summary']['unhealthy'] == 0 else 1)
