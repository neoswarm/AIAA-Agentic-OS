# SKILL: Dream 100 Email Sequence Builder

## METADATA
- **Skill Name**: Dream 100 Email Sequence Builder
- **Version**: 1.0
- **Category**: Email Marketing Asset Generation
- **API Requirements**: OpenAI GPT-4o (via OpenRouter for cost optimization)
- **Parent Skill**: SKILL_D100_orchestrator

---

## MISSION
Generate a 3-email "Speed-to-Trust" nurture sequence triggered after health assessment completion, designed to build belief and drive bookings.

---

## INPUT REQUIREMENTS

**Required:**
- `structured_json` (object): Output from SKILL_D100_scraper
- `booking_url` (string): Validated booking URL
- `output_directory` (string): Path to save outputs

---

## API CONFIGURATION

**Provider:** Direct OpenAI API
**Model:** `gpt-4o`
**Endpoint:** `https://api.openai.com/v1/chat/completions`

**Authentication:**
```bash
OPENAI_API_KEY (from .env)
```

**Request config:**
```json
{
  "model": "gpt-4o",
  "temperature": 0.7,
  "max_tokens": 4000,
  "top_p": 0.9
}
```

---

## EXECUTION LOGIC

### STEP 1: EXTRACT EMAIL CONTEXT

**From structured_json:**
```javascript
const emailContext = {
  company_name: structured_json.practice.brand_name.value,
  specialty: structured_json.practice.specialty.value,
  conditions: structured_json.conditions.map(c => c.name.value),
  services: structured_json.services.map(s => s.name.value),
  clinical_approach: {
    differentiators: structured_json.clinical_approach.differentiators.value,
    philosophy: structured_json.clinical_approach.philosophy.value,
    modalities: structured_json.clinical_approach.modalities.value
  },
  patient_journey: {
    discovery_call: structured_json.patient_journey.discovery_call.description.value,
    consult_expectations: structured_json.patient_journey.consult_expectations.value
  },
  providers: structured_json.providers.map(p => ({
    name: p.name.value,
    credentials: p.credentials.value,
    specialty: p.specialty.value,
    bio_summary: p.bio_summary.value
  })),
  trust_signals: {
    testimonials_present: structured_json.trust_signals.testimonials.present,
    testimonial_themes: structured_json.trust_signals.testimonials.themes.value,
    awards: structured_json.trust_signals.awards.value
  },
  booking_url: booking_url
};
```

**Define personalization variables:**
```javascript
const variables = {
  // Required
  FIRST_NAME: "[FIRST_NAME]",
  PRIMARY_SYMPTOM: "[PRIMARY_SYMPTOM]",
  BOOKING_LINK: booking_url,
  PROVIDER_OR_PRACTICE_NAME: emailContext.company_name,

  // Optional (from assessment)
  SECONDARY_SYMPTOM: "[SECONDARY_SYMPTOM]",
  DURATION_OR_TRIGGER: "[DURATION_OR_TRIGGER]",
  IMPACT_ON_LIFE: "[IMPACT_ON_LIFE]",
  KEY_ASSESSMENT_INSIGHT: "[KEY_ASSESSMENT_INSIGHT]",
  RECOMMENDED_SERVICE_OR_FOCUS: "[RECOMMENDED_SERVICE_OR_FOCUS]",
  PATIENT_GOAL: "[PATIENT_GOAL]"
};
```

---

### STEP 2: GENERATE EMAIL SEQUENCE

**Prompt to GPT-4o:**

```
You are a senior healthcare conversion copywriter + lifecycle marketing strategist.

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
  "company_name": "{company_name}",
  "specialty": "{specialty}",
  "conditions_treated": {conditions},
  "services_offered": {services},
  "clinical_approach": {
    "differentiators": {differentiators},
    "philosophy": {philosophy},
    "modalities": {modalities}
  },
  "providers": {providers},
  "patient_journey": {patient_journey},
  "trust_signals": {trust_signals},
  "booking_url": "{booking_url}"
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

BEGIN.
```

**Execute API call:**
```bash
curl -X POST "https://api.openai.com/v1/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {
        "role": "user",
        "content": "[FULL PROMPT WITH CONTEXT INJECTED]"
      }
    ],
    "temperature": 0.7,
    "max_tokens": 4000
  }'
```

---

### STEP 3: POST-PROCESS & STRUCTURE

