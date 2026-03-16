#!/usr/bin/env python3
"""
Dream 100 Email Sequence Generator
Uses the EXACT GPT-4o prompt from SKILL_D100_email_builder.md

Usage:
    python3 execution/generate_d100_email_sequence.py \
        --structured-json /path/to/structured_data_v2.json \
        --booking-url "https://example.com/book" \
        --output-dir /path/to/output
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

def load_structured_data(json_path):
    """Load and parse structured data JSON"""
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        sys.exit(1)

def extract_email_context(structured_json, booking_url):
    """Extract email context from structured JSON"""

    practice = structured_json.get('practice', {})
    conditions = structured_json.get('conditions', [])
    services = structured_json.get('services', [])
    clinical = structured_json.get('clinical_approach', {})
    patient_journey = structured_json.get('patient_journey', {})
    providers = structured_json.get('providers', [])
    trust = structured_json.get('trust_signals', {})

    context = {
        "company_name": practice.get('brand_name', {}).get('value', 'Unknown'),
        "specialty": practice.get('specialty', {}).get('value', 'Healthcare'),
        "conditions_treated": [c.get('name', {}).get('value') for c in conditions if c.get('name', {}).get('value')],
        "services_offered": [s.get('name', {}).get('value') for s in services if s.get('name', {}).get('value')],
        "clinical_approach": {
            "differentiators": clinical.get('differentiators', {}).get('value', []),
            "philosophy": clinical.get('philosophy', {}).get('value', ''),
            "modalities": clinical.get('modalities', {}).get('value', [])
        },
        "providers": [
            {
                "name": p.get('name', {}).get('value', ''),
                "credentials": p.get('credentials', {}).get('value', ''),
                "specialty": p.get('specialty', {}).get('value', ''),
                "bio_summary": p.get('bio_summary', {}).get('value', '')
            }
            for p in providers
        ],
        "patient_journey": {
            "discovery_call": patient_journey.get('discovery_call', {}).get('description', {}).get('value', ''),
            "consult_expectations": patient_journey.get('consult_expectations', {}).get('value', '')
        },
        "trust_signals": {
            "testimonials_present": trust.get('testimonials', {}).get('present', False),
            "testimonial_themes": trust.get('testimonials', {}).get('themes', {}).get('value', ''),
            "awards": trust.get('awards', {}).get('value', '')
        },
        "booking_url": booking_url
    }

    return context

def build_prompt(context):
    """Build the EXACT prompt from SKILL_D100_email_builder.md"""

    # Format context as JSON strings for insertion
    company_name = context['company_name']
    specialty = context['specialty']
    conditions = json.dumps(context['conditions_treated'], indent=2)
    services = json.dumps(context['services_offered'], indent=2)
    differentiators = json.dumps(context['clinical_approach']['differentiators'], indent=2)
    philosophy = json.dumps(context['clinical_approach']['philosophy'], indent=2)
    modalities = json.dumps(context['clinical_approach']['modalities'], indent=2)
    providers = json.dumps(context['providers'], indent=2)
    patient_journey = json.dumps(context['patient_journey'], indent=2)
    trust_signals = json.dumps(context['trust_signals'], indent=2)
    booking_url = context['booking_url']

    # EXACT prompt from skill file
    prompt = f"""You are a senior healthcare conversion copywriter + lifecycle marketing strategist.

GOAL
Using ONLY the context I provide (no assumptions), generate a **3-email "Speed-to-Trust" sequence** that is automatically triggered after a patient completes a Custom Health Assessment.

These emails are NOT newsletters.
They are hyper-relevant, short, empathetic, and insight-driven — designed to:
- Validate the patient's specific symptoms and concerns
- Demonstrate clinical intelligence and credibility
- Build belief using mechanisms + real patient outcomes
- Prepare the patient emotionally and intellectually to book

The app already captured the patient's core issues — use that data.

---

HARD RULES
- Use ONLY the provided context and assessment data.
- Do NOT invent symptoms, conditions, treatments, or results.
- Do NOT diagnose or make medical guarantees.
- If something is unknown, leave a placeholder.
- Write in plain, human language — not marketing hype.
- Tone: calm, confident, intelligent, reassuring.
- Each email must feel valuable on its own, not salesy.

---

CONTEXT FROM PRACTICE:
{{
  "company_name": "{company_name}",
  "specialty": "{specialty}",
  "conditions_treated": {conditions},
  "services_offered": {services},
  "clinical_approach": {{
    "differentiators": {differentiators},
    "philosophy": {philosophy},
    "modalities": {modalities}
  }},
  "providers": {providers},
  "patient_journey": {patient_journey},
  "trust_signals": {trust_signals},
  "booking_url": "{booking_url}"
}}

