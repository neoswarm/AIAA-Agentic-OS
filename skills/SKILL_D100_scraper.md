# SKILL: Dream 100 Website Scraper

## METADATA
- **Skill Name**: Dream 100 Website Scraper
- **Version**: 2.0
- **Category**: Data Collection
- **API Requirements**: Firecrawl CLI (primary), Puppeteer (fallback), OpenRouter (Perplexity Sonar - legacy fallback)
- **Parent Skill**: SKILL_D100_orchestrator

---

## MISSION
Scrape healthcare practice websites using Perplexity Sonar via OpenRouter, extract structured intelligence for Dream 100 outreach, and generate automation-ready JSON output.

---

## INPUT REQUIREMENTS

**Required:**
- `website_url` (string): Valid HTTP/HTTPS URL
- `output_directory` (string): Path to save outputs

**Optional:**
- `additional_context` (string): User-provided context about the practice

---

## API CONFIGURATION

**Provider:** OpenRouter
**Model:** `perplexity/sonar`
**Endpoint:** `https://openrouter.ai/api/v1/chat/completions`

**Authentication:**
- Read API key from: `/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/.env`
- Key name: `OPENROUTER_API_KEY`

**Request Headers:**
```json
{
  "Authorization": "Bearer $OPENROUTER_API_KEY",
  "Content-Type": "application/json",
  "HTTP-Referer": "https://aiaa-agentic-os.local",
  "X-Title": "AIAA Dream 100 Scraper"
}
```

---

## EXECUTION LOGIC

### STEP 1: VALIDATE ENVIRONMENT

**Check .env file exists:**
```bash
if [ ! -f "/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/.env" ]; then
  echo "ERROR: .env file not found"
  echo "Create .env with: OPENROUTER_API_KEY=your_key_here"
  exit 1
fi
```

**Load API key:**
```bash
source "/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/.env"
if [ -z "$OPENROUTER_API_KEY" ]; then
  echo "ERROR: OPENROUTER_API_KEY not set in .env"
  exit 1
fi
```

---

### STEP 2: INITIAL SCRAPE (PERPLEXITY SONAR)

**Prompt to send to Perplexity:**

