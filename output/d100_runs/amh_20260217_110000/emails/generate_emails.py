#!/usr/bin/env python3
"""
Generate Speed-to-Trust email sequence via GPT-4o API.
"""
import json
import urllib.request
import os
import sys

# Load API key from .env
env_path = "/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/.env"
api_key = None
with open(env_path, "r") as f:
    for line in f:
        line = line.strip()
        if line.startswith("OPENAI_API_KEY="):
            api_key = line.split("=", 1)[1].strip()
            break

if not api_key:
    print("ERROR: OPENAI_API_KEY not found in .env")
    sys.exit(1)

prompt = r'''You are a senior healthcare conversion copywriter + lifecycle marketing strategist.

GOAL
Using ONLY the context I provide (no assumptions), generate a **3-email "Speed-to-Trust" sequence** that is automatically triggered after a patient completes a Custom Health Assessment.

These emails are NOT newsletters. They are hyper-relevant, short, empathetic, and insight-driven — designed to:
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

INPUTS from JSON:
- Context Brief (scraped website + offerings)
- ICP & RAG (same as assessment app)
- Assessment Output Variables (examples below)
- USE THE BOOKING LINK URL

CONTEXT FROM PRACTICE:
{
  "company_name": "Aligned Modern Health",
  "specialty": "Integrative Healthcare (Functional Medicine, Hormone Health, Chiropractic, Acupuncture, Massage, IV Therapy, Clinical Nutrition)",
  "conditions_treated": ["Gut Health & Food Intolerance", "Hormone & Metabolic Health", "Reproductive Health", "Immune & Autoimmune Conditions", "Pain Movement & Recovery", "Full Family Wellness", "Whole-Body Wellness & Prevention", "Chronic Conditions & Unresolved Symptoms", "Adrenal Fatigue", "Thyroid Issues", "Perimenopause", "Menopause", "Fatigue", "Digestive Issues", "Inflammation", "Infertility", "Allergies", "Insomnia", "Back Pain", "Neck Pain", "Headaches", "Migraines"],
  "services_offered": ["Functional Medicine", "Hormone Health / HRT", "Chiropractic Physical Medicine", "Acupuncture", "Massage Therapy", "IV Vitamin Therapy", "Clinical Nutrition", "Comprehensive Testing"],
  "clinical_approach": {
    "differentiators": ["Root cause approach - go beyond symptoms to find answers", "4 Pillars: Clinical Care Team, Comprehensive Testing, Personalized Treatment, Whole-Body Wellness", "Team-based collaborative model across specialties", "Evidence-based patient-centered care", "Functional medicine testing as detective work", "Deeper evaluations, longer appointments"],
    "philosophy": "Healthcare Designed For You - Instead of looking for ways to mask your symptoms, our goal is to restore optimal function throughout your body.",
    "modalities": ["Functional Medicine", "Hormone Replacement Therapy", "Chiropractic Physical Medicine", "Acupuncture (needles, cupping, moxibustion, gua sha, herbal medicine, electro-stimulation, infrared heat)", "Clinical Massage (Swedish, deep tissue, sports, prenatal)", "IV Vitamin Therapy", "Comprehensive Blood Tests", "Hormone Analysis", "Food Sensitivity Testing", "Stool Analysis", "Nutrient Panels", "Environmental Exposure Testing"]
  },
  "providers": [
    {"name": "Dr. Delilah Renegar, DC", "credentials": "DC", "specialty": "Director of Functional Medicine and Clinical Nutrition"},
    {"name": "100+ expert doctors, nurse practitioners, and clinicians", "credentials": "Various (MD, DC, NP, LAc, LMT)", "specialty": "Multi-disciplinary team"}
  ],
  "patient_journey": {
    "discovery_call": "Free 15-minute acupuncture consultation available",
    "consult_expectations": "Deeper evaluations, longer appointments, same provider continuity, clinical care coordinator manages logistics"
  },
  "trust_signals": {
    "testimonials_present": true,
    "testimonial_themes": "Chicago's top-rated holistic healthcare provider, root cause results, team-based care",
    "awards": "Washington Post feature"
  },
  "booking_url": "https://alignedmodernhealth.com/services/#schedule"
}

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

EMAIL 1: Smart Practice Value Drop
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

EMAIL 2: Mechanism Story
Purpose:
- Explain the *why* behind their symptoms.
- Show that the practice understands root causes, not just symptoms.

Must include:
- Subject line
- Simple story or analogy explaining the mechanism
- Tie mechanism back to patient's assessment answers
- Explain what typically gets missed in standard care
- Position the practice's approach as different (without claims)

EMAIL 3: Proof & Results
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
- Each email should be 150-300 words max.
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

BEGIN.'''

payload = {
    "model": "gpt-4o",
    "temperature": 0.7,
    "max_tokens": 4000,
    "messages": [
        {
            "role": "system",
            "content": "You are a senior healthcare conversion copywriter + lifecycle marketing strategist."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
}

data = json.dumps(payload).encode("utf-8")

req = urllib.request.Request(
    "https://api.openai.com/v1/chat/completions",
    data=data,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    },
    method="POST"
)

print("Calling GPT-4o API...")
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    content = result["choices"][0]["message"]["content"]

    # Write the sequence.md file
    output_path = "/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/output/d100_runs/amh_20260217_110000/emails/sequence.md"
    with open(output_path, "w") as f:
        f.write("# Speed-to-Trust Email Sequence\n")
        f.write("## Aligned Modern Health\n")
        f.write(f"**Generated:** 2026-02-17 | **Model:** GPT-4o | **Temperature:** 0.7\n\n")
        f.write("---\n\n")
        f.write(content)
        f.write("\n")

    print(f"SUCCESS: Emails saved to {output_path}")
    print(f"Tokens used: prompt={result['usage']['prompt_tokens']}, completion={result['usage']['completion_tokens']}, total={result['usage']['total_tokens']}")
    print("\n--- GENERATED CONTENT ---\n")
    print(content)

except urllib.error.HTTPError as e:
    error_body = e.read().decode("utf-8")
    print(f"API ERROR {e.code}: {error_body}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