AVAILABLE PERSONALIZATION VARIABLES
(Use only if present; otherwise leave as placeholders)
- [FIRST_NAME]
- [PRIMARY_SYMPTOM]
- [SECONDARY_SYMPTOM]
- [DURATION_OR_TRIGGER]
- [IMPACT_ON_LIFE]
- [KEY_ASSESSMENT_INSIGHT]
- [RECOMMENDED_SERVICE_OR_FOCUS]
- [PATIENT_GOAL]
- [BOOKING_LINK]
- [PROVIDER_OR_PRACTICE_NAME]

---

EMAILS TO CREATE (IN THIS ORDER)

────────────────────────
EMAIL 1: Smart Practice Value Drop
────────────────────────
Purpose:
- Immediate validation: "We understand what's going on."
- Share ONE high-value insight derived from their assessment.
- Reframe the symptom in a way the patient hasn't heard before.

Must include:
- Subject line
- Empathetic opening referencing [PRIMARY_SYMPTOM]
- One clear insight tied to [KEY_ASSESSMENT_INSIGHT]
- Why generic solutions often fail (without attacking other providers)
- Soft CTA to book or "learn more"

────────────────────────
EMAIL 2: Mechanism Story
────────────────────────
Purpose:
- Explain the *why* behind their symptoms.
- Show that the practice understands root causes, not just symptoms.

Must include:
- Subject line
- Simple story or analogy explaining the mechanism
- Tie mechanism back to patient's assessment answers
- Explain what typically gets missed in standard care
- Position the practice's approach as different (without claims)

────────────────────────
EMAIL 3: Proof & Results
────────────────────────
Purpose:
- Transfer belief using a relatable patient story.
- Reduce fear and uncertainty.
- Invite the next step.

Must include:
- Subject line
- Short anonymized patient story with similar pattern
- What changed when the right issue was addressed
- Clear disclaimer that results vary
- Clear, calm CTA to book using [BOOKING_LINK]

---

STRUCTURE & FORMAT RULES
- Each email should be 150–300 words max.
- Short paragraphs. No walls of text.
- No emojis.
- No aggressive urgency.
- End each email with the practice name or care team (not "marketing").

---

OUTPUT FORMAT (STRICT)
Return:
- Email 1 (complete)
- Email 2 (complete)
- Email 3 (complete)

Each email must include:
- Subject line
- Body copy
- CTA line

Do NOT include explanations, commentary, or strategy notes.
Do NOT ask questions.

BEGIN."""

    return prompt

def call_openai_api(prompt, api_key):
    """Call OpenAI API with GPT-4o"""

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 4000,
        "top_p": 0.9
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API Error: {e}")
        sys.exit(1)

def save_emails(content, output_dir, company_name, booking_url):
    """Save email sequence to output files"""

    # Create output directories
    emails_dir = Path(output_dir) / "emails"
    esp_dir = emails_dir / "esp_imports"
    emails_dir.mkdir(parents=True, exist_ok=True)
    esp_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()

    # Save main sequence.md
    sequence_path = emails_dir / "sequence.md"
    with open(sequence_path, 'w') as f:
        f.write(f"""# 3-Email Speed-to-Trust Sequence
**Practice:** {company_name}
**Trigger:** Health Assessment Completion
**Generated:** {timestamp}

---

{content}

---

_Generated by AIAA Dream 100 Automation v1.0_
""")

    # Save raw output for reference
    raw_path = emails_dir / "raw_output.txt"
    with open(raw_path, 'w') as f:
        f.write(content)

    # Save setup guide
    setup_path = emails_dir / "SETUP_GUIDE.md"
    with open(setup_path, 'w') as f:
        f.write(f"""# Email Sequence Setup Guide

## Overview
3-email automated sequence triggered when a patient completes the health assessment.

## Timing
- **Email 1:** Immediately (within 5 minutes)
- **Email 2:** 2 days after Email 1
- **Email 3:** 4 days after Email 2 (6 days total)

## Setup Instructions

### Option 1: Klaviyo
1. Create a new Flow: "Health Assessment Follow-up"
2. Trigger: Tag added = "assessment_complete"
3. Import emails from sequence.md
4. Replace personalization tokens:
   - `[FIRST_NAME]` → `{{{{ person.first_name }}}}`
   - `[PRIMARY_SYMPTOM]` → `{{{{ event.PRIMARY_SYMPTOM }}}}`
   - etc.