```
You are a healthcare practice intelligence analyst specializing in extracting structured, source-grounded website data for marketing automation, Dream 100 outreach, ICP/RAG building, SEO, and paid media.

MISSION
Given a healthcare practice website, crawl it like a human would (live pages only) and extract ONLY what is explicitly stated on the site. Your output must be high-coverage, deeply sourced, and automation-ready.

NON-NEGOTIABLE RULES
1) Use the LIVE website (no cached snippets, no memory, no assumptions).
2) Extract ONLY what you can cite from the site. If missing/unclear: write "NOT FOUND ON SITE".
3) Go deep: don't stop at nav links. Follow in-page links, footer links, "Learn more" CTAs, and related service/condition/provider subpages.
4) Capture exact wording for claims that affect compliance (outcomes, guarantees, "best", "top", "cure", etc.).
5) Prefer canonical pages over duplicates; note duplicates if content differs.
6) If the site has multiple locations/providers, extract ALL.
7) If content is in PDFs, patient forms, or embedded widgets, attempt to open them; if inaccessible, mark as "NOT FOUND ON SITE (INACCESSIBLE)".
8) Always include SOURCE URLs for each extracted item (page-level citations at minimum; section-level when possible).
9) Visit AT LEAST these (if they exist): Homepage, Services, Conditions We Treat, Team/Providers, About. Then expand.

INPUT
Website URL: {website_url}
Optional Focus: {additional_context}
Output Mode: STANDARD
Max pages to open: 50

CRAWL PLAN (EXECUTE SILENTLY)
Step A — Identify Core Pages
- Homepage + top nav + footer nav
- Search for pages matching: services, treatments, procedures, conditions, symptoms, providers, physicians, team, about, mission, process, how it works, new patients, forms, resources, blog, insurance, pricing, patient portal, contact, locations.

Step B — Deep Expansion (Mandatory)
- Services: open each individual service/treatment subpage
- Conditions: open each condition subpage (if present)
- Team: open each provider bio page
- About: open any mission/story/values pages
- New Patients: open intake/process/forms/FAQ pages
- Locations: open each location page
- If blog/resources exist: open the 3 most recent + 3 most linked to pages that mention services/conditions
- If there are specialty programs/packages/memberships: open each

Step C — Validation Pass
- Cross-check consistency: names, phone, addresses, hours, accepted insurance, "we treat" lists
- Note contradictions (e.g., different phone numbers per page, varying condition lists)

OUTPUT FORMAT (STRICT — DO NOT ADD EXTRA SECTIONS)
Return Markdown exactly in this structure. Use bullets, short lines, and include SOURCE URLs.

## 0. PAGES VISITED (REQUIRED)
- Homepage: [URL]
- Services hub: [URL or NOT FOUND ON SITE]
- Conditions hub: [URL or NOT FOUND ON SITE]
- Team hub: [URL or NOT FOUND ON SITE]
- About: [URL or NOT FOUND ON SITE]
- Additional pages opened (list all):
  - [URL]
  - [URL]
- Crawl depth notes (what you could/couldn't access): [TEXT]

## 1. PRACTICE IDENTIFICATION
- Legal business name (exact):
- Brand name (if different):
- Tagline/headline (verbatim):
- Primary specialty positioning (verbatim phrase if possible):
- Practice type (as stated: e.g., dermatology clinic, PT, functional medicine, dental, etc.):
- Ownership/affiliation (hospital system, franchise, group, independent) (as stated):
- Primary location (full address):
- Additional locations (full addresses):
- Service areas (cities/regions mentioned):
- Phone number(s):
- Email(s):
- Contact form URL:
- Online booking URL (if any):
- Patient portal URL (if any):
- Hours (per location, if listed):
- Accessibility notes (wheelchair, parking, etc. if stated):
SOURCES:
- [URL(s)]

## 2. TEAM / PROVIDER DIRECTORY (ALL PROVIDERS)
For EACH provider/team member with a bio page or listing, output one block:

### Provider: [FULL NAME]
- Role/title (verbatim):
- Credentials (MD/DO/DC/NP/PT/etc):
- Specialty/focus areas (verbatim or near-verbatim):
- Conditions treated (only if explicitly tied to this provider):
- Services performed (only if explicitly tied to this provider):
- Education/training (schools, residencies, fellowships, if stated):
- Certifications/boards (verbatim):
- Memberships/associations (verbatim):
- Languages spoken (if stated):
- Years of experience (if stated):
- Publications/talks/media (if stated):
- Headshot/photo: YES/NO (and image page URL if possible):
- Bio summary (2–3 sentences, stitched only from site facts):
SOURCES:
- [URL]

## 3. SERVICES & TREATMENTS (EXACT, DE-DUPED LIST)
Output as a table. Include every service/treatment/program explicitly offered.

| Service/Treatment Name (verbatim) | Category (e.g., service, procedure, program, therapy) | Who it's for (verbatim snippet if present) | Deliverables/what happens (short) | CTA (book/call/etc.) | Source URL |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Then:
- "Signature offers" / named programs/packages (verbatim):
- Pediatric vs adult offerings (if stated):
- Telehealth/virtual care (if stated): YES/NO + details
SOURCES:
- [URL(s)]

## 4. CONDITIONS WE TREAT (VERBATIM MASTER LIST)
- Conditions/symptoms listed anywhere (bullets, deduped by exact phrasing):
  - [Condition]
  - [Condition]
- If the site uses categories (e.g., "Back Pain", "Sports Injuries"), keep hierarchy:
  - Category:
    - Condition:
SOURCES:
- [URL(s)]

## 5. IDEAL PATIENT + EXCLUSION CRITERIA (ONLY FROM SITE)
- Who they explicitly serve (verbatim phrases):
- Demographics mentioned (age, gender, life stage):
- Patient situations (athletes, chronic pain, post-op, etc.):
- "Not a fit" / exclusions / contraindications (verbatim):
- Referral requirements (PCP referral, imaging required, etc.):
SOURCES:
- [URL(s)]

## 6. CLINICAL APPROACH, METHODS, & DIFFERENTIATORS
- "How we're different" / value props (bullets; include verbatim snippets where possible):
- Treatment philosophy (verbatim snippets):
- Diagnostic methods mentioned (imaging, physical exams, screenings):
- Tests/labs offered or ordered (verbatim):
- Technology/equipment highlighted (brand/model if stated):
- Modalities/therapies (manual therapy, injections, acupuncture, etc.):
- Evidence/claims language (NOTE any strong claims verbatim):
SOURCES:
- [URL(s)]

## 7. PATIENT JOURNEY & INTAKE PROCESS
- First step CTA (call/book/form) (verbatim):
- New patient steps (numbered if possible):
  1)
  2)
- Discovery call offered: YES/NO + how it's described:
- Intake forms mentioned: YES/NO + links:
- Consult length/time expectations (if stated):
- Follow-up cadence/timeline (if stated):
- Membership/care plans/subscriptions: YES/NO + details
SOURCES:
- [URL(s)]

## 8. PRICING, INSURANCE, & FINANCIAL POLICIES
- Pricing transparency: TRANSPARENT / PARTIAL / NONE
- Any prices or ranges (verbatim + context):
- Insurance accepted (verbatim; list carriers if stated):
- Medicare/Medicaid acceptance (if stated):
- Self-pay/cash pricing mentioned: YES/NO + details
- Superbills/out-of-network guidance: YES/NO + details
- Payment plans/financing (CareCredit etc.) (if stated):
- HSA/FSA mention: YES/NO + details
SOURCES:
- [URL(s)]

## 9. TRUST, CREDIBILITY, & SOCIAL PROOF
- Reviews/testimonials on-site: YES/NO
  - If YES: where (page URL) + summary of themes (no inventing)
- Case studies / before-after galleries: YES/NO + URLs
- Awards/badges/press mentions (verbatim):
- Associations/affiliations (verbatim):
- Clinical research/evidence citations on-site: YES/NO + URLs
- Compliance notes:
  - Any "results may vary" disclaimers: YES/NO + verbatim snippet
SOURCES:
- [URL(s)]

## 10. SEO + ADS INTELLIGENCE (SITE-BASED ONLY)
- Primary service keywords implied by headings (list H1/H2 patterns from services pages):
- Location modifiers used (cities/areas mentioned in headings/meta copy):
- Core conversion CTAs used (exact button/link text):
- Lead magnets offered (guides, quizzes, downloads): YES/NO + URLs
- Forms present (contact, booking, newsletter, etc.) + URLs:
- Tracking/tech stack hints visible on-site (only if explicitly visible in page/footer text, e.g., "Powered by"):
SOURCES:
- [URL(s)]
```

