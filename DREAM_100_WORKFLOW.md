# Dream 100 Automation - Visual Workflow

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DREAM 100 AUTOMATION v1.0                        │
│                  Healthcare Outreach Asset Generator                 │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 1: INPUT VALIDATION                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  USER INPUT ──┬──→ Website URL (required, validated)                │
│               ├──→ Booking URL/Phone (required, validated)          │
│               └──→ Additional Context (optional)                    │
│                                                                      │
│  VALIDATION ───┬──→ URL format check (HTTP/HTTPS)                   │
│                ├──→ Phone number format (E.164 if applicable)       │
│                └──→ Re-prompt if invalid (max 3 attempts)           │
│                                                                      │
│  COLOR EXTRACTION ──→ Attempt auto-extract from site                │
│                    └──→ Fallback: Prompt user OR use defaults      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 2: WEBSITE SCRAPING                                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  SKILL: SKILL_D100_scraper                                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────┐            │
│  │ STEP 1: Perplexity Sonar Deep Scrape              │            │
│  │  • API: OpenRouter (Perplexity Sonar)             │            │
│  │  • Crawl depth: ~50 pages                         │            │
│  │  • Extract: Services, conditions, providers,      │            │
│  │    pricing, patient journey, trust signals        │            │
│  │  • Output: Raw Markdown with source citations     │            │
│  │                                                    │            │
│  │  ERROR HANDLING:                                  │            │
│  │  • If scrape fails → Grok DeepSearch fallback     │            │
│  │  • User provides manual JSON input                │            │
│  └────────────────────────────────────────────────────┘            │
│                           │                                         │
│                           ▼                                         │
│  ┌────────────────────────────────────────────────────┐            │
│  │ STEP 2: JSON Conversion                            │            │
│  │  • API: Claude Opus 4.6 (native Claude Code)      │            │
│  │  • Convert Markdown → Structured JSON schema      │            │
│  │  • Validate: Practice name, services, conditions  │            │
│  │  • Flag: Missing critical fields                  │            │
│  │  • Output: structured_data.json                   │            │
│  └────────────────────────────────────────────────────┘            │
│                                                                      │
│  OUTPUTS:                                                            │
│  ✓ /scrape_data/raw_scrape.md                                      │
│  ✓ /scrape_data/structured_data.json                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 3: SEO KEYWORD GENERATION                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  SKILL: SKILL_D100_seo_audit (Part 1)                               │
│                                                                      │
│  ┌────────────────────────────────────────────────────┐            │
│  │ Generate 100 BrightLocal Keywords                  │            │
│  │  • API: OpenAI GPT-4o                              │            │
│  │  • Input: Services, conditions, primary city       │            │
│  │  • Generate: 15 keyword categories                 │            │
│  │  • Output: Plain text (copy-ready)                 │            │
│  └────────────────────────────────────────────────────┘            │
│                           │                                         │
│                           ▼                                         │
│  ┌────────────────────────────────────────────────────┐            │
│  │ Open SEMrush in Browser                            │            │
│  │  • Auto-open: semrush.com/analytics/...           │            │
│  │  • User exports keyword CSV                        │            │
│  └────────────────────────────────────────────────────┘            │
│                                                                      │
│  OUTPUTS:                                                            │
│  ✓ /seo_data/brightlocal_keywords.txt (100 keywords)               │
│  ✓ SEMrush browser tab opened                                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ ⏸️  WORKFLOW PAUSED - MANUAL STEP REQUIRED                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  USER TASKS (7 minutes):                                            │
│  1. Copy keywords from terminal                                     │
│  2. Run BrightLocal audit → Download PDF                            │
│  3. Export SEMrush data → Download CSV                              │
│  4. Return to Claude Code                                           │
│  5. Type: RESUME D100 [TIMESTAMP]                                   │
│  6. Attach: BrightLocal PDF + SEMrush CSV                           │
│                                                                      │
│  STATE SAVED:                                                        │
│  • workflow_state.json (contains pause point, context)              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                        USER: RESUME D100 [TIMESTAMP]
                        ATTACH: PDF + CSV
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 4: SEO ANALYSIS                                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  SKILL: SKILL_D100_seo_audit (Part 2)                               │
│                                                                      │
│  ┌────────────────────────────────────────────────────┐            │
│  │ Analyze BrightLocal PDF                            │            │
│  │  • API: ChatGPT-4o (with file upload)              │            │
│  │  • Extract: 3 critical revenue-blocking issues     │            │
│  │  • Format: Plain-English, doctor-friendly          │            │
│  │  • Output: local_audit_insights.md                 │            │
│  └────────────────────────────────────────────────────┘            │
│                           │                                         │
│                           ▼                                         │
│  ┌────────────────────────────────────────────────────┐            │
│  │ Analyze SEMrush CSV                                │            │
│  │  • API: OpenAI o1 (reasoning model)                │            │
│  │  • Parse: Keywords, positions, volumes             │            │
│  │  • Analyze: Trends, opportunities, AI visibility   │            │
│  │  • Format: Executive narrative                     │            │
│  │  • Output: seo_insights.md                         │            │
│  └────────────────────────────────────────────────────┘            │
│                           │                                         │
│                           ▼                                         │
│  ┌────────────────────────────────────────────────────┐            │
│  │ Compile Master Report                              │            │
│  │  • Combine: Keywords + Audit + Insights            │            │
│  │  • Add: Executive summary, action plan             │            │
│  │  • Output: seo_master_report.md                    │            │
│  └────────────────────────────────────────────────────┘            │
│                                                                      │
│  OUTPUTS:                                                            │
│  ✓ /seo_data/local_audit_insights.md                               │
│  ✓ /seo_data/seo_insights.md                                       │
│  ✓ /seo_data/seo_master_report.md                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 5: PARALLEL ASSET GENERATION                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌────────────┐│
│  │ SKILL:               │  │ SKILL:               │  │ SKILL:     ││
│  │ D100_app_builder     │  │ D100_ads_builder     │  │ D100_email ││
│  │                      │  │                      │  │ _builder   ││
│  ├──────────────────────┤  ├──────────────────────┤  ├────────────┤│
│  │ Health Assessment App│  │ Google Ads Campaigns │  │ Email Seq  ││
│  │                      │  │                      │  │            ││
│  │ INPUT:               │  │ INPUT:               │  │ INPUT:     ││
│  │ • Scrape JSON        │  │ • Scrape JSON        │  │ • Scrape   ││
│  │ • Brand colors       │  │ • SEO insights       │  │   JSON     ││
│  │ • Booking URL        │  │                      │  │ • Booking  ││
│  │                      │  │ API:                 │  │   URL      ││
│  │ API:                 │  │ • Gemini 2.0 Flash   │  │            ││
│  │ • Claude Opus 4.6    │  │   (OpenRouter)       │  │ API:       ││
│  │   (native)           │  │                      │  │ • GPT-4o   ││
│  │                      │  │ GENERATES:           │  │   (OpenRT) ││
│  │ ASKS USER:           │  │ • 3 campaigns        │  │            ││
│  │ • Assessment depth   │  │ • 15 headlines       │  │ GENERATES: ││
│  │ • Required fields    │  │ • 6 descriptions     │  │ • Email 1  ││
│  │ • Redirect method    │  │ • 4 sitelinks        │  │   (Value)  ││
│  │ • End behavior       │  │ • 6 callouts         │  │ • Email 2  ││
│  │ • Legal text         │  │ • 5 keywords         │  │   (Mech)   ││
│  │                      │  │                      │  │ • Email 3  ││
│  │ GENERATES:           │  │ OUTPUTS:             │  │   (Proof)  ││
│  │ • Single HTML file   │  │ • Campaign MD        │  │            ││
│  │ • WCAG-compliant     │  │ • Import CSVs        │  │ OUTPUTS:   ││
│  │ • Mobile-responsive  │  │ • Setup guide        │  │ • MD seq   ││
│  │ • Brand-aligned      │  │                      │  │ • Plain    ││
│  │ • Booking redirect   │  │                      │  │   text     ││
│  │                      │  │                      │  │ • HTML     ││
│  │ VALIDATION:          │  │ VALIDATION:          │  │ • ESP CSVs ││
│  │ • HTML5 valid        │  │ • Char limits        │  │ • Setup    ││
│  │ • No ext deps        │  │ • 3 campaigns        │  │   guide    ││
│  │ • Brand colors OK    │  │ • All assets         │  │            ││
│  │                      │  │                      │  │ CHECKS:    ││
│  │ OUTPUT:              │  │                      │  │ • No diag  ││
│  │ ✓ health_assessment  │  │                      │  │ • Disclai  ││
│  │   .html              │  │                      │  │   mers     ││
│  │ ✓ README.md          │  │                      │  │ • Prof     ││
│  │ ✓ config.json        │  │                      │  │   tone     ││
│  └──────────────────────┘  └──────────────────────┘  └────────────┘│
│           │                         │                       │       │
│           └─────────────────────────┴───────────────────────┘       │
│                                     │                               │
│                         ALL SKILLS COMPLETE                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 6: OUTPUT COMPILATION                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ORCHESTRATOR: Compiles all outputs                                 │
│                                                                      │
│  ┌────────────────────────────────────────────────────┐            │
│  │ Generate Final Manifest                            │            │
│  │  • List all generated files                        │            │
│  │  • Include metadata (timestamps, sizes)            │            │
│  │  • Create summary report                           │            │
│  │  • Output: manifest.json                           │            │
│  └────────────────────────────────────────────────────┘            │
│                           │                                         │
│                           ▼                                         │
│  ┌────────────────────────────────────────────────────┐            │
│  │ Display Success Message                            │            │
│  │  • Summary of generated assets                     │            │
│  │  • File locations                                  │            │
│  │  • Next steps guide                                │            │
│  └────────────────────────────────────────────────────┘            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ FINAL OUTPUT STRUCTURE                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  /output/d100_runs/[TIMESTAMP]/                                     │
│  │                                                                   │
│  ├── inputs.json                    (User inputs)                   │
│  ├── workflow_state.json            (Execution state)               │
│  ├── manifest.json                  (Output manifest)               │
│  ├── error_log.txt                  (Errors if any)                 │
│  │                                                                   │
│  ├── scrape_data/                                                   │
│  │   ├── raw_scrape.md              (Perplexity output)             │
│  │   └── structured_data.json       (Structured intelligence)       │
│  │                                                                   │
│  ├── seo_data/                                                      │
│  │   ├── brightlocal_keywords.txt   (100 keywords)                  │
│  │   ├── brightlocal_audit.pdf      (User uploaded)                 │
│  │   ├── semrush_export.csv         (User uploaded)                 │
│  │   ├── local_audit_insights.md    (3 critical issues)             │
│  │   ├── seo_insights.md            (SEMrush analysis)              │
│  │   └── seo_master_report.md       (Combined report)               │
│  │                                                                   │
│  ├── app/                                                           │
│  │   ├── health_assessment.html     (Single-file app)               │
│  │   ├── README.md                  (Deployment guide)              │
│  │   └── config.json                (App configuration)             │
│  │                                                                   │
│  ├── ads/                                                           │
│  │   ├── google_ads_campaign.md     (Campaign copy)                 │
│  │   ├── google_ads_import.csv      (Ads Editor import)             │
│  │   ├── extensions.csv             (Extensions import)             │
│  │   ├── keywords.csv               (Keywords import)               │
│  │   └── SETUP_GUIDE.md             (Setup instructions)            │
│  │                                                                   │
│  └── emails/                                                        │
│      ├── sequence.md                (Master sequence)               │
│      ├── plain_text.txt             (Plain text versions)           │
│      ├── html_version.html          (HTML preview)                  │
│      ├── esp_imports/                                               │
│      │   ├── klaviyo_import.csv     (Klaviyo ready)                 │
│      │   └── convertkit_import.json (ConvertKit ready)              │
│      └── SETUP_GUIDE.md             (ESP setup guide)               │
│                                                                      │
│  TOTAL FILES: 15-20                                                 │
│  TOTAL SIZE: ~5-10 MB                                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## API Call Sequence

