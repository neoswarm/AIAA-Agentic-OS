# SKILL: Dream 100 Google Ads Builder

## METADATA
- **Skill Name**: Dream 100 Google Ads Campaign Builder
- **Version**: 2.0
- **Category**: Paid Media Asset Generation
- **API Requirements**: OpenRouter (Gemini 2.0 Flash Thinking)
- **Parent Skill**: SKILL_D100_orchestrator

---

## MISSION
Generate high-converting Google Ads campaigns (3 campaigns + extensions + keywords) optimized for healthcare practices' highest-value offers.

---

## INPUT REQUIREMENTS

**Required:**
- `structured_json` (object): Output from SKILL_D100_scraper
- `seo_insights` (object): Output from SKILL_D100_seo_audit
- `output_directory` (string): Path to save outputs

---

## API CONFIGURATION

**Provider:** OpenRouter
**Model:** `google/gemini-3.0-pro`
**Endpoint:** `https://openrouter.ai/api/v1/chat/completions`

**Authentication:**
```bash
OPENROUTER_API_KEY (from .env)
```

**Request config:**
```json
{
  "model": "google/gemini-3.0-pro",
  "temperature": 0.6,
  "max_tokens": 6000,
  "top_p": 0.9
}
```

---

## EXECUTION LOGIC

### STEP 1: EXTRACT CONTEXT

**From structured_json:**
```javascript
const adsContext = {
  company_name: structured_json.practice.brand_name.value,
  specialty: structured_json.practice.specialty.value,
  services: structured_json.services.map(s => ({
    name: s.name.value,
    category: s.category.value,
    target: s.target_audience.value
  })),
  conditions: structured_json.conditions.map(c => c.name.value),
  differentiators: structured_json.clinical_approach.differentiators.value,
  ideal_patient: structured_json.ideal_patient.who_they_serve.value,
  locations: structured_json.locations.map(l => l.address.value),
  pricing: structured_json.pricing.transparency,
  membership_available: structured_json.patient_journey.memberships.available,
  membership_details: structured_json.patient_journey.memberships.details.value,
  telehealth: structured_json.services.find(s => s.name.value.toLowerCase().includes('telehealth'))
};
```

**From seo_insights:**
```javascript
const seoContext = {
  top_keywords: /* Extract from SEMrush data */,
  high_intent_keywords: /* Keywords with position 4-10, volume >200 */,
  location_modifiers: structured_json.seo_intel.location_modifiers.value,
  primary_city: /* Parse from locations[0] */,
  adjacent_cities: /* From SEO audit */
};
```

**Identify highest-value offer:**
```javascript
// Priority: 1) Membership/program, 2) High-ticket service, 3) Primary service
let primaryOffer = null;
let annualValue = null;

if (adsContext.membership_available) {
  primaryOffer = adsContext.membership_details;
  // Estimate annual value or prompt user
} else {
  // Use highest-value service
  primaryOffer = adsContext.services[0].name;
}
```

**Auto-compute annual value (v2.0 - NO user prompt):**
```javascript
// Parse pricing from structured_json.pricing.prices.value
// Look for monthly membership amounts → multiply × 12
// Look for per-session prices → estimate 2x/month × 12
// Fallback: $5000 default

if (adsContext.membership_details) {
  // Extract highest monthly amount from membership details
  const monthlyMatch = adsContext.membership_details.match(/\$(\d+)\/month/);
  if (monthlyMatch) annualValue = parseInt(monthlyMatch[1]) * 12;
}
if (!annualValue) annualValue = 5000; // Safe default
```

**Auto-detect geographic targeting:**
```javascript
const primary_city = structured_json.seo_intel.location_modifiers.value[0];
const adjacent_cities = structured_json.seo_intel.location_modifiers.value.slice(1, 4);
```

---

### STEP 2: GENERATE GOOGLE ADS CAMPAIGNS

**Prompt to Gemini 2.0 Flash Thinking:**

```
You are a senior direct-response performance marketer and Google Ads architect specializing in high-LTV healthcare and membership-based offers.

TASK
You will be given a structured JSON object containing a full crawl, business intelligence, offerings, positioning, and gaps for a healthcare brand. Your job is to transform that JSON into a **conversion-maximized Google Ads asset system** designed to sell the brand's **highest-value core offer**.

PRIMARY OBJECTIVE
Generate Google Ads campaigns that attract **high-intent, high-income, long-retention users** and convert them into the brand's flagship paid membership or primary offer.

INPUTS:
{
  "practice": {adsContext},
  "seo": {seoContext},
  "primary_offer": {
    "name": "{primaryOffer}",
    "annual_value": {annualValue},
    "type": "membership|service|program"
  }
}

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

Here is the **Refined "Perfect" Output** optimized for the High-LTV {primary_offer} (${annualValue} value).

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
```

**Execute API call:**
```bash
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -H "HTTP-Referer: https://aiaa-agentic-os.local" \
  -H "X-Title: AIAA Dream 100 Ads Builder" \
  -d '{
    "model": "google/gemini-3.0-pro",
    "messages": [
      {
        "role": "user",
        "content": "[FULL PROMPT WITH CONTEXT INJECTED]"
      }
    ],
    "temperature": 0.6,
    "max_tokens": 6000
  }'
```

---

### STEP 3: POST-PROCESS & VALIDATE

**Validation checks:**
1. All 3 campaigns present
2. Each campaign has 5 headlines (≤30 chars each)
3. Each campaign has 2 descriptions (≤90 chars each)
4. 4 sitelinks present (each with name + description)
5. 6 callouts present
6. 5 keywords with explanations