**API Call:**
```bash
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -H "HTTP-Referer: https://aiaa-agentic-os.local" \
  -H "X-Title: AIAA Dream 100 Scraper" \
  -d '{
    "model": "perplexity/sonar",
    "messages": [
      {
        "role": "user",
        "content": "[FULL PROMPT ABOVE WITH VARIABLES REPLACED]"
      }
    ],
    "temperature": 0.3,
    "max_tokens": 8000
  }'
```

**Save Response:**
- Raw Markdown → `{output_directory}/scrape_data/raw_scrape.md`

**Error Handling:**
- If API call fails (network, auth, rate limit): Display error and prompt for Grok DeepSearch JSON
- If response is incomplete: Retry once, then prompt for manual input
- If rate limited: Wait and retry with exponential backoff (max 3 attempts)

---

### STEP 3: CONVERT TO STRUCTURED JSON

**Use:** Claude Sonnet 3.7 (native Claude Code model)

**Prompt:**

```
You are a healthcare practice intelligence crawler designed for AUTOMATION-FIRST pipelines.

ABSOLUTE OUTPUT ENFORCEMENT (NON-NEGOTIABLE)
- You MUST output a SINGLE JSON object.
- You MUST output JSON ONLY (no Markdown, no prose, no explanations).
- Your JSON MUST EXACTLY match the schema below:
  - Same keys
  - Same nesting
  - Same casing
  - Same data types
  - Same arrays (present even if empty)
- You are NOT allowed to:
  - Rename fields
  - Add fields
  - Remove fields
  - Reorder fields
- If data is missing, unclear, inaccessible, or contradictory:
  - Set the field value(s) to null
  - Log the issue in the `missing[]` array
- Every extracted field MUST include:
  - value
  - verbatim (exact on-site text where available)
  - sources (array of live URLs)
  - confidence (high | medium | low)

FAILURE CONDITION
If you cannot comply with the schema exactly, you MUST still output the schema with nulls populated and log failures in `missing[]`. Do NOT refuse. Do NOT explain.

INPUT (RAW SCRAPE MARKDOWN):
{raw_scrape_content}

OUTPUT SCHEMA:
{
  "run_metadata": {
    "run_id": "string (UUID)",
    "website_url": "string",
    "started_at": "ISO-8601 timestamp",
    "finished_at": "ISO-8601 timestamp",
    "crawl_depth": "number",
    "pages_visited": ["array of URLs"]
  },
  "practice": {
    "legal_name": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "brand_name": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "tagline": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "specialty": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "practice_type": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "ownership": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }
  },
  "locations": [
    {
      "type": "primary|additional",
      "address": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "phone": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "email": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "hours": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "accessibility": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    }
  ],
  "contact": {
    "contact_form_url": {
      "value": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "booking_url": {
      "value": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "patient_portal_url": {
      "value": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }
  },
  "providers": [
    {
      "name": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "role": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "credentials": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "specialty": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "conditions_treated": {
        "value": ["array or null"],
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "services_performed": {
        "value": ["array or null"],
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "education": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "certifications": {
        "value": ["array or null"],
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "languages": {
        "value": ["array or null"],
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "years_experience": {
        "value": "number or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "bio_summary": {
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "headshot_url": {
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    }
  ],
  "services": [
    {
      "name": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "category": {
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "target_audience": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "deliverables": {
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "cta": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    }
  ],
  "conditions": [
    {
      "name": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "category": {
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    }
  ],
  "ideal_patient": {
    "who_they_serve": {
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "demographics": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "situations": {
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "exclusions": {
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "referral_requirements": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }
  },
  "clinical_approach": {
    "differentiators": {
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "philosophy": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "diagnostic_methods": {
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "technology": {
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "modalities": {
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "claims": {
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }
  },
  "patient_journey": {
    "first_step_cta": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "new_patient_steps": {
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "discovery_call": {
      "offered": "boolean",
      "description": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    },
    "intake_forms": {
      "available": "boolean",
      "links": {
        "value": ["array or null"],
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    },
    "consult_expectations": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "follow_up": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "memberships": {
      "available": "boolean",
      "details": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    }
  },
  "pricing": {
    "transparency": "TRANSPARENT|PARTIAL|NONE",
    "prices": {
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "insurance_accepted": {
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "medicare_medicaid": {
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "self_pay": {
      "available": "boolean",
      "details": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    },
    "superbills": {
      "available": "boolean",
      "details": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    },
    "payment_plans": {
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "hsa_fsa": {
      "available": "boolean",
      "details": {
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    }
  },
  "trust_signals": {
    "testimonials": {
      "present": "boolean",
      "location": {
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      },
      "themes": {
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    },
    "case_studies": {
      "present": "boolean",
      "urls": {
        "value": ["array or null"],
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    },
    "awards": {
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "associations": {
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "research_citations": {
      "present": "boolean",
      "urls": {
        "value": ["array or null"],
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    },
    "disclaimers": {
      "present": "boolean",
      "verbatim": {
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    }
  },
  "seo_intel": {
    "primary_keywords": {
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "location_modifiers": {
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "conversion_ctas": {
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "lead_magnets": {
      "present": "boolean",
      "urls": {
        "value": ["array or null"],
        "sources": ["array"],
        "confidence": "high|medium|low"
      }
    },
    "forms": {
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    },
    "tech_stack": {
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    }
  },
  "missing": [
    {
      "field": "string (JSON path)",
      "reason": "string (why missing/unclear/contradictory)",
      "impact": "critical|moderate|minor"
    }
  ]
}

BEGIN CONVERSION. OUTPUT JSON ONLY.
```

