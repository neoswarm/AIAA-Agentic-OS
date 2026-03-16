# Dream 100 Outreach Automation 1.0

## Overview

The Dream 100 Outreach Automation is a modular, AI-powered system that transforms a healthcare practice website into a complete personalized outreach campaign package including:

- **Website Intelligence Extraction** - Deep scrape + structured JSON
- **SEO Analysis** - BrightLocal keywords + local audit + SEMrush insights
- **Health Assessment App** - Premium, brand-aligned, single-file HTML
- **Google Ads Campaigns** - 3 campaigns + extensions + keywords
- **Email Nurture Sequence** - 3-email automation ready for ESP import

---

## Architecture

### Modular Skill System (6 Skills)

```
SKILL_D100_orchestrator.md
├── SKILL_D100_scraper.md (Website → JSON)
├── SKILL_D100_seo_audit.md (Keywords + Audit + Insights)
├── SKILL_D100_app_builder.md (Health Assessment HTML)
├── SKILL_D100_ads_builder.md (Google Ads Campaigns)
└── SKILL_D100_email_builder.md (Email Sequence)
```

### Execution Flow

```
1. USER INPUT VALIDATION
   ↓
2. WEBSITE SCRAPING (Perplexity Sonar)
   ↓
3. JSON CONVERSION (Claude Opus 4.6)
   ↓
4. SEO KEYWORD GENERATION (OpenAI GPT-4o)
   ↓
5. [PAUSE - USER UPLOADS SEO DATA]
   ↓
6. SEO AUDIT ANALYSIS (ChatGPT + OpenAI o1)
   ↓
7. PARALLEL ASSET GENERATION
   ├── Health App (Claude Opus 4.6)
   ├── Google Ads (Gemini 2.0 Flash)
   └── Email Sequence (GPT-4o)
   ↓
8. OUTPUT COMPILATION
```

---

## Prerequisites

### 1. API Keys Required

Create `.env` file in `/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/`:

```bash
# OpenRouter (Perplexity + Gemini)
OPENROUTER_API_KEY=sk-or-v1-xxxxx

# OpenAI (GPT-4o, o1, ChatGPT)
OPENAI_API_KEY=sk-xxxxx

# Optional: Direct Anthropic (if not using Claude Code's native Claude)
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 2. Manual Tools Access

- **SEMrush** - Free or paid account for keyword export
- **BrightLocal** - For local search audit (free trial available)

### 3. System Requirements

- Claude Code with Max subscription
- Internet connection
- ~500MB free disk space per run

---

## Usage

### Quick Start

```bash
# In Claude Code, run:
"Run Dream 100 automation for [WEBSITE_URL]"
```

### Step-by-Step Execution

**Step 1: Initiate**
```
User: "Run Dream 100 automation for https://example-clinic.com"
```

**Step 2: Provide Required Inputs**
The orchestrator will prompt for:
- Website URL (validated)
- Booking URL or Phone Number (validated)
- Optional: Additional context

**Step 3: Automatic Scraping**
- Perplexity Sonar scrapes website
- Claude Opus converts to structured JSON
- Brand colors extracted (or you provide manually)

**Step 4: SEO Data Collection (Manual Pause)**
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

**Step 5: Resume & Complete**
```
User: "RESUME D100 [TIMESTAMP]"
[Attach BrightLocal PDF and SEMrush CSV]
```

System will:
- Analyze SEO data
- Generate all assets in parallel
- Compile final outputs

**Step 6: Review Outputs**
```
/output/d100_runs/[TIMESTAMP]/
├── inputs.json
├── scrape_data/
│   ├── raw_scrape.md
│   └── structured_data.json
├── seo_data/
│   ├── brightlocal_keywords.txt
│   ├── local_audit_insights.md
│   ├── seo_insights.md
│   └── seo_master_report.md
├── app/
│   ├── health_assessment.html
│   ├── README.md
│   └── config.json
├── ads/
│   ├── google_ads_campaign.md
│   ├── google_ads_import.csv
│   ├── extensions.csv
│   ├── keywords.csv
│   └── SETUP_GUIDE.md
└── emails/
    ├── sequence.md
    ├── plain_text.txt
    ├── html_version.html
    ├── esp_imports/
    │   ├── klaviyo_import.csv
    │   └── convertkit_import.json
    └── SETUP_GUIDE.md