**If validation fails:**
- Identify missing elements
- Retry generation with specific instruction to fix gaps
- Max 2 retries

**Character limit enforcement:**
If any headline/description exceeds limits:
```javascript
headlines.forEach(h => {
  if (h.length > 30) {
    // Truncate intelligently at word boundary
    h = h.substring(0, 27) + '...';
    // Log warning
  }
});
```

---

### STEP 4: GENERATE COMPANION FILES

**File 1: Import-ready CSV for Google Ads Editor**
`{output_directory}/ads/google_ads_import.csv`

```csv
Campaign,Ad Group,Headline 1,Headline 2,Headline 3,Description 1,Description 2,Final URL
Campaign 1,Ad Group 1,{headline1},{headline2},{headline3},{desc1},{desc2},{landing_url}
...
```

**File 2: Extensions CSV**
`{output_directory}/ads/extensions.csv`

```csv
Campaign,Extension Type,Text 1,Text 2
All,Sitelink,{name},{description}
All,Callout,{callout},
...
```

**File 3: Keywords CSV**
`{output_directory}/ads/keywords.csv`

```csv
Campaign,Ad Group,Keyword,Match Type,Max CPC
Campaign 1,Ad Group 1,{keyword},Exact,{suggested_bid}
...
```

**File 4: Setup Guide**
`{output_directory}/ads/SETUP_GUIDE.md`

```markdown
# Google Ads Campaign Setup Guide

## Overview
3 high-converting campaigns optimized for {primary_offer} (${annualValue} LTV)

## Import Instructions

### Step 1: Import Campaigns
1. Open Google Ads Editor
2. File → Import → From file
3. Select: `google_ads_import.csv`
4. Review and post

### Step 2: Add Extensions
1. In Google Ads Editor, select all campaigns
2. Extensions → Import
3. Select: `extensions.csv`

### Step 3: Add Keywords
1. Select each campaign
2. Keywords → Import
3. Select: `keywords.csv`

### Step 4: Set Budgets
Recommended daily budgets:
- Campaign 1 (Medical Mystery): $150-300/day
- Campaign 2 (Condition): $100-200/day
- Campaign 3 (Authority): $75-150/day

### Step 5: Configure Tracking
- Add conversion tracking for: form submissions, phone calls
- Link Google Analytics
- Set up call tracking

## Campaign Details

### Campaign 1: Medical Mystery Solver
[Details from generated content]

### Campaign 2: Condition Remission
[Details from generated content]

### Campaign 3: Virtual Authority
[Details from generated content]

## Ongoing Optimization
- Week 1: Monitor search terms, add negatives
- Week 2: Adjust bids based on conversion data
- Week 3: Test new ad variations
- Month 2: Scale winning campaigns

---
Generated by AIAA Dream 100 Automation v1.0
{timestamp}
```

---

## OUTPUT

**Save main file:**
`{output_directory}/ads/google_ads_campaign.md`

**Success response:**
```json
{
  "status": "success",
  "main_file": "{output_directory}/ads/google_ads_campaign.md",
  "import_csv": "{output_directory}/ads/google_ads_import.csv",
  "extensions_csv": "{output_directory}/ads/extensions.csv",
  "keywords_csv": "{output_directory}/ads/keywords.csv",
  "setup_guide": "{output_directory}/ads/SETUP_GUIDE.md",
  "campaigns_generated": 3,
  "total_headlines": 15,
  "total_keywords": 5,
  "estimated_setup_time_min": 30,
  "timestamp": "ISO-8601"
}
```

**Display to user:**
```
═══════════════════════════════════════════════════════════
✓ Google Ads Campaigns Generated
═══════════════════════════════════════════════════════════

PRIMARY OFFER: {primary_offer} (${annualValue} LTV)

CAMPAIGNS CREATED:
1. Medical Mystery Solver (High Intent)
2. Condition Remission (Volume Driver)
3. Virtual Authority (Trust Builder)

ASSETS:
✓ 15 Headlines (5 per campaign)
✓ 6 Descriptions (2 per campaign)
✓ 4 Sitelinks
✓ 6 Callouts
✓ 5 High-Value Keywords

FILES GENERATED:
→ google_ads_campaign.md (copy-ready)
→ google_ads_import.csv (Google Ads Editor ready)
→ extensions.csv (bulk upload ready)
→ keywords.csv (bulk upload ready)
→ SETUP_GUIDE.md (step-by-step instructions)

ESTIMATED SETUP TIME: 30 minutes

NEXT STEPS:
1. Review campaign copy in google_ads_campaign.md
2. Follow SETUP_GUIDE.md to import into Google Ads
3. Set daily budgets ($325-650 recommended)
4. Launch and monitor

═══════════════════════════════════════════════════════════
```

---

## ERROR HANDLING

**Missing primary offer:**
- Attempt to infer from services
- If unable: Prompt user to specify
- HALT if not provided

**API failure:**
- Retry with exponential backoff (max 3 attempts)
- If persistent: Use fallback template with JSON data
- Log error details

**Invalid character lengths:**
- Auto-truncate with warning
- Log all truncations
- Display summary: "Truncated 3 headlines to meet Google Ads limits"

**Missing LTV/annual value:**
- Prompt user for estimate
- If not provided: Use generic high-value positioning
- Log assumption made

---

## VERSION HISTORY

**1.0** - Initial release
- Gemini 2.0 Flash Thinking for campaign generation
- 3-campaign framework (Mystery Solver, Condition, Authority)
- CSV exports for Google Ads Editor
- Setup guide with optimization timeline
