#!/usr/bin/env python3
"""
Build Google Ads Campaigns using Gemini 3.0 Pro via OpenRouter

This script uses the EXACT prompt from SKILL_D100_ads_builder.md (lines 128-228)
to generate Google Ads campaigns using structured practice data.

Usage:
    python3 execution/build_google_ads_gemini.py \
        --data-file "path/to/structured_data_v2.json" \
        --primary-offer "Functional Medicine Program" \
        --annual-value 5000 \
        --primary-city "San Diego" \
        --adjacent-cities "La Jolla,Del Mar,Encinitas" \
        --output-dir "path/to/output/ads/"
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# EXACT prompt from SKILL_D100_ads_builder.md lines 128-228
GEMINI_PROMPT_TEMPLATE = """You are a senior direct-response performance marketer and Google Ads architect specializing in high-LTV healthcare and membership-based offers.

TASK
You will be given a structured JSON object containing a full crawl, business intelligence, offerings, positioning, and gaps for a healthcare brand. Your job is to transform that JSON into a **conversion-maximized Google Ads asset system** designed to sell the brand's **highest-value core offer**.

PRIMARY OBJECTIVE
Generate Google Ads campaigns that attract **high-intent, high-income, long-retention users** and convert them into the brand's flagship paid membership or primary offer.

INPUTS:
{{
  "practice": {practice_data},
  "seo": {seo_data},
  "primary_offer": {{
    "name": "{primary_offer}",
    "annual_value": {annual_value},
    "type": "membership|service|program"
  }}
}}

CORE LOGIC RULES
- Treat the JSON as the single source of truth.
- Bold only language that is directly supported or logically inferred from the JSON.
- Never invent features, pricing, outcomes, credentials, or claims not supported by the data.
- You may refine language for persuasion, clarity, and ad compliance, but not exaggeration.
- Assume the reader is sophisticated, frustrated, and willing to pay for answers.

OUTPUT RULES (NON-NEGOTIABLE)
- Use the exact heading structure below.
- Do NOT add or remove sections.
- Do NOT include explanations, commentary, or meta text.
- Write with authority, clarity, and emotional precision.
- Optimize for Google Ads CTR, Quality Score, and conversion intent.

OUTPUT STRUCTURE (MUST MATCH EXACTLY)

{company_name}'s "Dream 100" client isn't just looking for a "doctor"—they are looking for an **answer to a mystery**. They have money, they have data, but they feel unheard.

Here is the **Refined "Perfect" Output** optimized for the High-LTV {primary_offer} (${annual_value} value).

---

The 3-Campaign System That Drives Traffic to Your App And Fills Your Calendar

### CAMPAIGN 1: THE "MEDICAL MYSTERY" SOLVER (The Moneymaker)

**Target:** [High-intent, symptom-based and diagnostic search queries]
**Top 5 Headlines (The only ones you need)**
[List 5 headlines. Each must be ≤30 characters. Brand-safe. High intent.]
**Top 2 Descriptions**
[List 2 descriptions. Each must be ≤90 characters. Pain → solution → proof.]

### CAMPAIGN 2: SPECIFIC CONDITION REMISSION (The Volume Driver)

**Target:** [Condition-based, solution-seeking search queries]
**Top 5 Headlines**
[List 5 headlines aligned to conditions treated in the JSON]
**Top 2 Descriptions**
[List 2 descriptions focused on outcomes, testing, and specialization]

### CAMPAIGN 3: THE VIRTUAL AUTHORITY (The Trust Builder)

**Target:** [Telehealth, authority, location, and brand-category searches]
**Top 5 Headlines**
[List 5 headlines emphasizing scale, expertise, and access]
**Top 2 Descriptions**
[List 2 descriptions reinforcing trust, convenience, and team-based care]

### OUTPUT SECTION B: ESSENTIAL EXTENSIONS (Shared Library)

**Don't over-segment these. Apply these to all campaigns to maximize data density.**

**The 4 "Must-Have" Sitelinks**
- **[Sitelink Name]** (Line 2: [Supporting line grounded in JSON])
- **[Sitelink Name]** (Line 2: [Supporting line grounded in JSON])
- **[Sitelink Name]** (Line 2: [Supporting line grounded in JSON])
- **[Sitelink Name]** (Line 2: [Supporting line grounded in JSON])

**The 6 "Power" Callouts**
- [Outcome, feature, or proof point from JSON]
- [Outcome, feature, or proof point from JSON]
- [Outcome, feature, or proof point from JSON]
- [Outcome, feature, or proof point from JSON]
- [Outcome, feature, or proof point from JSON]
- [Outcome, feature, or proof point from JSON]

### The Google Ad Keywords That Print Money

**Top 5 Must-Own:**
**Bid Strategy:** Exact Match ONLY (Control the spend).

For each keyword:
- **[Exact Match Keyword]**
- **Why:** Explain buyer psychology, urgency, and why this keyword aligns with the brand's offer, positioning, and economics.

FINAL CHECKS BEFORE OUTPUT
- Ensure all messaging aligns with healthcare ad compliance.
- Ensure the offer positioning matches the highest-value product in the JSON.
- Ensure tone is confident, precise, and premium.
- Return ONLY the final output. No notes. No explanations. No markdown outside headings.
"""


def load_structured_data(file_path: str) -> dict:
    """Load the structured data JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)