**Save Response:**
- Structured JSON → `{output_directory}/scrape_data/structured_data.json`

**Validation:**
- Parse JSON to verify valid structure
- Check for critical missing fields (practice.legal_name, locations, services, conditions)
- If critical fields are null: Log to `missing[]` and prompt user for manual input

---

## ERROR HANDLING & FALLBACK

**If Perplexity scrape fails:**
```
═══════════════════════════════════════════════════════════
SCRAPE FAILED
═══════════════════════════════════════════════════════════

The automated website scrape could not be completed.

FALLBACK OPTION:
Use Grok DeepSearch to manually scrape the website and provide
the raw JSON output.

1. Go to: https://x.com/i/grok (or use Grok app)
2. Paste this prompt:
   "Deep search and extract all data from {website_url} following
    healthcare practice intelligence schema"
3. Copy the JSON response
4. Paste it when prompted below

═══════════════════════════════════════════════════════════

[PROMPT] Paste Grok DeepSearch JSON:
```

**Validate manual JSON:**
- Attempt to parse as valid JSON
- Check for required top-level keys
- If invalid: Re-prompt (max 3 attempts)
- If still invalid after 3 attempts: HALT with error

---

## OUTPUT

**Success:**
```json
{
  "status": "success",
  "raw_scrape_path": "/path/to/raw_scrape.md",
  "structured_json_path": "/path/to/structured_data.json",
  "pages_crawled": 45,
  "critical_missing_fields": 0,
  "timestamp": "2025-02-10T12:34:56Z"
}
```

**Failure:**
```json
{
  "status": "failed",
  "error": "string describing error",
  "fallback_used": true|false,
  "partial_data_path": "/path/to/partial.json",
  "timestamp": "2025-02-10T12:34:56Z"
}
```

---

## TESTING

**Test with:**
```bash
website_url="https://example-medical-practice.com"
output_directory="/tmp/d100_test"
additional_context="Functional medicine practice in Austin, TX"
```

**Expected:**
- `raw_scrape.md` contains 10+ sections with source citations
- `structured_data.json` parses without errors
- `missing[]` array contains only minor/moderate issues
- Run completes in < 3 minutes

---

## VERSION HISTORY

**1.0** - Initial release
- Perplexity Sonar integration via OpenRouter
- Grok DeepSearch fallback
- Claude Opus 4.6 JSON conversion
- Full validation and error handling