**Parse response into structured format:**
```javascript
const emails = parseEmailResponse(response); // Extract 3 emails

// Validate each email has:
emails.forEach((email, index) => {
  if (!email.subject_line) throw new Error(`Email ${index+1} missing subject line`);
  if (!email.body) throw new Error(`Email ${index+1} missing body`);
  if (!email.cta) throw new Error(`Email ${index+1} missing CTA`);
  if (email.body.length > 2000) {
    console.warn(`Email ${index+1} body is long (${email.body.length} chars)`);
  }
});
```

**Check for compliance issues:**
- No diagnosis language ("you have", "you need treatment for")
- No guaranteed outcomes ("will cure", "will eliminate")
- Includes disclaimer where appropriate
- Emergency guidance if mentioning serious symptoms

**If issues found:**
- Log warnings
- Optionally retry with compliance feedback
- Display warnings to user

---

### STEP 4: GENERATE OUTPUT FILES

**File 1: Main Sequence (Markdown)**
`{output_directory}/emails/sequence.md`

```markdown
# 3-Email Speed-to-Trust Sequence
**Practice:** {company_name}
**Trigger:** Health Assessment Completion
**Generated:** {timestamp}

---

## EMAIL 1: Smart Practice Value Drop
**Send:** Immediately after assessment
**Subject:** {subject_line}

{body}

{cta}

---
**Personalization Variables Used:**
- [FIRST_NAME]
- [PRIMARY_SYMPTOM]
- [KEY_ASSESSMENT_INSIGHT]

---

## EMAIL 2: Mechanism Story
**Send:** 2 days after Email 1
**Subject:** {subject_line}

{body}

{cta}

---
**Personalization Variables Used:**
- [FIRST_NAME]
- [PRIMARY_SYMPTOM]
- [DURATION_OR_TRIGGER]

---

## EMAIL 3: Proof & Results
**Send:** 4 days after Email 2
**Subject:** {subject_line}

{body}

{cta}

**Disclaimer:**
Results may vary. Individual outcomes depend on many factors. This email does not constitute medical advice. Consult with a healthcare professional.

---
**Personalization Variables Used:**
- [FIRST_NAME]
- [PRIMARY_SYMPTOM]
- [BOOKING_LINK]

---

_Generated by AIAA Dream 100 Automation v1.0_
```

**File 2: Plain Text Versions**
`{output_directory}/emails/plain_text.txt`

```
=== EMAIL 1 ===
SUBJECT: {subject_line}

{body in plain text, no HTML}

{cta}

---

=== EMAIL 2 ===
SUBJECT: {subject_line}

{body in plain text}

{cta}

---

=== EMAIL 3 ===
SUBJECT: {subject_line}

{body in plain text}

{cta}

Results may vary. Individual outcomes depend on many factors.
```

