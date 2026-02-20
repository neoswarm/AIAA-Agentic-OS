# SKILL: Dream 100 Outreach Orchestrator 2.0

## METADATA
- **Skill Name**: Dream 100 Outreach Orchestrator
- **Version**: 2.0
- **Category**: Automation Workflow
- **Required Skills**: SKILL_D100_scraper, SKILL_D100_seo_audit, SKILL_D100_app_builder, SKILL_D100_ads_builder, SKILL_D100_email_builder
- **API Requirements**: OpenRouter (Gemini), OpenAI GPT-4o, Claude (native)
- **Optimization Target**: Complete full run in <15 minutes with ZERO user intervention after initial input

---

## MISSION
Orchestrate the complete Dream 100 Outreach automation workflow for healthcare practices. v2.0 eliminates all manual pauses, auto-computes all defaults from scraped data, and maximizes parallel execution.

---

## CRITICAL RULES (v2.0)

1. **ZERO INTERVENTION**: After user provides initial input (URL + booking + context), the ENTIRE workflow runs without asking the user ANYTHING. All config values are auto-computed from the structured JSON.
2. **MAXIMUM PARALLELISM**: Launch every independent task simultaneously. Never run sequentially what can run in parallel.
3. **EXACT PROMPTS**: Use the EXACT prompts from each skill file. Never improvise or paraphrase.
4. **AUTO-COMPUTE EVERYTHING**: LTV, primary offer, adjacent cities, brand colors, app config -- ALL derived from JSON data. No user prompts.
5. **FAIL FORWARD**: If any single deliverable fails, continue generating the rest. Report failures at the end.
6. **SINGLE CONTEXT LOAD**: Load structured JSON once, pass relevant slices to all downstream tasks. Never re-read the same file twice.

---

## WORKFLOW OVERVIEW (v2.0)

```
USER INPUT (30 sec)
    │
    ▼
PHASE 1: SCRAPE + EXTRACT (3-5 min)
    │ Firecrawl/Puppeteer scrape
    │ Brand color extraction (parallel)
    │ Raw markdown compilation
    │ JSON conversion
    │
    ▼
PHASE 2: ALL ASSETS IN PARALLEL (5-8 min)
    │ ┌─ BrightLocal Keywords (GPT-4o)
    │ ├─ Google Ads (Gemini via OpenRouter)
    │ ├─ Email Sequence (GPT-4o)
    │ ├─ Health Assessment App (Claude native)
    │ └─ SEO Insights from SEMrush CSV (if provided)
    │
    ▼
PHASE 3: COMPILE (1-2 min)
    │ COMPLETE_DELIVERABLES.md
    │ GAMMA_FILE.md
    │
    ▼
DONE (<15 min total)
```

---

## EXECUTION LOGIC

### STEP 1: VALIDATE INPUTS (30 seconds max)

**Required from user (ONE prompt, all at once):**
1. **Website URL** (required)
2. **Booking URL or Phone** (required)
3. **Practice context** (optional - tier, revenue, CEO, pricing, etc.)

**Auto-detect from context string:**
- Practice name → parse from URL or context
- Tier level → parse from context (e.g., "Tier 195 High")
- CEO name → parse from context
- Pricing data → parse from context (e.g., "$179 base, $150-$275 membership")
- Primary city → parse from URL domain or context

**Validation:**
- URL must be valid HTTP/HTTPS
- Booking must be valid URL or phone
- If invalid after 1 attempt: HALT (do not loop)

**Create run directory immediately:**
```
/output/d100_runs/{slug}_{YYYYMMDD_HHMMSS}/
├── scrape_data/
├── seo_data/
├── ads/
├── emails/
└── app/
```

---

### STEP 2: SCRAPE + EXTRACT (Parallel - 3-5 min)

**Launch simultaneously:**

**2A: Website Scrape**
- Use Firecrawl CLI (`firecrawl scrape`) as primary
- Fallback: Puppeteer (`mcp__puppeteer__puppeteer_navigate` + `puppeteer_evaluate`)
- Scrape main pages: /, /services/, /about/, /locations/, /people/, /insurance-payments/, individual service pages
- Save raw output to `scrape_data/raw_puppeteer.md`

