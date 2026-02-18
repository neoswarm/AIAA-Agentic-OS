#!/usr/bin/env python3
"""
Zoom Call Multi-Content Repurposer

Processes Zoom call recordings/transcripts to generate multi-platform content:
YouTube scripts, LinkedIn posts, Twitter threads, newsletters, and Facebook posts.
Follows directive: directives/zoom_call_multi_content_copywriter_scheduler.md
"""

import argparse
import json
import os
import sys
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


@retry(max_attempts=3, backoff_factor=2)
def generate_youtube_script(transcript: str, api_key: str) -> Dict:
    """Generate YouTube video script from transcript"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Convert this Zoom call transcript into a high-converting YouTube video script.

Transcript:
{transcript[:4000]}  # Limit to avoid token overflow

Structure:
1. HOOK (15 seconds) - Proof, promise, plan, persona
2. Teaching segments (3-5 segments with clear value)
3. CTA close (clear next step)

Keep the original insights but make it engaging for YouTube.
Max 2000 words."""
    
    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3000,
        "temperature": 0.7
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    
    # Generate title
    title_prompt = f"Create a 3-7 word YouTube title for this script (no quotes):\n\n{content[:500]}"
    title_payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": title_prompt}],
        "max_tokens": 50
    }
    
    title_response = requests.post(url, json=title_payload, headers=headers, timeout=15)
    title = title_response.json()["choices"][0]["message"]["content"].strip()
    
    return {
        "title": title,
        "content": content,
        "platform": "youtube"
    }


@retry(max_attempts=3, backoff_factor=2)
def generate_linkedin_post(transcript: str, api_key: str) -> Dict:
    """Generate LinkedIn post from transcript"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Create a LinkedIn post from this call transcript.

Transcript:
{transcript[:3000]}

Structure:
- Strong hook (first line must grab attention)
- Clear structure (bullet points, short paragraphs)
- Engaging conclusion with CTA
- Lucas Synnott's voice: authentic, insightful, conversational

NO formatting characters (#, *, **). Plain text only.
Max 3000 characters."""
    
    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500,
        "temperature": 0.8
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=45)
    response.raise_for_status()
    
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    
    # Generate title
    title_prompt = f"Create a 3-7 word title for this LinkedIn post (no quotes):\n\n{content[:300]}"
    title_payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": title_prompt}],
        "max_tokens": 30
    }
    
    title_response = requests.post(url, json=title_payload, headers=headers, timeout=15)
    title = title_response.json()["choices"][0]["message"]["content"].strip()
    
    return {
        "title": title,
        "content": content,
        "platform": "linkedin"
    }


@retry(max_attempts=3, backoff_factor=2)
def generate_newsletter(transcript: str, api_key: str) -> Dict:
    """Generate email newsletter from transcript"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Write an emotionally resonant, personal newsletter from this call.

Transcript:
{transcript[:3000]}

Style:
- Lucas Synnott's voice: personal, vulnerable, insightful
- NOT over-polished or corporate
- Story-driven with key insights
- Feels like a letter from a friend

Include a clear CTA at the end.
Max 1200 words."""
    
    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
        "temperature": 0.8
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    
    # Generate title
    title_prompt = f"Create a 3-7 word newsletter subject line (no quotes):\n\n{content[:300]}"
    title_payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": title_prompt}],
        "max_tokens": 30
    }
    
    title_response = requests.post(url, json=title_payload, headers=headers, timeout=15)
    title = title_response.json()["choices"][0]["message"]["content"].strip()
    
    return {
        "title": title,
        "content": content,
        "platform": "newsletter"
    }


@retry(max_attempts=2)
def generate_twitter_post(transcript: str, api_key: str) -> Dict:
    """Generate Twitter/X post from transcript"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Create a concise, high-performing tweet from this call's key insight.

Transcript:
{transcript[:2000]}

Requirements:
- Max 280 characters
- No hashtags or formatting
- Single powerful insight
- Conversational tone

Output only the tweet, nothing else."""
    
    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100,
        "temperature": 0.9
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    
    result = response.json()
    content = result["choices"][0]["message"]["content"].strip()
    
    return {
        "title": "Twitter Post",
        "content": content,
        "platform": "twitter"
    }


