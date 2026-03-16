"""D100 Email Sequence Builder - GPT-4o via OpenRouter"""

import os
import requests
from pathlib import Path
from datetime import datetime


class D100EmailBuilder:
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")

        if not self.openrouter_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

    def build(self, structured_data, booking_url):
        """
        Generate 3-email Speed-to-Trust sequence from structured JSON data.

        Returns:
            dict: { status, email_path, timestamp }
        """
        try:
            # Extract context
            practice          = structured_data.get("practice", {})
            services          = structured_data.get("services", [])
            conditions        = structured_data.get("conditions", [])
            clinical_approach = structured_data.get("clinical_approach", {})

            company_name    = (
                practice.get("brand_name", {}).get("value") or
                practice.get("legal_name", {}).get("value") or
                "Healthcare Practice"
            )
            specialty        = practice.get("specialty", {}).get("value", "Integrative Medicine")
            differentiators  = clinical_approach.get("differentiators", {}).get("value", "")
            philosophy       = clinical_approach.get("philosophy", {}).get("value", "")
            service_list     = [s.get("name", {}).get("value", "") for s in services if s.get("name", {}).get("value")]
            condition_list   = [c.get("name", {}).get("value", "") for c in conditions if c.get("name", {}).get("value")]

            prompt = f"""You are a senior healthcare conversion copywriter + lifecycle marketing strategist.

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
{{
  "company_name": "{company_name}",
  "specialty": "{specialty}",
  "conditions_treated": {condition_list},
  "services_offered": {service_list},
  "clinical_approach": {{
    "differentiators": "{differentiators[:400]}",
    "philosophy": "{philosophy[:400]}"
  }},
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
Email 1: Smart Practice Value Drop
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
Email 2: Mechanism Story
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
Email 3: Proof & Results
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

            print(f"  ✉️  Building email sequences...")

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type":  "application/json"
                },
                json={
                    "model":       "openai/gpt-4o",
                    "messages":    [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens":  4000
                },
                timeout=180
            )

            if response.status_code != 200:
                raise ValueError(f"OpenRouter error: {response.status_code}")

            email_content = response.json()["choices"][0]["message"]["content"]

            # Save
            email_dir = self.run_dir / "emails"
            email_dir.mkdir(parents=True, exist_ok=True)
            email_path = email_dir / "nurture-sequences.md"
            email_path.write_text(email_content, encoding="utf-8")

            print(f"  ✅ Emails saved ({len(email_content):,} chars)")

            return {
                "status":     "success",
                "email_path": str(email_path),
                "timestamp":  datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "status":    "error",
                "error":     str(e),
                "timestamp": datetime.now().isoformat()
            }
