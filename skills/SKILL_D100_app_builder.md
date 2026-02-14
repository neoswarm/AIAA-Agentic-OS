# SKILL: Dream 100 App Builder

## METADATA
- **Skill Name**: Dream 100 Health Assessment App Builder
- **Version**: 1.0
- **Category**: Interactive Asset Generation
- **API Requirements**: Claude Opus 4.6 (native Claude Code)
- **Parent Skill**: SKILL_D100_orchestrator

---

## MISSION
Generate a premium, brand-aligned, WCAG-compliant health assessment app (single-file HTML) that captures high-intent patient data and redirects to booking with a concise summary.

---

## INPUT REQUIREMENTS

**Required:**
- `structured_json` (object): Output from SKILL_D100_scraper
- `brand_colors` (object): Hex color values (primary, secondary, accent, text, background)
- `booking_url` (string): Validated booking URL or phone number
- `output_directory` (string): Path to save output

---

## EXECUTION LOGIC

### STEP 1: EXTRACT CONTEXT FROM JSON

**Required extraction (with validation):**

```javascript
const context = {
  company_name: structured_json.practice.brand_name.value || structured_json.practice.legal_name.value,
  specialty: structured_json.practice.specialty.value,
  services: structured_json.services.map(s => s.name.value),
  conditions: structured_json.conditions.map(c => c.name.value),
  providers: structured_json.providers.map(p => ({
    name: p.name.value,
    credentials: p.credentials.value,
    specialty: p.specialty.value
  })),
  ideal_patient: structured_json.ideal_patient.who_they_serve.value,
  clinical_approach: structured_json.clinical_approach.differentiators.value,
  patient_journey: structured_json.patient_journey.new_patient_steps.value,
  exclusions: structured_json.ideal_patient.exclusions.value,
  brand_colors: brand_colors,
  booking_url: booking_url
};
```

**Validation:**
- If `company_name` is null: HALT with error "Critical field missing: company name"
- If `services` array is empty: HALT with error "Critical field missing: services"
- If `conditions` array is empty: Prompt user: "No conditions found. Provide comma-separated list of conditions treated:"

---

### STEP 2: ASK MISSING QUESTIONS

**Only ask questions NOT answerable from JSON:**

```
═══════════════════════════════════════════════════════════
HEALTH ASSESSMENT APP - Configuration Required
═══════════════════════════════════════════════════════════

I need to ask a few questions to build the health assessment app.
(Answering from JSON where possible - only asking what's missing)

A) CONVERSION & BOOKING INTENT
1. Primary booking objective:
   [ ] New patient consultation
   [ ] Specific service booking
   [ ] General appointment

2. Geographic/location constraints to surface?
   [Text input or "None"]

3. Social proof allowed?
   [ ] Yes (paste exact copy below)
   [ ] No

B) ASSESSMENT DEPTH & STRUCTURE
4. Desired assessment depth:
   [ ] Quick (5-7 min, ~15 questions)
   [ ] Standard (10-12 min, ~25 questions)
   [ ] Comprehensive (15-20 min, ~40 questions)

5. Required vs optional fields:
   Required: Name, Email, Phone (default)
   Additional required: [User specifies or "None"]

C) BOOKING PAYLOAD RULES
6. Redirect method:
   [ ] URL query parameters (e.g., ?name=John&email=...)
   [ ] Single encoded summary parameter (e.g., ?summary=base64...)
   [ ] Copy-to-clipboard + redirect

7. Fields allowed in booking payload:
   [Default: name, email, phone, primary_concern]
   [User can add: symptoms, medications, insurance, etc.]

8. Character limit for booking payload:
   [Default: 500 characters]

D) END-STATE BEHAVIOR
9. What should users see before redirect?
   [ ] Review & edit their responses
   [ ] Next steps + urgency notice
   [ ] Service recommendation
   [ ] All of the above

10. Booking routing:
    [ ] One link for all services
    [ ] Conditional routing per service/condition

E) BRANDING & LEGAL
11. Brand colors: ✓ Already extracted
12. Mandatory legal/privacy text:
    [Paste verbatim OR "Use standard healthcare disclaimer"]

═══════════════════════════════════════════════════════════
```