@retry(max_attempts=2)
def generate_facebook_post(transcript: str, api_key: str) -> Dict:
    """Generate Facebook post from transcript"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Create an engagement-optimized Facebook post from this call.

Transcript:
{transcript[:2500]}

Requirements:
- Personal and relatable tone
- Clear structure with line breaks
- Strong hook and CTA
- 300-600 words
- No markdown formatting

Output only the post, nothing else."""
    
    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.8
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    content = result["choices"][0]["message"]["content"].strip()
    
    return {
        "title": "Facebook Post",
        "content": content,
        "platform": "facebook"
    }


def save_content(content_piece: Dict, output_dir: Path) -> Path:
    """Save content piece to markdown file"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    platform = content_piece["platform"]
    filename = f"{platform}_{content_piece['title'][:30].replace(' ', '_')}.md"
    filepath = output_dir / filename
    
    with open(filepath, "w") as f:
        f.write(f"# {content_piece['title']}\n\n")
        f.write(f"Platform: {platform}\n\n")
        f.write("---\n\n")
        f.write(content_piece["content"])
    
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Repurpose Zoom call into multi-platform content"
    )
    parser.add_argument("--transcript", required=True, help="Path to transcript file or raw text")
    parser.add_argument("--platforms", default="linkedin,twitter,youtube,newsletter,facebook", help="Comma-separated platforms")
    parser.add_argument("--output-dir", default=".tmp/zoom-repurpose", help="Output directory")
    
    args = parser.parse_args()
    
    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY not configured")
        sys.exit(1)
    
    try:
        # Load transcript
        transcript_path = Path(args.transcript)
        if transcript_path.exists():
            with open(transcript_path) as f:
                transcript = f.read()
        else:
            # Treat as raw text
            transcript = args.transcript
        
        print(f"📝 Processing transcript ({len(transcript)} characters)")
        
        platforms = [p.strip() for p in args.platforms.split(",")]
        print(f"🎯 Target platforms: {', '.join(platforms)}")
        
        output_dir = Path(args.output_dir)
        generated_content = []
        
        # Generate content for each platform
        for platform in platforms:
            print(f"\n📱 Generating {platform} content...")
            
            try:
                if platform == "youtube":
                    content = generate_youtube_script(transcript, api_key)
                elif platform == "linkedin":
                    content = generate_linkedin_post(transcript, api_key)
                elif platform == "newsletter":
                    content = generate_newsletter(transcript, api_key)
                elif platform == "twitter":
                    content = generate_twitter_post(transcript, api_key)
                elif platform == "facebook":
                    content = generate_facebook_post(transcript, api_key)
                else:
                    print(f"   ⚠️  Unknown platform: {platform}")
                    continue
                
                # Save to file
                filepath = save_content(content, output_dir)
                print(f"   ✅ Saved to: {filepath}")
                
                generated_content.append({
                    "platform": platform,
                    "title": content["title"],
                    "file": str(filepath),
                    "word_count": len(content["content"].split())
                })
                
            except Exception as e:
                report_error("zoom-content-repurposer", e, {
                    "platform": platform,
                    "transcript_length": len(transcript)
                })
        
        # Report success
        if generated_content:
            report_success(
                "zoom-content-repurposer",
                f"Generated {len(generated_content)} content pieces",
                {
                    "platforms": [c["platform"] for c in generated_content],
                    "output_dir": str(output_dir),
                    "pieces": generated_content
                }
            )
        
        print(f"\n✅ Complete! Generated {len(generated_content)} content pieces")
        for piece in generated_content:
            print(f"   • {piece['platform']}: {piece['title']} ({piece['word_count']} words)")
        
    except Exception as e:
        report_error("zoom-content-repurposer", e, {"transcript_file": args.transcript})
        sys.exit(1)


if __name__ == "__main__":
    main()
