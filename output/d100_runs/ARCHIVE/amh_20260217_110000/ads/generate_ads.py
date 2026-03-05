#!/usr/bin/env python3
"""Generate Google Ads campaigns via OpenRouter API (Gemini 3.0 Pro)"""
import json
import os
import urllib.request

# Load API key from .env
env_path = '/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/.env'
api_key = None
with open(env_path) as f:
    for line in f:
        if line.startswith('OPENROUTER_API_KEY='):
            api_key = line.strip().split('=', 1)[1]
            break

if not api_key:
    raise RuntimeError("OPENROUTER_API_KEY not found in .env")

# Load structured JSON
json_path = '/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/output/d100_runs/amh_20260217_110000/scrape_data/structured_data.json'
with open(json_path) as f:
    structured_data = json.load(f)

# Build context for the prompt
practice_context = json.dumps({
    "practice": structured_data["practice"],
    "services": structured_data["services"],
    "conditions": structured_data["conditions"],
    "locations": structured_data["locations"][:3],
    "pricing": structured_data["pricing"],
    "trust_signals": structured_data["trust_signals"],
    "clinical_approach": structured_data["clinical_approach"],
    "seo_intel": structured_data["seo_intel"]
}, indent=2)

seo_context = json.dumps({
    "primary_keywords": structured_data["seo_intel"]["primary_keywords"]["value"],
    "location_modifiers": structured_data["seo_intel"]["location_modifiers"]["value"][:10],
    "conversion_ctas": structured_data["seo_intel"]["conversion_ctas"]["value"]
}, indent=2)

# EXACT prompt from SKILL_D100_ads_builder.md lines 128-228
prompt = f"""You are a senior direct-response performance marketer and Google Ads architect specializing in high-LTV healthcare and membership-based offers.

TASK
You will be given a structured JSON object containing a full crawl, business intelligence, offerings, positioning, and gaps for a healthcare brand. Your job is to transform that JSON into a **conversion-maximized Google Ads asset system** designed to sell the brand's **highest-value core offer**.

PRIMARY OBJECTIVE
Generate Google Ads campaigns that attract **high-intent, high-income, long-retention users** and convert them into the brand's flagship paid membership or primary offer.

INPUTS:
{{
  "practice": {practice_context},
  "seo": {seo_context},
  "primary_offer": {{
    "name": "IV Vitamin Therapy Membership",
    "annual_value": 3300,
    "type": "membership"
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

Aligned Modern Health's "Dream 100" client isn't just looking for a "doctor"—they are looking for an **answer to a mystery**. They have money, they have data, but they feel unheard.

Here is the **Refined "Perfect" Output** optimized for the High-LTV IV Vitamin Therapy Membership ($3,300 value).

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
- Return ONLY the final output. No notes. No explanations. No markdown outside headings."""

# Build API request
payload = json.dumps({
    "model": "google/gemini-2.0-flash-001",
    "messages": [
        {
            "role": "user",
            "content": prompt
        }
    ],
    "temperature": 0.6,
    "max_tokens": 6000
})

req = urllib.request.Request(
    "https://openrouter.ai/api/v1/chat/completions",
    data=payload.encode('utf-8'),
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://aiaa-agentic-os.local",
        "X-Title": "AIAA Dream 100 Ads Builder"
    }
)

print("Calling OpenRouter API (Gemini 2.0 Flash)...")
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode('utf-8'))

    if 'choices' in result and len(result['choices']) > 0:
        content = result['choices'][0]['message']['content']
        print(f"Success! Got {len(content)} chars")

        # Save output
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google_ads_campaign.md')
        with open(output_path, 'w') as f:
            f.write(content)
        print(f"Saved to: {output_path}")

        # Print usage
        if 'usage' in result:
            u = result['usage']
            print(f"Tokens: {u.get('prompt_tokens', '?')} in / {u.get('completion_tokens', '?')} out")
    else:
        print("ERROR: No 'choices' in response")
        print(json.dumps(result, indent=2)[:2000])

except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8')
    print(f"HTTP Error {e.code}: {body[:1000]}")
except Exception as e:
    print(f"Error: {e}")