```
TIME  SKILL                API                  PURPOSE
─────────────────────────────────────────────────────────────
00:00 orchestrator         -                    Validate inputs
00:01 scraper              Perplexity Sonar     Website scrape
02:30 scraper              Claude Opus 4.6      JSON conversion
03:00 seo_audit            OpenAI GPT-4o        Generate keywords
03:30 [PAUSE]              -                    User uploads files
─────────────────────────────────────────────────────────────
[USER RESUMES AFTER ~7 MIN]
─────────────────────────────────────────────────────────────
10:00 seo_audit            ChatGPT-4o           BrightLocal analysis
11:00 seo_audit            OpenAI o1            SEMrush analysis
12:00 ┌ app_builder        Claude Opus 4.6      Health app
      ├ ads_builder        Gemini 2.0 Flash     Google Ads
      └ email_builder      GPT-4o               Email sequence
      │                    (PARALLEL)
      └─ All complete at ~15:00
15:00 orchestrator         -                    Compile outputs
─────────────────────────────────────────────────────────────
TOTAL ACTIVE TIME: ~15 minutes
TOTAL MANUAL TIME: ~7 minutes (SEO data collection)
TOTAL ELAPSED TIME: ~22 minutes
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────┐
│ ERROR DETECTED                          │
└─────────────────────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │ ERROR TYPE?   │
         └───────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌───────┐  ┌──────────┐  ┌─────────┐
│CRITICAL│  │RECOVERABLE│  │WARNING │
└───────┘  └──────────┘  └─────────┘
    │            │            │
    ▼            ▼            ▼
  HALT      RETRY (3x)     LOG &
    │            │         CONTINUE
    │            │            │
    ▼            ▼            ▼
DISPLAY     SUCCESS?      DISPLAY
ERROR       YES │ NO      WARNING
MESSAGE        │  │          │
    │          ▼  ▼          │
    │       CONTINUE  HALT   │
    │          │      │      │
    └──────────┴──────┴──────┘
                 │
                 ▼
         ┌───────────────┐
         │ LOG TO FILE   │
         │ error_log.txt │
         └───────────────┘
```

