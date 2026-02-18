#!/usr/bin/env python3
"""
LinkedIn Profile Change Tracker

Monitors LinkedIn profiles for job changes, promotions, posts, and other signals
that indicate outreach opportunities. Sends priority-classified alerts.
Follows directive: directives/linkedin_profile_tracker.md
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

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


@retry(max_attempts=2)
def fetch_linkedin_profile(profile_url: str, scraper_api_key: str) -> Dict:
    """
    Fetch current LinkedIn profile data.
    
    Note: Requires LinkedIn scraping service (Phantombuster, Apify, etc.)
    Placeholder implementation.
    """
    # TODO: Integrate with LinkedIn scraping API
    report_warning(
        "linkedin-profile-tracker",
        f"LinkedIn scraper not integrated - using placeholder for {profile_url}"
    )
    
    # Mock profile data
    return {
        "profile_url": profile_url,
        "name": "John Smith",
        "headline": "VP of Marketing at TechCorp",
        "company": "TechCorp",
        "position": "VP of Marketing",
        "location": "San Francisco, CA",
        "recent_posts": [
            {
                "text": "Excited to announce we're hiring a team of SDRs!",
                "date": "2026-02-17",
                "url": f"{profile_url}/recent-activity"
            }
        ],
        "connections": 2500,
        "last_updated": time.strftime("%Y-%m-%d")
    }


def load_snapshot(profile_url: str, snapshot_file: Path) -> Dict:
    """Load previous snapshot for comparison"""
    if not snapshot_file.exists():
        return None
    
    try:
        with open(snapshot_file) as f:
            snapshots = json.load(f)
            return snapshots.get(profile_url)
    except:
        return None


def save_snapshot(profile_url: str, profile_data: Dict, snapshot_file: Path) -> None:
    """Save current profile snapshot"""
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing snapshots
    snapshots = {}
    if snapshot_file.exists():
        try:
            with open(snapshot_file) as f:
                snapshots = json.load(f)
        except:
            pass
    
    # Update snapshot
    snapshots[profile_url] = profile_data
    
    # Save
    with open(snapshot_file, "w") as f:
        json.dump(snapshots, f, indent=2)


def detect_changes(old: Dict, new: Dict) -> Dict:
    """
    Detect changes between snapshots.
    
    Returns:
        {
            "high_priority": [...],  # Job change, promotion, hiring
            "medium_priority": [...],  # New post, profile update
            "low_priority": [...]     # Connection milestones
        }
    """
    if not old:
        return {
            "high_priority": [],
            "medium_priority": [],
            "low_priority": [],
            "is_new_profile": True
        }
    
    changes = {
        "high_priority": [],
        "medium_priority": [],
        "low_priority": [],
        "is_new_profile": False
    }
    
    # High priority: Job/company change
    if old.get("company") != new.get("company"):
        changes["high_priority"].append({
            "type": "company_change",
            "old_company": old.get("company"),
            "new_company": new.get("company"),
            "message": f"Changed company: {old.get('company')} → {new.get('company')}"
        })
    
    # High priority: Position change (promotion or role change)
    if old.get("position") != new.get("position"):
        changes["high_priority"].append({
            "type": "position_change",
            "old_position": old.get("position"),
            "new_position": new.get("position"),
            "message": f"New position: {old.get('position')} → {new.get('position')}"
        })
    
    # High priority: Hiring announcement in recent posts
    for post in new.get("recent_posts", []):
        if any(keyword in post.get("text", "").lower() for keyword in ["hiring", "we're looking", "join our team"]):
            changes["high_priority"].append({
                "type": "hiring_announcement",
                "post_text": post["text"],
                "post_url": post.get("url"),
                "message": f"Hiring announcement detected"
            })
    
    # Medium priority: New posts
    old_post_count = len(old.get("recent_posts", []))
    new_post_count = len(new.get("recent_posts", []))
    if new_post_count > old_post_count:
        changes["medium_priority"].append({
            "type": "new_posts",
            "count": new_post_count - old_post_count,
            "message": f"Posted {new_post_count - old_post_count} new updates"
        })
    
    # Low priority: Connection milestones
    old_connections = old.get("connections", 0)
    new_connections = new.get("connections", 0)
    if new_connections >= old_connections + 100:
        changes["low_priority"].append({
            "type": "connection_milestone",
            "old_count": old_connections,
            "new_count": new_connections,
            "message": f"Reached {new_connections} connections"
        })
    
    return changes


@retry(max_attempts=3)
def generate_outreach_template(change: Dict, profile: Dict, api_key: str) -> str:
    """Generate personalized outreach message for a change event"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Generate a personalized LinkedIn message for this situation:

Name: {profile['name']}
Current Role: {profile['position']} at {profile['company']}

Change detected: {change['message']}
Type: {change['type']}

