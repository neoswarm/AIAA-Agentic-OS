#!/usr/bin/env python3
"""
Keyword Research Skill

Strategic keyword research using the 6 Circles Method.
Follows skill: skills/keyword-research.md

Usage:
    python3 execution/keyword_research.py \
        --business "AI marketing consulting for startups" \
        --audience "Funded startups, 10-50 employees" \
        --goal "Leads for consulting" \
        --output output/keyword_research.md
"""

import os
import sys
import argparse
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def call_llm(prompt: str, max_tokens: int = 8000) -> str:
    """Call Claude via OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY required")
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "anthropic/claude-sonnet-4",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": max_tokens
        },
        timeout=180
    )
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"API error: {response.status_code} - {response.text}")


def load_skill() -> str:
    """Load the keyword research skill definition."""
    skill_path = Path(__file__).parent.parent / "skills" / "keyword-research.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return ""


def main():
    parser = argparse.ArgumentParser(description="Strategic Keyword Research")
    parser.add_argument("--business", required=True, help="What you sell/offer")
    parser.add_argument("--audience", required=True, help="Who you're targeting")
    parser.add_argument("--website", help="Your website URL")
    parser.add_argument("--competitors", help="Competitor URLs (comma-separated)")
    parser.add_argument("--goal", required=True, help="Campaign goal (traffic/leads/sales/authority)")
    parser.add_argument("--timeline", default="mix", help="Timeline (quick-wins/long-term/mix)")
    parser.add_argument("--output", required=True, help="Output markdown file")
    
    args = parser.parse_args()
    
    print("🔍 Starting keyword research...")
    print(f"   Business: {args.business}")
    print(f"   Audience: {args.audience}")
    print(f"   Goal: {args.goal}")
    
    # Load skill definition
    skill_content = load_skill()
    
    # Build context
    context = f"""
Business: {args.business}
Target Audience: {args.audience}
Website: {args.website or 'Not provided'}
Competitors: {args.competitors or 'Not provided'}
Goal: {args.goal}
Timeline: {args.timeline}
"""
    
    # Create prompt
    prompt = f"""You are an expert SEO strategist using the 6 Circles Method for keyword research.

{skill_content}

---

CONTEXT:
{context}

---

TASK:
Perform comprehensive keyword research following the exact process outlined in the skill:

1. SEED GENERATION - Generate 20-30 seed keywords
2. EXPAND (6 Circles Method) - Expand each seed using all 6 circles
3. CLUSTER - Group into content pillars with validation
4. PRIORITIZE - Score by business value, opportunity, and speed
5. MAP TO CONTENT - Assign content types and calendar placement

OUTPUT FORMAT:
Use the exact Executive Summary, Pillar Overview, and 90-Day Content Calendar format from the skill.

Be EXTREMELY specific:
- Include actual keyword examples
- Provide search volume estimates
- Show competitive analysis
- Give clear "start here" recommendation
- Include proprietary advantage analysis

Generate the complete keyword research document now."""

    print("🤖 Generating keyword research (this may take 2-3 minutes)...")
    
    # Call LLM
    result = call_llm(prompt)
    
    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Add metadata header
    full_output = f"""# Keyword Research Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Business:** {args.business}
**Audience:** {args.audience}
**Goal:** {args.goal}

---

{result}

---

*Generated using the 6 Circles Method*
*Skill: keyword-research*
"""
    
    output_path.write_text(full_output, encoding="utf-8")
    
    print("\n✅ Keyword research complete!")
    print(f"   Saved to: {output_path}")
    print(f"   Length: {len(result)} characters")
    
    # Also create Google Doc if token exists
    if (Path.cwd() / "token.pickle").exists():
        try:
            print("\n📄 Creating Google Doc...")
            import subprocess
            subprocess.run([
                "python3", "execution/create_google_doc.py",
                "--title", f"Keyword Research - {args.business}",
                "--content", str(output_path),
                "--output-json", "/tmp/keyword_research_doc.json"
            ], check=False, capture_output=True)
            
            doc_json = Path("/tmp/keyword_research_doc.json")
            if doc_json.exists():
                import json
                doc_data = json.loads(doc_json.read_text())
                if "url" in doc_data:
                    print(f"   Google Doc: {doc_data['url']}")
        except Exception as e:
            print(f"   (Google Doc creation skipped: {e})")
    
    return 0


if __name__ == "__main__":
    exit(main())
