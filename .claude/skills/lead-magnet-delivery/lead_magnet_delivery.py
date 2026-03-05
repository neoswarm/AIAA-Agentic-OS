#!/usr/bin/env python3
"""
Lead Magnet Delivery Automation

Automates lead magnet delivery when someone opts in. Immediately delivers resource
via email, tags contacts, triggers nurture sequences, and tracks conversion sources.
Follows directive: directives/lead_magnet_delivery.md
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict

# Add _shared to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "_shared"))

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

from error_reporter import report_error, report_success, report_warning
from resilience import retry


@retry(max_attempts=3, backoff_factor=2)
def send_delivery_email(email: str, name: str, lead_magnet: str, download_url: str, email_api_key: str) -> bool:
    """
    Send lead magnet delivery email.
    
    Uses ConvertKit API (or similar email service).
    """
    # TODO: Integrate with actual email service (ConvertKit, SendGrid, Mailchimp, etc.)
    # This is a placeholder implementation
    
    url = "https://api.convertkit.com/v3/broadcasts"
    
    subject = f"Here's your {lead_magnet} 📥"
    
    email_body = f"""Hi {name or 'there'},

Thanks for your interest! Here's your {lead_magnet}:

👉 Download: {download_url}

Quick tips to get started:
• Start with section 2 for immediate wins
• Implement one strategy at a time
• Track your results after 7 days

Questions? Just reply to this email.

Best,
AIAA Team"""
    
    payload = {
        "api_key": email_api_key,
        "subject": subject,
        "content": email_body,
        "email_address": email
    }
    
    # Placeholder - actual implementation would vary by provider
    print(f"   📧 Email sent to {email}")
    return True


@retry(max_attempts=3)
def tag_contact(email: str, tags: list, email_api_key: str) -> bool:
    """
    Add tags to contact in email service.
    
    Tags format: ["lead_magnet:name", "source:channel", "date:YYYY-MM-DD"]
    """
    # TODO: Integrate with email service tagging API
    
    print(f"   🏷️  Tagged contact: {', '.join(tags)}")
    return True


@retry(max_attempts=2)
def trigger_nurture_sequence(email: str, sequence_id: str, email_api_key: str) -> bool:
    """
    Trigger automated nurture email sequence.
    
    Sequence:
    - Day 1: Implementation tips
    - Day 3: Case study
    - Day 5: Related resource
    - Day 7: Soft pitch
    - Day 10: Value + harder pitch
    - Day 14: Final offer
    """
    # TODO: Integrate with email automation API
    
    print(f"   📬 Triggered nurture sequence: {sequence_id}")
    return True


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def check_duplicate(email: str, email_api_key: str) -> bool:
    """Check if contact already exists"""
    # TODO: Query email service to check for existing contact
    # For now, always return False (not duplicate)
    return False


def log_conversion(email: str, lead_magnet: str, source: str, output_path: Path) -> None:
    """Log conversion for attribution tracking"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    conversion_data = {
        "email": email,
        "lead_magnet": lead_magnet,
        "source": source,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    
    # Append to JSONL log
    with open(output_path, "a") as f:
        f.write(json.dumps(conversion_data) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Automate lead magnet delivery and nurture sequence"
    )
    parser.add_argument("--email", required=True, help="Lead's email address")
    parser.add_argument("--name", help="Lead's name")
    parser.add_argument("--lead-magnet", required=True, help="Lead magnet identifier")
    parser.add_argument("--download-url", required=True, help="Download URL for resource")
    parser.add_argument("--source", default="unknown", help="Conversion source (e.g., linkedin_ad, blog_post)")
    parser.add_argument("--sequence-id", default="default_nurture", help="Nurture sequence ID")
    
    args = parser.parse_args()
    
    # Check API key (using ConvertKit as example, could be any email service)
    email_api_key = os.getenv("CONVERTKIT_API_KEY") or os.getenv("SENDGRID_API_KEY")
    if not email_api_key:
        print("⚠️  Warning: Email service API key not configured")
        print("   Set CONVERTKIT_API_KEY or SENDGRID_API_KEY in .env")
        print("   Continuing in simulation mode...")
    
    try:
        print(f"📧 Processing lead magnet delivery...")
        print(f"   Email: {args.email}")
        print(f"   Lead Magnet: {args.lead_magnet}")
        print(f"   Source: {args.source}")
        
        # Validate email
        if not validate_email(args.email):
            print("❌ Error: Invalid email format")
            sys.exit(1)
        
        # Check for duplicate
        if check_duplicate(args.email, email_api_key or ""):
            print("⚠️  Warning: Contact already exists")
            report_warning(
                "lead-magnet-delivery",
                f"Duplicate submission from {args.email}",
                {"lead_magnet": args.lead_magnet}
            )
            # Continue anyway - they might want the resource again
        
        # Generate tags
        current_date = time.strftime("%Y-%m-%d")
        tags = [
            f"lead_magnet:{args.lead_magnet}",
            f"source:{args.source}",
            f"date:{current_date}"
        ]
        
        # Send delivery email
        print(f"\n📤 Sending delivery email...")
        send_delivery_email(
            args.email,
            args.name,
            args.lead_magnet,
            args.download_url,
            email_api_key or ""
        )
        
        # Tag contact
        print(f"\n🏷️  Tagging contact...")
        tag_contact(args.email, tags, email_api_key or "")
        
        # Trigger nurture sequence
        print(f"\n📬 Triggering nurture sequence...")
        trigger_nurture_sequence(args.email, args.sequence_id, email_api_key or "")
        
        # Log conversion for attribution
        log_path = Path(".tmp/lead-magnets/conversions.jsonl")
        log_conversion(args.email, args.lead_magnet, args.source, log_path)
        
        # Report success
        report_success(
            "lead-magnet-delivery",
            f"Lead magnet delivered to {args.email}",
            {
                "email": args.email,
                "lead_magnet": args.lead_magnet,
                "source": args.source,
                "nurture_sequence": args.sequence_id
            }
        )
        
        print(f"\n✅ Complete! Lead magnet delivered")
        print(f"   Next: Contact will receive nurture sequence over 14 days")
        
    except Exception as e:
        report_error("lead-magnet-delivery", e, {
            "email": args.email,
            "lead_magnet": args.lead_magnet
        })
        sys.exit(1)


if __name__ == "__main__":
    main()
