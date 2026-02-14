# SKILL: Dream 100 Outreach Orchestrator 1.0

## METADATA
- **Skill Name**: Dream 100 Outreach Orchestrator
- **Version**: 1.0
- **Category**: Automation Workflow
- **Required Skills**: SKILL_D100_scraper, SKILL_D100_seo_audit, SKILL_D100_app_builder, SKILL_D100_ads_builder, SKILL_D100_email_builder
- **API Requirements**: OpenRouter (Perplexity, Gemini), OpenAI, Claude Opus 4.6

---

## MISSION
Orchestrate the complete Dream 100 Outreach automation workflow for healthcare practices, coordinating data collection, analysis, and asset generation for personalized outreach campaigns.

---

## WORKFLOW OVERVIEW

### Phase 1: INPUT VALIDATION & COLLECTION
### Phase 2: WEBSITE SCRAPING & JSON GENERATION
### Phase 3: SEO DATA COLLECTION (MANUAL PAUSE)
### Phase 4: PARALLEL ASSET GENERATION
### Phase 5: OUTPUT COMPILATION

---

## EXECUTION LOGIC

### STEP 1: VALIDATE REQUIRED INPUTS

**Prompt user for:**
1. **Website URL** (required)
2. **Booking URL or Phone Number** (required)
3. **Additional Context** (optional)

**Validation Rules:**
- Website URL: Must be valid HTTP/HTTPS URL
- Booking URL: Must be valid URL OR valid phone number (E.164 format acceptable)
- If validation fails: Re-prompt until valid
- Do NOT proceed until all required inputs are valid

**Store validated inputs in:**
```
/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/output/d100_runs/[TIMESTAMP]/inputs.json
```

---

### STEP 2: EXTRACT BRAND COLORS

**Check if brand color extraction is needed:**
- Attempt to fetch website and extract primary brand colors from CSS/HTML
- If extraction fails: Prompt user to provide hex colors manually
- Store colors in `inputs.json`

**Fallback:** If color extraction fails and user doesn't provide colors, use neutral modern palette:
```json
{
  "primary": "#2563eb",
  "secondary": "#1e40af",
  "accent": "#3b82f6",
  "text": "#1f2937",
  "background": "#ffffff"
}
```

---

### STEP 3: CALL SCRAPER SKILL

**Invoke:** `SKILL_D100_scraper`

**Pass:**
- Website URL
- Additional context (if provided)

**Expected Output:**
- Raw scrape data (Markdown)
- Structured JSON output
- Saved to: `/output/d100_runs/[TIMESTAMP]/scrape_data/`

**Error Handling:**
- If scrape fails: Prompt user to provide Grok DeepSearch JSON manually
- Validate JSON structure before proceeding
- If invalid: Re-prompt or halt

---

### STEP 4: GENERATE SEO KEYWORDS & PAUSE FOR MANUAL DATA

**Action:**
1. Generate 100 BrightLocal keywords using scrape JSON
2. Open SEMrush URL in user's default browser: `https://www.semrush.com/analytics/overview/?searchType=domain&q=[WEBSITE_URL]`
3. Display generated keywords in terminal (copy-ready format)
4. Save keywords to: `/output/d100_runs/[TIMESTAMP]/seo_data/brightlocal_keywords.txt`

**Pause Workflow:**
```
═══════════════════════════════════════════════════════════
WORKFLOW PAUSED - Manual SEO Data Collection Required
═══════════════════════════════════════════════════════════

✓ BrightLocal Keywords Generated (100 keywords)
  Location: /output/d100_runs/[TIMESTAMP]/seo_data/brightlocal_keywords.txt

NEXT STEPS:
1. Run BrightLocal audit using the generated keywords
2. Download BrightLocal audit PDF
3. Download SEMrush keyword export CSV from the opened browser tab
4. Return to Claude Code and type: RESUME D100 [TIMESTAMP]

When ready, attach:
- BrightLocal PDF
- SEMrush CSV

═══════════════════════════════════════════════════════════
```

**Save workflow state to:**
`/output/d100_runs/[TIMESTAMP]/workflow_state.json`

---

### STEP 5: RESUME - SEO AUDIT ANALYSIS

**Trigger:** User types `RESUME D100 [TIMESTAMP]` and attaches files

**Validate attachments:**
- BrightLocal PDF exists
- SEMrush CSV exists
- If missing: Re-prompt

**Invoke:** `SKILL_D100_seo_audit`

**Pass:**
- Scrape JSON
- BrightLocal PDF
- SEMrush CSV