Create a 3-sentence message that:
1. Congratulates them on the change (authentic, specific)
2. Makes a relevant connection
3. Soft CTA (offer value, not pitch)

Keep it casual and genuine."""
    
    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0.8
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def send_alert(profile: Dict, changes: Dict, slack_webhook: str) -> None:
    """Send Slack alert for changes"""
    if not slack_webhook:
        return
    
    high_count = len(changes["high_priority"])
    medium_count = len(changes["medium_priority"])
    
    if high_count == 0 and medium_count == 0:
        return  # No significant changes
    
    # Build alert message
    priority = "🔴 HIGH PRIORITY" if high_count > 0 else "🟡 MEDIUM PRIORITY"
    
    changes_text = ""
    for change in changes["high_priority"]:
        changes_text += f"• {change['message']}\n"
    for change in changes["medium_priority"][:3]:  # Limit to first 3
        changes_text += f"• {change['message']}\n"
    
    payload = {
        "text": f"{priority}: LinkedIn profile change detected",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{priority} Profile Change"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{profile['name']}*\n{profile['headline']}\n<{profile['profile_url']}|View Profile>"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Changes:*\n{changes_text}"
                }
            }
        ]
    }
    
    try:
        requests.post(slack_webhook, json=payload, timeout=10)
    except Exception as e:
        report_warning("linkedin-profile-tracker", f"Failed to send Slack alert: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor LinkedIn profiles for outreach triggers"
    )
    parser.add_argument("--profiles", required=True, help="CSV file with LinkedIn profile URLs")
    parser.add_argument("--check-frequency", default="daily", choices=["daily", "weekly"], help="Check frequency")
    parser.add_argument("--output", default=".tmp/linkedin-tracker/changes.json", help="Output file for changes")
    
    args = parser.parse_args()
    
    # Check API keys
    scraper_key = os.getenv("PHANTOMBUSTER_API_KEY") or os.getenv("APIFY_API_TOKEN")
    if not scraper_key:
        print("⚠️  Warning: LinkedIn scraper API key not configured")
        print("   Set PHANTOMBUSTER_API_KEY or APIFY_API_TOKEN in .env")
    
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    
    try:
        # Load profile list
        profiles = []
        with open(args.profiles) as f:
            for line in f:
                url = line.strip()
                if url and url.startswith("http"):
                    profiles.append(url)
        
        print(f"🔍 Monitoring {len(profiles)} LinkedIn profiles")
        
        snapshot_file = Path(".tmp/linkedin-tracker/snapshots.json")
        all_changes = []
        
        for profile_url in profiles:
            print(f"\n👤 Checking: {profile_url}")
            
            # Fetch current profile
            current_profile = fetch_linkedin_profile(profile_url, scraper_key or "")
            
            # Load previous snapshot
            previous_profile = load_snapshot(profile_url, snapshot_file)
            
            # Detect changes
            changes = detect_changes(previous_profile, current_profile)
            
            # Report changes
            high_count = len(changes["high_priority"])
            medium_count = len(changes["medium_priority"])
            
            if changes.get("is_new_profile"):
                print(f"   ℹ️  New profile added to monitoring")
            elif high_count > 0:
                print(f"   🔴 {high_count} high-priority changes detected")
                
                # Generate outreach templates for high-priority changes
                if openrouter_key:
                    for change in changes["high_priority"]:
                        template = generate_outreach_template(change, current_profile, openrouter_key)
                        change["outreach_template"] = template
                
                # Send Slack alert
                send_alert(current_profile, changes, slack_webhook or "")
                
            elif medium_count > 0:
                print(f"   🟡 {medium_count} medium-priority changes detected")
            else:
                print(f"   ✅ No changes detected")
            
            # Save changes
            if high_count > 0 or medium_count > 0:
                all_changes.append({
                    "profile": current_profile,
                    "changes": changes
                })
            
            # Save updated snapshot
            save_snapshot(profile_url, current_profile, snapshot_file)
        
        # Save all changes to output
        if all_changes:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(all_changes, f, indent=2)
            print(f"\n💾 Changes saved to: {output_path}")
        
        # Report success
        report_success(
            "linkedin-profile-tracker",
            f"Monitored {len(profiles)} profiles",
            {
                "profiles_checked": len(profiles),
                "changes_detected": len(all_changes),
                "output_file": str(args.output) if all_changes else None
            }
        )
        
        print(f"\n✅ Complete! Detected {len(all_changes)} profiles with changes")
        
    except FileNotFoundError:
        print(f"❌ Error: Profiles file not found: {args.profiles}")
        sys.exit(1)
    except Exception as e:
        report_error("linkedin-profile-tracker", e, {"profiles_file": args.profiles})
        sys.exit(1)


if __name__ == "__main__":
    main()