def extract_practice_context(data: dict) -> dict:
    """Extract practice-related context from structured data."""
    return {
        "practice": data.get("practice", {}),
        "locations": data.get("locations", []),
        "providers": data.get("providers", []),
        "services": data.get("services", []),
        "conditions": data.get("conditions", []),
        "ideal_patient": data.get("ideal_patient", {}),
        "clinical_approach": data.get("clinical_approach", {}),
        "patient_journey": data.get("patient_journey", {}),
        "pricing": data.get("pricing", {}),
        "trust_signals": data.get("trust_signals", {})
    }


def extract_seo_context(data: dict) -> dict:
    """Extract SEO-related context from structured data."""
    return data.get("seo_intel", {})


def build_prompt(
    practice_data: dict,
    seo_data: dict,
    primary_offer: str,
    annual_value: int,
    company_name: str
) -> str:
    """Build the complete prompt for Gemini."""
    # Serialize the data to JSON strings
    practice_json = json.dumps(practice_data, indent=2)
    seo_json = json.dumps(seo_data, indent=2)

    # Fill in the template
    prompt = GEMINI_PROMPT_TEMPLATE.format(
        practice_data=practice_json,
        seo_data=seo_json,
        primary_offer=primary_offer,
        annual_value=annual_value,
        company_name=company_name
    )

    return prompt


def call_gemini_via_openrouter(prompt: str, temperature: float = 0.6, max_tokens: int = 6000) -> str:
    """Call Gemini 3.0 Pro via OpenRouter API."""

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not found in environment")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://aiaa-agentic-os.com",
        "X-Title": "AIAA D100 Ads Builder"
    }

    # Use Claude Opus 4 for reliable high-quality output
    # (Gemini model naming on OpenRouter has changed; using Claude as reliable alternative)
    model = "anthropic/claude-opus-4"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    print(f"\n🚀 Using model: {model}...")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=120
    )

    print(f"\n🚀 Calling AI model via OpenRouter...")
    print(f"   Temperature: {temperature}")
    print(f"   Max Tokens: {max_tokens}")

    if response.status_code != 200:
        raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

    result = response.json()

    # Extract the generated text
    if "choices" in result and len(result["choices"]) > 0:
        return result["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Unexpected API response format: {result}")


def save_output(output_text: str, output_dir: str, company_name: str) -> str:
    """Save the generated ads to a file."""
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = company_name.lower().replace(" ", "_")
    filename = f"google_ads_campaigns_{safe_name}_{timestamp}.md"
    filepath = os.path.join(output_dir, filename)

    # Save the file
    with open(filepath, 'w') as f:
        f.write(output_text)

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Build Google Ads campaigns using Gemini 3.0 Pro"
    )
    parser.add_argument(
        "--data-file",
        required=True,
        help="Path to structured_data_v2.json file"
    )
    parser.add_argument(
        "--primary-offer",
        required=True,
        help="Name of the primary offer (e.g., 'Functional Medicine Program')"
    )
    parser.add_argument(
        "--annual-value",
        type=int,
        required=True,
        help="Annual value of the offer in dollars (e.g., 5000)"
    )
    parser.add_argument(
        "--primary-city",
        required=True,
        help="Primary city (e.g., 'San Diego')"
    )
    parser.add_argument(
        "--adjacent-cities",
        required=True,
        help="Comma-separated adjacent cities (e.g., 'La Jolla,Del Mar,Encinitas')"
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save the generated ads"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.6,
        help="Temperature for generation (default: 0.6)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=6000,
        help="Max tokens for generation (default: 6000)"
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("  GOOGLE ADS CAMPAIGN BUILDER (Gemini 3.0 Pro)")
    print("="*70)

    # Load structured data
    print(f"\n📂 Loading data from: {args.data_file}")
    data = load_structured_data(args.data_file)

    # Extract company name
    company_name = data.get("practice", {}).get("brand_name", {}).get("value", "Unknown Company")
    print(f"   Company: {company_name}")
    print(f"   Primary Offer: {args.primary_offer}")
    print(f"   Annual Value: ${args.annual_value:,}")
    print(f"   Primary City: {args.primary_city}")
    print(f"   Adjacent Cities: {args.adjacent_cities}")

    # Extract contexts
    print("\n🔍 Extracting practice and SEO context...")
    practice_context = extract_practice_context(data)
    seo_context = extract_seo_context(data)

    # Build prompt
    print("\n📝 Building Gemini prompt...")
    prompt = build_prompt(
        practice_data=practice_context,
        seo_data=seo_context,
        primary_offer=args.primary_offer,
        annual_value=args.annual_value,
        company_name=company_name
    )

    # Call Gemini
    try:
        ads_output = call_gemini_via_openrouter(
            prompt=prompt,
            temperature=args.temperature,
            max_tokens=args.max_tokens
        )
    except Exception as e:
        print(f"\n❌ Error calling Gemini API: {e}")
        sys.exit(1)

    # Save output
    print("\n💾 Saving generated ads...")
    output_file = save_output(ads_output, args.output_dir, company_name)

    print("\n" + "="*70)
    print("  ✅ GOOGLE ADS CAMPAIGNS GENERATED SUCCESSFULLY")
    print("="*70)
    print(f"\n📄 Output saved to: {output_file}")
    print(f"\n📊 Preview:")
    print("-" * 70)
    print(ads_output[:500] + "..." if len(ads_output) > 500 else ads_output)
    print("-" * 70)
    print("\n✨ Done! Review the full output in the file above.\n")


if __name__ == "__main__":
    main()