---

## Data Flow Diagram

```
┌─────────────┐
│  WEBSITE    │
│   (Live)    │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Perplexity Sonar   │  ──→  Raw Markdown
│  Deep Crawl         │       (10+ sections,
└──────┬──────────────┘        citations)
       │
       ▼
┌─────────────────────┐
│  Claude Opus 4.6    │  ──→  Structured JSON
│  JSON Conversion    │       (Practice intel,
└──────┬──────────────┘        services, etc.)
       │
       ├──────────────────────────┬──────────────────┐
       │                          │                  │
       ▼                          ▼                  ▼
┌──────────────┐      ┌────────────────┐  ┌─────────────────┐
│ GPT-4o       │      │ Gemini 2.0     │  │ GPT-4o          │
│ Keywords     │      │ Google Ads     │  │ Email Sequence  │
└──────┬───────┘      └────────┬───────┘  └────────┬────────┘
       │                       │                   │
       ▼                       ▼                   ▼
┌──────────────┐      ┌────────────────┐  ┌─────────────────┐
│ BrightLocal  │      │ 3 Campaigns    │  │ 3-Email Flow    │
│ 100 Keywords │      │ + Extensions   │  │ + ESP Imports   │
└──────┬───────┘      └────────────────┘  └─────────────────┘
       │
       ▼
┌─────────────────────┐
│  [USER UPLOADS]     │
│  BrightLocal PDF    │
│  SEMrush CSV        │
└──────┬──────────────┘
       │
       ├──────────────────┐
       │                  │
       ▼                  ▼
┌──────────────┐  ┌────────────────┐
│ ChatGPT-4o   │  │ OpenAI o1      │
│ Local Audit  │  │ SEO Insights   │
└──────┬───────┘  └────────┬───────┘
       │                   │
       └─────────┬─────────┘
                 │
                 ▼
       ┌──────────────────┐
       │  SEO Master      │
       │  Report          │
       └──────────────────┘

PARALLEL BRANCH (from JSON):
       │
       ▼
┌─────────────────────┐
│  Claude Opus 4.6    │  ──→  Health Assessment App
│  App Builder        │       (Single HTML file)
└─────────────────────┘
```

---

## Cost Breakdown Per Run

```
API CALL                    TOKENS    COST      PROVIDER
─────────────────────────────────────────────────────────────
Perplexity Sonar (scrape)   8,000    $0.08     OpenRouter
Claude Opus (JSON)         10,000    $0.15     Claude Code
GPT-4o (keywords)           4,000    $0.02     OpenAI Direct
ChatGPT-4o (audit)          3,000    $0.02     OpenAI Direct
o1 (insights)               5,000    $0.30     OpenAI Direct
Claude Opus (app)           8,000    $0.12     Claude Code
Gemini 2.0 Flash (ads)      6,000    FREE      OpenRouter
GPT-4o (emails)             4,000    $0.02     OpenRouter
─────────────────────────────────────────────────────────────
TOTAL                      48,000    $0.71
─────────────────────────────────────────────────────────────

TIME SAVED vs MANUAL:       12 hours
FREELANCER COST EQUIVALENT: $500-1000
ROI:                        700-1400x
```

---

This workflow represents the complete **Dream 100 Automation v1.0** system.