**2B: Brand Color Extraction (parallel with scrape)**
- Fetch homepage CSS/HTML
- Extract primary, secondary, accent, text colors
- Fallback: Use neutral palette if extraction fails
- Store in memory for app builder

**2C: Compile Raw Scrape**
- After 2A completes: Compile into 10-section `raw_scrape.md` format
- Sections: Pages Visited, Practice ID, Team/Providers, Services, Conditions, Ideal Patient, Clinical Approach, Patient Journey, Pricing/Insurance, Trust/Credibility, SEO Intelligence

**2D: Convert to Structured JSON**
- After 2C completes: Use EXACT prompt from SKILL_D100_scraper.md (lines 300-823)
- Claude native conversion (no external API)
- Validate all 14 top-level schema keys
- Save to `scrape_data/structured_data.json`

---

### STEP 3: ALL ASSETS IN PARALLEL (5-8 min)

**As soon as structured JSON is ready, launch ALL of these simultaneously:**

**3A: BrightLocal Keywords**
- API: OpenAI GPT-4o (Direct)
- Use EXACT prompt from SKILL_D100_seo_audit.md (lines 52-105)
- Auto-compute inputs from JSON:
  - Services → `structured_json.services[].name.value`
  - Conditions → `structured_json.conditions[].name.value`
  - Primary city → Parse from `structured_json.locations[0].address.value` OR `structured_json.seo_intel.location_modifiers.value[0]`
  - Adjacent cities → Take cities 1-3 from `structured_json.seo_intel.location_modifiers.value` (skip primary city)
- Output: `seo_data/brightlocal_keywords.txt` (100 keywords)

**3B: Google Ads Campaigns**
- API: OpenRouter (Gemini 2.0 Flash or latest available)
- Use EXACT prompt from SKILL_D100_ads_builder.md (lines 128-228)
- Auto-compute inputs from JSON:
  - `adsContext` → Extract from JSON per skill spec (lines 54-71)
  - `seoContext` → Build from `structured_json.seo_intel` (primary_keywords, location_modifiers, conversion_ctas)
  - `primaryOffer` → Auto-detect: If `memberships.available == true`, use membership name. Else use first service.
  - `annualValue` → Auto-compute: Parse pricing from `structured_json.pricing.prices.value`. If membership, multiply monthly × 12. If no pricing: default to $5000.
- **DO NOT prompt user for LTV or offer details. Compute from data.**
- Output: `ads/google_ads_campaign.md`
- Method: Write Python script with `urllib.request` (avoids bash permission issues in subagents)

**3C: Email Sequence**
- API: OpenAI GPT-4o (Direct)
- Use EXACT prompt from SKILL_D100_email_builder.md (lines 109-247)
- Auto-compute `emailContext` from JSON per skill spec (lines 54-81)
- **DO NOT prompt user for anything.**
- Output: `emails/sequence.md`
- Method: Write Python script with `urllib.request`

**3D: Health Assessment App**
- Built by: Claude Opus 4.6 (latest) -- native, NO external API
- **MUST use model: opus** when launching subagent (Task tool `model: "opus"`)
- Use EXACT prompt from SKILL_D100_app_builder.md (lines 100-197)
- Auto-compute ALL config from JSON:
  - `company_name` → `practice.brand_name.value`
  - `services` → `services[].name.value`
  - `conditions` → `conditions[].name.value`
  - `brand_colors` → From Step 2B extraction
  - `booking_url` → From user input
  - `providers` → `providers[].name.value`
  - `ideal_patient` → `ideal_patient.who_they_serve.value`
  - Question categories → Auto-derive from conditions + services
- **DO NOT ask user 12 config questions. Compute all from JSON.**
- Output: `app/health_assessment.html` (single-file, self-contained)