**Wait for user responses. Validate each answer before proceeding.**

**Store responses in:**
`{output_directory}/app/config.json`

---

### STEP 3: BUILD APP WITH CLAUDE OPUS 4.6

**Use:** Native Claude Code model (Claude Opus 4.6)

**Prompt:**

```
You are a senior product designer + conversion copywriter + front-end engineer + healthcare-compliance-minded UX writer.

PRIMARY OBJECTIVE
Using ONLY the context and content I provide (no assumptions, no inference), produce a "Dream 100" demo experience that combines:
1) A premium patient-acquisition landing page for {company_name}, and
2) An extremely detailed, high-substance Health Assessment (intake + guided triage-style),

that culminates in a redirect to a booking link carrying a concise, safe summary of user responses suitable for scheduling staff.

This prompt is optimized for **accuracy, constraint-discipline, and repeatable output quality**.

---

NON-NEGOTIABLE RULES
- Use ONLY information explicitly provided in the pasted context and content.
- Do NOT infer demographics, conditions, compliance rules, tone, or logic.
- All code must be in ONE self-contained HTML file (embedded CSS + JS).
- No external libraries, assets, analytics, APIs, or network calls.
- Client-side only; in-memory data only (optional copy/print allowed).
- Medical responsibility enforced: no diagnosis, no guarantees, no treatment claims.
- USE BRAND COLORS: {brand_colors}
- ENSURE ALL MULTI-SELECT BUTTONS ACTUALLY ALLOW MULTIPLE SELECTABLE ITEMS (AND ALLOW USER TO DE-SELECT)

---

CONTEXT (FROM JSON):
{
  "company_name": "{company_name}",
  "specialty": "{specialty}",
  "services": {services},
  "conditions": {conditions},
  "providers": {providers},
  "ideal_patient": {ideal_patient},
  "clinical_approach": {clinical_approach},
  "patient_journey": {patient_journey},
  "exclusions": {exclusions}
}

USER CONFIGURATION:
{
  "booking_objective": "{booking_objective}",
  "location_constraints": "{location_constraints}",
  "social_proof": "{social_proof}",
  "assessment_depth": "{assessment_depth}",
  "required_fields": {required_fields},
  "redirect_method": "{redirect_method}",
  "payload_fields": {payload_fields},
  "payload_char_limit": {payload_char_limit},
  "end_state_behavior": "{end_state_behavior}",
  "booking_routing": "{booking_routing}",
  "legal_text": "{legal_text}",
  "booking_url": "{booking_url}"
}

---

OUTPUT DISCIPLINE
When building:
- Mobile-first, responsive, WCAG-aware accessibility.
- All selectable UI controls MUST show unmistakable selected + focus states
  (high-contrast, persistent, keyboard-accessible).
- Use fieldset/legend, labels, aria where appropriate.
- Clear disclaimers ("Not medical advice," emergency guidance, etc.).
- Red-flag logic ONLY if explicitly provided in content.

---

BUILD SPECIFICATION

1) Patient Acquisition Landing Page
- Clear value prop tied strictly to offerings content
- "How it works" flow
- Offerings cards (benefit-led, compliant)
- Trust & safety section
- Sticky mobile CTA

2) Extremely Detailed Health Assessment
- Multi-step flow with progress + time estimate
- Sections derived ONLY from provided content
- Inputs: chips/toggles, sliders, checklists, text, dates, long-form narrative
- Strong microcopy without medical claims
- Review & edit step

3) Results & Booking Transition
- Concise, human-readable Booking Summary
- Optional JSON view
- Copy Summary action
- Redirect to booking link with payload
- Safety disclaimers and emergency guidance

---

FINAL OUTPUT
Return ONLY: Complete single-file HTML/JS in ONE code block

No explanations. No filler. No assumptions.
```

**Execute prompt and capture response.**

---

### STEP 4: VALIDATE & SAVE OUTPUT