```

---

## Skills Reference

### SKILL_D100_orchestrator
**Purpose:** Master workflow controller
**Dependencies:** All other D100 skills
**Key Functions:**
- Input validation
- Workflow state management
- Pause/resume logic
- Output compilation

### SKILL_D100_scraper
**Purpose:** Website data extraction
**API:** OpenRouter (Perplexity Sonar), Claude Sonnet 3.7
**Output:** Raw Markdown + Structured JSON
**Fallback:** Grok DeepSearch manual input

### SKILL_D100_seo_audit
**Purpose:** SEO intelligence generation
**API:** OpenAI GPT-4o (Direct), OpenAI o1 (Direct)
**Output:** Keywords, audit insights, master report
**Manual Steps:** BrightLocal audit, SEMrush export

### SKILL_D100_app_builder
**Purpose:** Health assessment app generation
**API:** Claude Sonnet 3.7 (native)
**Output:** Single-file HTML app
**Features:** WCAG-compliant, mobile-first, branded

### SKILL_D100_ads_builder
**Purpose:** Google Ads campaign generation
**API:** OpenRouter (Gemini 3.0 Pro)
**Output:** 3 campaigns + extensions + keywords
**Formats:** Markdown, CSV (Google Ads Editor ready)

### SKILL_D100_email_builder
**Purpose:** Email sequence generation
**API:** OpenAI GPT-4o (Direct)
**Output:** 3-email sequence, multiple formats
**ESP Support:** Klaviyo, ConvertKit, ActiveCampaign, generic

---

## Output Formats

### 1. Website Intelligence (JSON)
- Practice identification
- Services & conditions
- Providers
- Patient journey
- Pricing & insurance
- Trust signals
- SEO intel

### 2. SEO Data (Markdown + CSV)
- 100 BrightLocal keywords (plain text)
- Local audit insights (Markdown)
- SEMrush analysis (Markdown)
- Master report (Markdown)

### 3. Health App (HTML)
- Single-file HTML/CSS/JS
- No external dependencies
- Brand-aligned design
- Booking redirect with payload

### 4. Google Ads (Markdown + CSV)
- Campaign copy (Markdown)
- Import CSVs (Ads Editor ready)
- Setup guide (Markdown)

### 5. Email Sequence (Markdown + HTML + CSV/JSON)
- Master copy (Markdown)
- Plain text versions
- HTML preview
- ESP import files
- Setup guide

---

## API Cost Estimates (Per Run)

| Service | Model | Est. Tokens | Est. Cost |
|---------|-------|-------------|-----------|
| Website Scrape | Perplexity Sonar | 8,000 | $0.08 |
| JSON Conversion | Claude Sonnet 3.7 | 10,000 | $0.08 |
| BL Keywords | GPT-4o (Direct) | 4,000 | $0.02 |
| Local Audit | o1 (Direct) | 3,000 | $0.30 |
| SEO Insights | o1 (Direct) | 5,000 | $0.30 |
| Health App | Claude Sonnet 3.7 | 8,000 | $0.06 |
| Google Ads | Gemini 3.0 Pro | 6,000 | $0.03 |
| Email Sequence | GPT-4o (Direct) | 4,000 | $0.02 |
| **TOTAL** | | **~48,000** | **~$0.89** |

*Costs are estimates based on OpenRouter/OpenAI pricing as of Feb 2025. Uses direct OpenAI API for GPT-4o and o1, OpenRouter for Perplexity and Gemini.*

---

## Error Handling

### Common Issues & Solutions

**1. "Scrape failed"**
- **Cause:** Website blocking, Cloudflare, paywall
- **Solution:** Use Grok DeepSearch fallback (manual JSON input)

**2. "Critical field missing: X"**
- **Cause:** Website lacks required data
- **Solution:** System prompts for manual input

**3. "API key not found"**
- **Cause:** `.env` file missing or incorrect
- **Solution:** Create/update `.env` with valid keys

**4. "SEO data files not found"**
- **Cause:** User hasn't uploaded BrightLocal/SEMrush files
- **Solution:** Follow pause screen instructions, attach files

**5. "Invalid booking URL"**
- **Cause:** Malformed URL or phone format
- **Solution:** System re-prompts until valid

**6. "Character limit exceeded (Google Ads)"**
- **Cause:** Generated headline/description too long
- **Solution:** Auto-truncated with warning

---

## Customization

### Modify Assessment Depth
Edit `SKILL_D100_app_builder.md`:
```markdown
Line 75: Assessment depth options
- Quick (5-7 min, ~15 questions)
- Standard (10-12 min, ~25 questions) ← Default
- Comprehensive (15-20 min, ~40 questions)
```

### Change Email Timing
Edit `SKILL_D100_email_builder.md`:
```markdown
Line 320: Timing configuration
- Email 1: Immediately (default)
- Email 2: 2 days (change to desired delay)
- Email 3: 4 days (change to desired delay)
```

### Add More Campaigns
Edit `SKILL_D100_ads_builder.md`:
```markdown
Line 150: Campaign structure
Add Campaign 4, Campaign 5, etc.
```

### Adjust Brand Colors Fallback
Edit `SKILL_D100_orchestrator.md`:
```markdown
Line 65: Fallback color palette
{
  "primary": "#2563eb",  ← Change
  "secondary": "#1e40af",
  ...
}
```

---

## Troubleshooting

### Debug Mode
Add to any skill:
```bash
set -x  # Enable verbose bash output
```

### View Logs
```bash
cat /output/d100_runs/[TIMESTAMP]/error_log.txt
```

### Re-run Individual Skills
```bash
# Example: Re-run just the scraper
"Run SKILL_D100_scraper for https://example.com"
```

### Validate JSON Output
```bash
jq . /output/d100_runs/[TIMESTAMP]/scrape_data/structured_data.json
```

---

## Future Enhancements (Roadmap)

- [ ] Gamma API integration (auto-presentation generation)
- [ ] BrightLocal API integration (remove manual step)
- [ ] SEMrush API integration (remove manual step)
- [ ] Web interface for input collection
- [ ] Real-time progress tracking UI
- [ ] Email ESP API integrations (Klaviyo, ConvertKit)
- [ ] Google Ads API integration (auto-campaign creation)
- [ ] Multi-language support
- [ ] A/B test variant generation
- [ ] Social media ad variant generation (Meta, LinkedIn)

---

## Contributing

This is part of the AIAA Agentic OS. To modify:

1. Edit individual skill files in `/skills/SKILL_D100_*.md`
2. Test with sample data
3. Update this README with changes
4. Document any new API dependencies

---

## License

Part of AIAA-Agentic-OS - All rights reserved

---

## Support

**Documentation:** This file
**Issues:** Check `/output/d100_runs/[TIMESTAMP]/error_log.txt`
**Version:** 1.0
**Last Updated:** 2025-02-10

---

## Quick Command Reference

```bash
# Start automation
"Run Dream 100 automation for [URL]"

# Resume after SEO data collection
"RESUME D100 [TIMESTAMP]"

# View outputs
"Show me the D100 outputs for [TIMESTAMP]"

# Re-run specific skill
"Run SKILL_D100_scraper for [URL]"
"Run SKILL_D100_app_builder with [JSON_PATH]"
```

---

**Generated by AIAA-Agentic-OS**
**Dream 100 Outreach Automation v1.0**