**3E: SEMrush Analysis (OPTIONAL - only if CSV provided)**
- If user provided SEMrush CSV path in initial context: Analyze it
- If not provided: SKIP (do not pause workflow)
- Use EXACT prompt from SKILL_D100_seo_audit.md (lines 303-403)
- Output: `seo_data/seo_insights.md`

**3F: BrightLocal Audit Analysis (OPTIONAL - only if PDF provided)**
- If user provided BrightLocal PDF path in initial context: Analyze it
- If not provided: SKIP (do not pause workflow)
- Use EXACT prompt from SKILL_D100_seo_audit.md (lines 168-243)
- Output: `seo_data/local_audit_insights.md`

---

### STEP 4: COMPILE OUTPUTS + GAMMA PRESENTATION (2-5 min)

**After all parallel tasks complete (or fail), immediately do ALL of these in parallel:**

**4A: COMPLETE_DELIVERABLES.md**
- Practice intelligence summary (from JSON)
- All deliverable contents inline
- File index
- SEMrush data snapshot (if CSV was provided)
- Mark any failed deliverables as "GENERATION FAILED - [reason]"

**4B: GAMMA_FILE.md**
- 12-slide presentation-ready content
- All deliverable summaries
- Competitive position analysis
- Next steps

**4C: GAMMA PRESENTATION (MANDATORY - always run)**
- Use module: `modules/d100_gamma.py` OR standalone `run_gamma.py` script
- Template ID: `g_tibdaac6hk58l4v`
- API: Gamma API (`GAMMA_API_KEY` from .env)
- Reads: structured_data.json, google_ads_campaign.md, sequence.md, seo_insights.md (if exists)
- Builds prompt from all deliverables, calls Gamma API, polls for URL (up to 5 min)
- Saves `gamma_response.json` to run directory
- Sends Slack notification with live Gamma URL
- **Method:** Write standalone Python script with `urllib.request` (same pattern as ads/emails)
- **v2.0 filenames:** `google_ads_campaign.md` (not `google-ads-campaigns.md`), `sequence.md` (not `nurture-sequences.md`)
- If Gamma API fails: Log error, continue (non-blocking)

**Display final summary:**
```
═══════════════════════════════════════════════════════════
DREAM 100 COMPLETE - {company_name}
═══════════════════════════════════════════════════════════

Run ID: {run_id}
Time: {elapsed_minutes} minutes
Status: {X}/7 deliverables generated

OUTPUTS:
├── scrape_data/structured_data.json     {status}
├── seo_data/brightlocal_keywords.txt    {status}
├── ads/google_ads_campaign.md           {status}
├── emails/sequence.md                   {status}
├── app/health_assessment.html           {status}
├── COMPLETE_DELIVERABLES.md             {status}
├── GAMMA_FILE.md                        {status}
└── Gamma Presentation                   {gamma_url or FAILED}

{if_semrush: SEMrush analysis included}
{if_brightlocal: BrightLocal analysis included}

NEXT STEPS:
1. Review Gamma presentation: {gamma_url}
2. Upload BrightLocal keywords for audit (if not done)
3. Review deliverables in output directory
4. Deploy health assessment app
═══════════════════════════════════════════════════════════
```

---

## AUTO-COMPUTATION RULES

### Primary Offer Detection
```
IF pricing.prices.value contains "membership" → use that
ELSE IF patient_journey.memberships.available == true → use membership details
ELSE → use first service with highest price
ELSE → use first service name, default LTV $5000
```

### Annual Value Computation
```
IF pricing contains monthly amount → multiply × 12
IF pricing contains per-session + membership → use membership × 12
IF no pricing found → default $5000
```

### Adjacent Cities
```
TAKE seo_intel.location_modifiers.value
REMOVE primary city (index 0 or parsed from locations)
RETURN first 3 remaining cities
IF < 3 cities → use what's available
```

### Brand Colors
```
IF extracted from CSS → use extracted
ELSE IF user provided → use provided
ELSE → neutral modern palette:
  primary: "#2563eb"
  secondary: "#1e40af"
  accent: "#3b82f6"
  text: "#1f2937"
  background: "#ffffff"
```