**Expected Output:**
- SEO insights (Markdown)
- Local audit analysis (Markdown)
- Saved to: `/output/d100_runs/[TIMESTAMP]/seo_data/`

---

### STEP 6: PARALLEL ASSET GENERATION

**Launch in parallel:**

1. **App Builder** (`SKILL_D100_app_builder`)
   - Input: Scrape JSON + Brand Colors
   - Output: HTML file → `/output/d100_runs/[TIMESTAMP]/app/health_assessment.html`

2. **Ads Builder** (`SKILL_D100_ads_builder`)
   - Input: Scrape JSON + SEO insights
   - Output: Google Ads copy → `/output/d100_runs/[TIMESTAMP]/ads/google_ads_campaign.md`

3. **Email Builder** (`SKILL_D100_email_builder`)
   - Input: Scrape JSON + Booking URL
   - Output: Email sequence → `/output/d100_runs/[TIMESTAMP]/emails/sequence.md`

**Monitor completion:**
- Wait for all 3 skills to complete
- Validate outputs exist
- If any fail: Report error and allow manual retry

---

### STEP 7: COMPILE FINAL OUTPUT

**Generate summary report:**
```
═══════════════════════════════════════════════════════════
DREAM 100 OUTREACH AUTOMATION - COMPLETE
═══════════════════════════════════════════════════════════

Run ID: [TIMESTAMP]
Website: [URL]
Status: ✓ SUCCESS

OUTPUTS GENERATED:
├── Scrape Data
│   ├── Raw scrape (Markdown)
│   └── Structured JSON
├── SEO Analysis
│   ├── BrightLocal keywords (100)
│   ├── Local audit insights
│   └── SEMrush keyword analysis
├── Health Assessment App
│   └── health_assessment.html (ready to deploy)
├── Google Ads Campaign
│   └── google_ads_campaign.md (3 campaigns + extensions)
└── Email Sequence
    └── sequence.md (3-email automation)

NEXT STEPS:
1. Review outputs in: /output/d100_runs/[TIMESTAMP]/
2. Deploy health assessment app
3. Import Google Ads copy
4. Set up email automation
5. (Future) Send to Gamma API for presentation

═══════════════════════════════════════════════════════════
```

**Save final manifest:**
`/output/d100_runs/[TIMESTAMP]/manifest.json`

---

## ERROR HANDLING

**Critical Errors (HALT):**
- Invalid URL after 3 attempts
- Scrape failure + no manual JSON provided
- Missing critical JSON fields after manual input
- SEO data files not attached after resume

**Recoverable Errors (RETRY):**
- Color extraction failure → prompt manual input
- Single asset generation failure → allow retry
- File write errors → retry with fallback path

**Logging:**
- All errors logged to: `/output/d100_runs/[TIMESTAMP]/error_log.txt`
- Include timestamp, step, error message, user action taken

---

## FILE STRUCTURE

```
/output/d100_runs/[TIMESTAMP]/
├── inputs.json
├── workflow_state.json
├── manifest.json
├── error_log.txt
├── scrape_data/
│   ├── raw_scrape.md
│   └── structured_data.json
├── seo_data/
│   ├── brightlocal_keywords.txt
│   ├── brightlocal_audit.pdf (user-provided)
│   ├── semrush_export.csv (user-provided)
│   ├── local_audit_insights.md
│   └── seo_insights.md
├── app/
│   └── health_assessment.html
├── ads/
│   └── google_ads_campaign.md
└── emails/
    └── sequence.md
```

---

## USAGE

**Initial Run:**
```
User: "Run Dream 100 automation for [website]"
Claude: [Executes SKILL_D100_orchestrator]
```

**Resume After Pause:**
```
User: "RESUME D100 [TIMESTAMP]" + attach PDF/CSV
Claude: [Continues from STEP 5]
```

---

## NOTES FOR FUTURE ENHANCEMENT

- [ ] Add Gamma API integration for auto-presentation generation
- [ ] Add webform interface (host on Vercel/Netlify)
- [ ] Add BrightLocal/SEMrush API integration to remove manual steps
- [ ] Add real-time progress tracking UI
- [ ] Add email ESP integration (e.g., Klaviyo, ConvertKit)
- [ ] Add Google Ads API integration for campaign creation

---

## VERSION HISTORY

**1.0** - Initial release
- 6-step orchestration workflow
- Manual SEO data collection pause/resume
- Parallel asset generation
- Local filesystem outputs