**Validation checks:**
1. Response is valid HTML5
2. Contains `<!DOCTYPE html>`
3. Contains all required sections (landing, assessment, results)
4. Brand colors are applied correctly
5. Booking URL is present in redirect logic
6. No external dependencies (check for `<script src=`, `<link href=` to external URLs)

**If validation fails:**
- Log specific error
- Retry generation once with error feedback
- If still fails: HALT with detailed error message

**Save output:**
```
{output_directory}/app/health_assessment.html
```

**Generate companion files:**

1. **README.md** - Deployment instructions:
```markdown
# Health Assessment App - Deployment Guide

## File
`health_assessment.html`

## How to Deploy

### Option 1: Direct Hosting
1. Upload `health_assessment.html` to your web host
2. Access via: `https://yourdomain.com/health-assessment.html`

### Option 2: Embed on Existing Page
1. Copy the HTML content
2. Paste into your page builder (WordPress, Webflow, etc.)
3. Ensure no conflicting CSS/JS

### Option 3: Standalone App
1. Host on Vercel/Netlify for free:
   - Drag and drop file to Vercel
   - Get instant URL

## Testing
- Test on mobile (required)
- Test all multi-select buttons
- Test booking redirect with sample data
- Verify brand colors display correctly

## Customization
Edit these sections in the HTML:
- Line 45-60: Brand colors (CSS variables)
- Line 250-300: Assessment questions
- Line 450: Booking URL

## Support
Generated by AIAA Dream 100 Automation v1.0
{timestamp}
```

2. **config.json** - App configuration:
```json
{
  "app_version": "1.0",
  "generated_at": "ISO-8601",
  "company_name": "string",
  "booking_url": "string",
  "brand_colors": {object},
  "assessment_depth": "string",
  "redirect_method": "string",
  "payload_char_limit": number,
  "required_fields": ["array"],
  "sections_included": ["array"]
}
```

---

## OUTPUT

**Success:**
```json
{
  "status": "success",
  "html_path": "{output_directory}/app/health_assessment.html",
  "readme_path": "{output_directory}/app/README.md",
  "config_path": "{output_directory}/app/config.json",
  "file_size_kb": number,
  "validation_passed": true,
  "timestamp": "ISO-8601"
}
```

**Display to user:**
```
═══════════════════════════════════════════════════════════
✓ Health Assessment App Generated
═══════════════════════════════════════════════════════════

FILE: {output_directory}/app/health_assessment.html
SIZE: {file_size_kb} KB

FEATURES INCLUDED:
✓ Premium landing page with {company_name} branding
✓ {assessment_depth} health assessment flow
✓ Mobile-responsive, WCAG-compliant
✓ Booking redirect to: {booking_url}
✓ Brand colors applied: {brand_colors.primary}

NEXT STEPS:
1. Open file in browser to preview
2. Test on mobile device
3. Deploy using instructions in README.md

═══════════════════════════════════════════════════════════
```

---

## ERROR HANDLING

**Critical field missing:**
- Display error: "Cannot build app: missing {field_name}"
- Prompt user to provide missing data manually
- Update JSON and retry

**Generation timeout (>5 min):**
- Cancel request
- Retry with simplified prompt (reduce assessment depth)
- If still fails: HALT

**Invalid HTML output:**
- Log validation errors
- Display to user: "Generated HTML failed validation: {errors}"
- Retry once
- If fails again: Save partial output and HALT

---

## TESTING

**Test with minimal JSON:**
```json
{
  "company_name": "Test Clinic",
  "specialty": "Functional Medicine",
  "services": ["Consultation", "Lab Testing"],
  "conditions": ["Fatigue", "Gut Issues"],
  "brand_colors": {
    "primary": "#2563eb",
    "secondary": "#1e40af"
  },
  "booking_url": "https://example.com/book"
}
```

**Expected:**
- HTML file generates in < 3 minutes
- File size: 50-150 KB
- Valid HTML5
- All validation checks pass

---

## VERSION HISTORY

**1.0** - Initial release
- Claude Opus 4.6 single-file HTML generation
- WCAG-compliant, mobile-first design
- Multi-select chip interactions
- Booking redirect with configurable payload
- Full validation and error handling