### App Config (replaces 12 user questions)
```
company_name     → practice.brand_name.value
specialty        → practice.specialty.value
services_list    → services[].name.value (all)
conditions_list  → conditions[].name.value (top 20 by relevance)
providers_count  → providers.length or parse from trust_signals
locations_count  → locations.length
booking_url      → from user input
phone            → contact.phone or parse from locations
hours            → patient_journey or "Contact for hours"
insurance        → pricing.insurance_accepted.value
has_telehealth   → check if any service/location mentions virtual/telehealth
has_membership   → patient_journey.memberships.available
```

---

## SUBAGENT EXECUTION PATTERN

For API calls (Ads, Emails, Keywords), use this proven pattern:

```python
# Write standalone Python script with urllib.request
# This avoids bash permission issues in subagents
import json, os, urllib.request

# Load API key from .env
with open('.env') as f:
    for line in f:
        if line.startswith('KEY_NAME='):
            api_key = line.strip().split('=', 1)[1]

# Build request
payload = json.dumps({...})
req = urllib.request.Request(url, data=payload.encode(), headers={...})

# Execute
with urllib.request.urlopen(req, timeout=120) as resp:
    result = json.loads(resp.read().decode())
    content = result['choices'][0]['message']['content']

# Save output
with open(output_path, 'w') as f:
    f.write(content)
```

---

## ERROR HANDLING (v2.0)

**Fail-forward principle:** Never halt the entire workflow for a single deliverable failure.

| Error | Action |
|-------|--------|
| Scrape fails | Try Firecrawl → Puppeteer → halt (need data) |
| JSON conversion fails | Retry once with smaller context → halt if still fails |
| API call fails (Ads/Emails/Keywords) | Retry once with exponential backoff → mark as FAILED, continue |
| App generation fails | Retry once → mark as FAILED, continue |
| File write fails | Retry with alternate path → log error |
| Color extraction fails | Use neutral palette, continue |
| SEMrush/BrightLocal not provided | Skip, continue (optional deliverables) |

---

## TIMING TARGETS (v2.0)

| Phase | Target | Max |
|-------|--------|-----|
| Input validation | 30 sec | 1 min |
| Scrape + compile + JSON | 4 min | 6 min |
| All assets (parallel) | 5 min | 8 min |
| Compile outputs | 1 min | 2 min |
| **TOTAL** | **~10 min** | **~15 min** |

---

## FILE STRUCTURE

```
/output/d100_runs/{slug}_{TIMESTAMP}/
├── COMPLETE_DELIVERABLES.md
├── GAMMA_FILE.md
├── scrape_data/
│   ├── raw_puppeteer.md
│   ├── raw_scrape.md
│   └── structured_data.json
├── seo_data/
│   ├── brightlocal_keywords.txt
│   ├── seo_insights.md (if SEMrush provided)
│   └── local_audit_insights.md (if BrightLocal provided)
├── app/
│   └── health_assessment.html
├── ads/
│   ├── google_ads_campaign.md
│   └── generate_ads.py
└── emails/
    ├── sequence.md
    └── generate_emails.py
```

---

## USAGE

```
User: "Run D100 for [website] booking: [url] [context...]"
Claude: [Executes entire workflow autonomously in ~10 min]
```

Optional SEMrush/BrightLocal data can be included in initial input:
```
User: "Run D100 for [website] booking: [url] SEMrush: /path/to/csv BrightLocal: /path/to/pdf"
```

---

## VERSION HISTORY

**2.0** - Performance optimization release
- Eliminated manual BrightLocal/SEMrush pause (now optional inputs)
- Auto-computes ALL config from JSON (LTV, offer, cities, app config)
- Zero user intervention after initial input
- Target: <15 min total runtime
- Python urllib.request pattern for reliable API calls in subagents
- Fail-forward error handling

**1.0** - Initial release
- 6-step orchestration with manual SEO pause
- Required user input at multiple points
- Sequential asset generation