5. Set time delays: 0d, 2d, 6d
6. Test with sample profile

### Option 2: ConvertKit
1. Create Automation: "Assessment Nurture"
2. Copy email content from sequence.md
3. Map custom fields to assessment data
4. Set delays and test

### Option 3: ActiveCampaign
1. Create Automation
2. Copy email content from sequence.md
3. Paste into email editor
4. Configure personalization tags
5. Set wait conditions: 2 days, 4 days

## Personalization Variables

**Required (from assessment app):**
- `FIRST_NAME` - Patient's first name
- `PRIMARY_SYMPTOM` - Main concern from assessment
- `BOOKING_LINK` - {booking_url}

**Optional (enhance if available):**
- `SECONDARY_SYMPTOM`
- `DURATION_OR_TRIGGER`
- `IMPACT_ON_LIFE`
- `KEY_ASSESSMENT_INSIGHT`
- `RECOMMENDED_SERVICE_OR_FOCUS`
- `PATIENT_GOAL`

## Testing Checklist
- [ ] All personalization variables render correctly
- [ ] Links work and point to {booking_url}
- [ ] Plain text version is readable
- [ ] HTML renders on mobile
- [ ] Unsubscribe link present (add per ESP requirements)
- [ ] Disclaimer present in Email 3
- [ ] Send test to yourself
- [ ] Verify timing delays

## Compliance Notes
- No diagnosis or medical advice given
- Results disclaimers included
- Emergency guidance if needed
- Professional, non-promotional tone

---
Generated by AIAA Dream 100 Automation v1.0
{timestamp}
""")

    return {
        "sequence_md": str(sequence_path),
        "raw_output": str(raw_path),
        "setup_guide": str(setup_path)
    }

def main():
    parser = argparse.ArgumentParser(description="Generate Dream 100 Email Sequence using GPT-4o")
    parser.add_argument("--structured-json", required=True, help="Path to structured_data_v2.json")
    parser.add_argument("--booking-url", required=True, help="Booking URL")
    parser.add_argument("--output-dir", required=True, help="Output directory")

    args = parser.parse_args()

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment")
        sys.exit(1)

    print("═══════════════════════════════════════════════════════════")
    print("Dream 100 Email Sequence Generator")
    print("═══════════════════════════════════════════════════════════")
    print()

    # Load structured data
    print("Loading structured data...")
    structured_json = load_structured_data(args.structured_json)

    # Extract context
    print("Extracting email context...")
    context = extract_email_context(structured_json, args.booking_url)
    print(f"✓ Practice: {context['company_name']}")
    print(f"✓ Specialty: {context['specialty']}")
    print(f"✓ Conditions: {len(context['conditions_treated'])}")
    print(f"✓ Services: {len(context['services_offered'])}")
    print()

    # Build prompt
    print("Building GPT-4o prompt (from SKILL_D100_email_builder.md)...")
    prompt = build_prompt(context)
    print(f"✓ Prompt length: {len(prompt)} characters")
    print()

    # Call OpenAI API
    print("Calling OpenAI API (gpt-4o)...")
    print("Model: gpt-4o")
    print("Temperature: 0.7")
    print("Max tokens: 4000")
    print()
    response = call_openai_api(prompt, api_key)

    # Extract content
    content = response['choices'][0]['message']['content']
    print(f"✓ Generated {len(content)} characters")
    print()

    # Save outputs
    print("Saving outputs...")
    files = save_emails(content, args.output_dir, context['company_name'], args.booking_url)
    print(f"✓ Sequence: {files['sequence_md']}")
    print(f"✓ Raw output: {files['raw_output']}")
    print(f"✓ Setup guide: {files['setup_guide']}")
    print()

    print("═══════════════════════════════════════════════════════════")
    print("✓ Email Sequence Generated")
    print("═══════════════════════════════════════════════════════════")
    print()
    print("SEQUENCE: 3-Email Speed-to-Trust")
    print("TRIGGER: Health Assessment Completion")
    print()
    print("EMAILS:")
    print("1. Smart Practice Value Drop (Send: Immediately)")
    print("2. Mechanism Story (Send: Day 2)")
    print("3. Proof & Results (Send: Day 6)")
    print()
    print("FILES GENERATED:")
    print(f"→ {files['sequence_md']}")
    print(f"→ {files['setup_guide']}")
    print()
    print("NEXT STEPS:")
    print("1. Review emails in sequence.md")
    print("2. Follow SETUP_GUIDE.md for ESP setup")
    print("3. Test with sample data before going live")
    print()

if __name__ == "__main__":
    main()
