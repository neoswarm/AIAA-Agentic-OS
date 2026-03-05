#!/usr/bin/env python3
"""
Dream 100 Instagram Personalized DM Automation

Generates personalized Instagram DM openers for Dream 100 prospects using AI vision analysis.
Analyzes profile images and latest posts to create authentic, non-salesy compliment-first openers.
Follows directive: directives/dream_100_instagram_personalized_dm_automation.md
"""

import argparse
import json
import os
import sys
from pathlib import Path

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
from resilience import retry, graceful_fallback


@retry(max_attempts=3, backoff_factor=2)
def analyze_post_with_vision(image_url: str, caption: str, bio: str, api_key: str) -> str:
    """Use OpenRouter vision model to analyze Instagram post"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Analyze this Instagram post and bio to create a personalized compliment.

Bio: {bio}

Caption: {caption}

Instructions:
- Look at the image content, style, and context
- Reference specific visual elements (colors, composition, subject, setting)
- Make the compliment authentic and specific, not generic
- Keep it casual and friendly, not salesy
- 1-2 sentences maximum

Output only the compliment, nothing else."""
    
    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        "max_tokens": 150
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


@retry(max_attempts=2)
def generate_dm_text(compliment: str, booking_link: str, api_key: str) -> str:
    """Generate complete DM with compliment and soft CTA"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Create a 3-sentence Instagram DM using this compliment:

"{compliment}"

Structure:
1. Open with the compliment
2. Brief connection or common ground
3. Soft CTA with booking link: {booking_link}

Keep it casual, authentic, and non-salesy. Max 3 sentences."""
    
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


@graceful_fallback(fallback_value=None)
def fetch_instagram_profile(username: str) -> dict:
    """
    Fetch Instagram profile data.
    
    Note: Requires Instagram scraping tool or API.
    This is a placeholder - integrate with Apify or similar service.
    """
    # TODO: Integrate with Instagram scraping service (Apify, etc.)
    # For now, return mock data structure
    report_warning("dream100-instagram", f"Instagram API not integrated - using placeholder for {username}")
    
    return {
        "username": username,
        "full_name": "Demo User",
        "bio": "Entrepreneur | Content Creator | Coffee Lover",
        "profile_pic_url": "https://via.placeholder.com/150",
        "latest_post": {
            "image_url": "https://via.placeholder.com/600",
            "caption": "Just launched something exciting! Check it out 🚀",
            "timestamp": "2026-02-17"
        }
    }


def process_prospect(prospect: dict, booking_link: str, api_key: str) -> dict:
    """Process a single prospect to generate personalized DM"""
    username = prospect["username"]
    
    print(f"\n🔍 Processing @{username}...")
    
    # Fetch profile data
    profile = fetch_instagram_profile(username)
    if not profile:
        report_warning("dream100-instagram", f"Could not fetch profile for @{username}")
        return None
    
    # Analyze latest post with vision
    try:
        compliment = analyze_post_with_vision(
            image_url=profile["latest_post"]["image_url"],
            caption=profile["latest_post"]["caption"],
            bio=profile["bio"],
            api_key=api_key
        )
        print(f"   ✅ Generated compliment")
    except Exception as e:
        report_error("dream100-instagram", e, {"username": username, "step": "vision_analysis"})
        return None
    
    # Generate full DM
    try:
        dm_text = generate_dm_text(compliment, booking_link, api_key)
        print(f"   ✅ Generated DM")
    except Exception as e:
        report_error("dream100-instagram", e, {"username": username, "step": "dm_generation"})
        return None
    
    return {
        "username": username,
        "full_name": profile["full_name"],
        "bio": profile["bio"],
        "latest_post_url": f"https://instagram.com/p/{username}",
        "compliment": compliment,
        "dm_text": dm_text,
        "status": "ready"
    }


def save_results(results: list, output_path: Path) -> None:
    """Save DM results to JSON"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate personalized Instagram DMs for Dream 100 prospects"
    )
    parser.add_argument("--prospects", required=True, help="JSON file with prospect list")
    parser.add_argument("--booking-link", default="https://calendly.com/example", help="Calendar booking link")
    parser.add_argument("--output", default=".tmp/dream100/dm_results.json", help="Output file")
    
    args = parser.parse_args()
    
    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY not configured")
        print("   Set in .env file")
        sys.exit(1)
    
    try:
        # Load prospects
        with open(args.prospects) as f:
            prospects = json.load(f)
        
        print(f"📋 Loaded {len(prospects)} prospects")
        print(f"🔗 Booking link: {args.booking_link}")
        
        # Process each prospect
        results = []
        for prospect in prospects:
            result = process_prospect(prospect, args.booking_link, api_key)
            if result:
                results.append(result)
        
        # Save results
        output_path = Path(args.output)
        save_results(results, output_path)
        
        # Report success
        report_success(
            "dream100-instagram",
            f"Generated {len(results)} personalized DMs",
            {
                "total_prospects": len(prospects),
                "successful": len(results),
                "output_file": str(output_path)
            }
        )
        
        print(f"\n✅ Complete! Generated {len(results)}/{len(prospects)} DMs")
        
    except FileNotFoundError:
        print(f"❌ Error: Prospects file not found: {args.prospects}")
        sys.exit(1)
    except Exception as e:
        report_error("dream100-instagram", e, {"prospects_file": args.prospects})
        sys.exit(1)


if __name__ == "__main__":
    main()