**File 3: HTML Versions (Basic)**
`{output_directory}/emails/html_version.html`

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Email Sequence Preview</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
    .email { margin-bottom: 40px; border: 1px solid #e0e0e0; padding: 20px; }
    .subject { font-size: 18px; font-weight: 600; margin-bottom: 10px; color: #000; }
    .body { margin-bottom: 20px; }
    .cta { background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; display: inline-block; border-radius: 4px; }
    .disclaimer { font-size: 12px; color: #666; margin-top: 20px; font-style: italic; }
  </style>
</head>
<body>
  <div class="email">
    <div class="subject">Email 1: {subject_line}</div>
    <div class="body">{body with basic HTML formatting}</div>
    <a href="{booking_url}" class="cta">{cta_text}</a>
  </div>

  <div class="email">
    <div class="subject">Email 2: {subject_line}</div>
    <div class="body">{body with basic HTML formatting}</div>
    <a href="{booking_url}" class="cta">{cta_text}</a>
  </div>

  <div class="email">
    <div class="subject">Email 3: {subject_line}</div>
    <div class="body">{body with basic HTML formatting}</div>
    <a href="{booking_url}" class="cta">{cta_text}</a>
    <div class="disclaimer">Results may vary. Individual outcomes depend on many factors. This email does not constitute medical advice.</div>
  </div>
</body>
</html>
```

**File 4: ESP Import Templates**
`{output_directory}/emails/esp_imports/`

**Klaviyo format:** `klaviyo_import.csv`
```csv
Email Name,Subject,Plain Text,HTML,Send Delay
Email 1 - Value Drop,{subject},{plain_text},{html},0 days
Email 2 - Mechanism,{subject},{plain_text},{html},2 days
Email 3 - Proof,{subject},{plain_text},{html},6 days
```

**ConvertKit format:** `convertkit_import.json`
```json
{
  "sequence_name": "{company_name} Assessment Follow-up",
  "trigger": "Tag: assessment_complete",
  "emails": [
    {
      "name": "Email 1 - Value Drop",
      "subject": "{subject}",
      "content": "{html}",
      "delay_days": 0
    },
    ...
  ]
}
```

**File 5: Setup Guide**
`{output_directory}/emails/SETUP_GUIDE.md`

```markdown
# Email Sequence Setup Guide

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
3. Import emails from `klaviyo_import.csv`
4. Replace personalization tokens:
   - `[FIRST_NAME]` → `{{ person.first_name }}`
   - `[PRIMARY_SYMPTOM]` → `{{ event.PRIMARY_SYMPTOM }}`
   - etc.
5. Set time delays: 0d, 2d, 6d
6. Test with sample profile

### Option 2: ConvertKit
1. Create Automation: "Assessment Nurture"
2. Import from `convertkit_import.json`
3. Map custom fields to assessment data
4. Set delays and test

### Option 3: ActiveCampaign
1. Create Automation
2. Copy email content from `sequence.md`
3. Paste into email editor
4. Configure personalization tags
5. Set wait conditions: 2 days, 4 days

### Option 4: Custom/Manual Setup
1. Use `plain_text.txt` for plain versions
2. Use `html_version.html` as template
3. Customize styling to match brand
4. Set up automation in your ESP

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
```

---

## OUTPUT

**Success response:**
```json
{
  "status": "success",
  "main_file": "{output_directory}/emails/sequence.md",
  "plain_text": "{output_directory}/emails/plain_text.txt",
  "html_preview": "{output_directory}/emails/html_version.html",
  "klaviyo_import": "{output_directory}/emails/esp_imports/klaviyo_import.csv",
  "convertkit_import": "{output_directory}/emails/esp_imports/convertkit_import.json",
  "setup_guide": "{output_directory}/emails/SETUP_GUIDE.md",
  "emails_generated": 3,
  "total_word_count": number,
  "personalization_variables": ["array"],
  "compliance_checks_passed": true,
  "timestamp": "ISO-8601"
}
```

**Display to user:**
```
═══════════════════════════════════════════════════════════
✓ Email Sequence Generated
═══════════════════════════════════════════════════════════

SEQUENCE: 3-Email Speed-to-Trust
TRIGGER: Health Assessment Completion

EMAILS:
1. Smart Practice Value Drop (Send: Immediately)
2. Mechanism Story (Send: Day 2)
3. Proof & Results (Send: Day 6)

PERSONALIZATION:
✓ [FIRST_NAME]
✓ [PRIMARY_SYMPTOM]
✓ [BOOKING_LINK]
✓ 5 additional optional variables

FILES GENERATED:
→ sequence.md (master copy)
→ plain_text.txt (ESP import ready)
→ html_version.html (preview in browser)
→ klaviyo_import.csv (Klaviyo ready)
→ convertkit_import.json (ConvertKit ready)
→ SETUP_GUIDE.md (step-by-step)

COMPLIANCE:
✓ No diagnosis language
✓ Disclaimers included
✓ Professional tone maintained

NEXT STEPS:
1. Review emails in sequence.md
2. Open html_version.html to preview
3. Follow SETUP_GUIDE.md for ESP setup
4. Test with sample data before going live

═══════════════════════════════════════════════════════════
```

---

## ERROR HANDLING

**API failure:**
- Retry with exponential backoff (max 3 attempts)
- If persistent: Use fallback template-based generation
- Log error details

**Missing context:**
- Identify which fields are null
- Generate emails with placeholders
- Display warning: "Limited context - review emails carefully"

**Compliance issues detected:**
- Log specific issues
- Retry generation with compliance feedback
- If unresolved after 2 retries: Flag for manual review

**Invalid email structure:**
- Re-parse response
- If still invalid: Request user to provide manual input
- HALT if cannot generate valid emails after 3 attempts

---

## TESTING

**Test with minimal context:**
```json
{
  "company_name": "Test Clinic",
  "specialty": "Functional Medicine",
  "conditions": ["Fatigue", "Gut Issues"],
  "booking_url": "https://example.com/book"
}
```

**Expected:**
- 3 emails generated
- Each 150-300 words
- All personalization variables present
- Compliance checks pass
- Generation time < 2 minutes

---

## VERSION HISTORY

**1.0** - Initial release
- GPT-4o via OpenRouter for cost optimization
- 3-email Speed-to-Trust framework
- Multi-ESP export formats
- HTML preview generation
- Compliance validation
