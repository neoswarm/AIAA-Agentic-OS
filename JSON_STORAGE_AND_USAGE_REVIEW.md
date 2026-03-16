# 📊 JSON Storage & Usage Review - Dream 100 Workflow

## Overview

The Dream 100 workflow generates **ONE MASTER JSON** file (`structured_data.json`) that serves as the **single source of truth** for all downstream assets (Google Ads, emails, health assessment app, SEO insights).

---

## 🔄 **The Complete Data Flow**

```
User Input
   ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: WEBSITE SCRAPING                                       │
│ ─────────────────────────────────────────────────────────       │
│ 1. Perplexity Sonar scrapes website                            │
│    Output: raw_scrape.md (11 sections, source citations)       │
│                                                                  │
│ 2. Claude Sonnet converts to JSON                              │
│    Output: structured_data.json (strict schema)                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────┐
                    │ MASTER JSON FILE │
                    │ structured_data  │
                    │     .json        │
                    └─────────────────┘
                    ↓   ↓   ↓   ↓   ↓
     ┌──────────────┼───┼───┼───┼───┼──────────────┐
     │              │   │   │   │   │              │
     ↓              ↓   ↓   ↓   ↓   ↓              ↓
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│ Google  │  │ Email   │  │ Health  │  │ SEO     │  │ App     │
│ Ads     │  │Sequence │  │ Assess. │  │ Audit   │  │ Builder │
│ Builder │  │ Builder │  │ App     │  │         │  │         │
└─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘
     │              │            │            │            │
     ↓              ↓            ↓            ↓            ↓
 ads.md      emails.md    health_app.html  seo.md    app_data.json
```

---

## 📁 **File Storage Structure**

All outputs are stored in timestamped run directories:

```
output/d100_runs/{timestamp}/
├── inputs.json                    # User inputs (URL, booking, context)
├── manifest.json                  # Summary of all generated assets
│
├── scrape_data/                   # 🔥 THE MASTER DATA SOURCE
│   ├── raw_scrape.md             # Perplexity Sonar output (11 sections)
│   └── structured_data.json      # ⭐ MASTER JSON - Used by ALL modules
│
├── seo_data/                      # SEO analysis outputs
│   ├── keywords.json
│   └── seo_insights.md
│
├── ads/                           # Google Ads campaigns
│   ├── google_ads_campaigns.md
│   ├── CAMPAIGN_SUMMARY.txt
│   └── KEYWORDS_THAT_PRINT_MONEY.md
│
├── emails/                        # Email sequence
│   ├── sequence.md
│   ├── plain_text.txt
│   └── GENERATION_SUMMARY.md
│
└── app/                           # Health assessment app
    ├── health_app.html
    └── app_config.json
```

---

## 🎯 **The Master JSON Schema**

The `structured_data.json` file follows this exact schema:

```json
{
  "run_metadata": {
    "run_id": "string (UUID)",
    "website_url": "string",
    "started_at": "ISO-8601",
    "finished_at": "ISO-8601",
    "crawl_depth": "number",
    "pages_visited": ["array of URLs"]
  },

  "practice": {
    "legal_name": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
    "brand_name": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
    "tagline": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
    "specialty": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
    "practice_type": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
    "ownership": { "value": "", "verbatim": "", "sources": [], "confidence": "" }
  },

  "locations": [
    {
      "type": "primary|additional",
      "address": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
      "phone": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
      "email": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
      "hours": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
      "accessibility": { "value": "", "verbatim": "", "sources": [], "confidence": "" }
    }
  ],

  "contact": {
    "contact_form_url": { "value": "", "sources": [], "confidence": "" },
    "booking_url": { "value": "", "sources": [], "confidence": "" },
    "patient_portal_url": { "value": "", "sources": [], "confidence": "" }
  },

  "providers": [
    {
      "name": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
      "role": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
      "credentials": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
      "specialty": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
      "conditions_treated": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
      "services_performed": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
      "education": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
      "certifications": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
      "languages": { "value": [], "sources": [], "confidence": "" },
      "years_experience": { "value": 0, "verbatim": "", "sources": [], "confidence": "" },
      "bio_summary": { "value": "", "sources": [], "confidence": "" },
      "headshot_url": { "value": "", "sources": [], "confidence": "" }
    }
  ],

  "services": [
    {
      "name": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
      "category": { "value": "", "sources": [], "confidence": "" },
      "target_audience": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
      "deliverables": { "value": "", "sources": [], "confidence": "" },
      "cta": { "value": "", "verbatim": "", "sources": [], "confidence": "" }
    }
  ],

  "conditions": [
    {
      "name": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
      "category": { "value": "", "sources": [], "confidence": "" }
    }
  ],

  "ideal_patient": {
    "who_they_serve": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
    "demographics": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
    "situations": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
    "exclusions": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
    "referral_requirements": { "value": "", "verbatim": "", "sources": [], "confidence": "" }
  },

  "clinical_approach": {
    "differentiators": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
    "philosophy": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
    "diagnostic_methods": { "value": [], "sources": [], "confidence": "" },
    "technology": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
    "modalities": { "value": [], "sources": [], "confidence": "" },
    "claims": { "value": [], "verbatim": "", "sources": [], "confidence": "" }
  },

  "patient_journey": {
    "first_step_cta": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
    "new_patient_steps": { "value": [], "sources": [], "confidence": "" },
    "discovery_call": {
      "offered": false,
      "description": { "value": "", "verbatim": "", "sources": [], "confidence": "" }
    },
    "intake_forms": {
      "available": false,
      "links": { "value": [], "sources": [], "confidence": "" }
    },
    "consult_expectations": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
    "follow_up": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
    "memberships": {
      "available": false,
      "details": { "value": "", "verbatim": "", "sources": [], "confidence": "" }
    }
  },

  "pricing": {
    "transparency": "TRANSPARENT|PARTIAL|NONE",
    "prices": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
    "insurance_accepted": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
    "medicare_medicaid": { "value": "", "verbatim": "", "sources": [], "confidence": "" },
    "self_pay": {
      "available": false,
      "details": { "value": "", "verbatim": "", "sources": [], "confidence": "" }
    },
    "superbills": {
      "available": false,
      "details": { "value": "", "verbatim": "", "sources": [], "confidence": "" }
    },
    "payment_plans": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
    "hsa_fsa": {
      "available": false,
      "details": { "value": "", "verbatim": "", "sources": [], "confidence": "" }
    }
  },

  "trust_signals": {
    "testimonials": {
      "present": false,
      "location": { "value": "", "sources": [], "confidence": "" },
      "themes": { "value": "", "sources": [], "confidence": "" }
    },
    "case_studies": {
      "present": false,
      "urls": { "value": [], "sources": [], "confidence": "" }
    },
    "awards": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
    "associations": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
    "research_citations": {
      "present": false,
      "urls": { "value": [], "sources": [], "confidence": "" }
    },
    "disclaimers": {
      "present": false,
      "verbatim": { "value": "", "sources": [], "confidence": "" }
    }
  },

  "seo_intel": {
    "primary_keywords": { "value": [], "sources": [], "confidence": "" },
    "location_modifiers": { "value": [], "sources": [], "confidence": "" },
    "conversion_ctas": { "value": [], "verbatim": "", "sources": [], "confidence": "" },
    "lead_magnets": {
      "present": false,
      "urls": { "value": [], "sources": [], "confidence": "" }
    },
    "forms": { "value": [], "sources": [], "confidence": "" },
    "tech_stack": { "value": [], "sources": [], "confidence": "" }
  },

  "missing": [
    {
      "field": "string (JSON path)",
      "reason": "string (why missing/unclear/contradictory)",
      "impact": "critical|moderate|minor"
    }
  ]
}
```

---

## 📥 **How Each Module Uses the JSON**

### **1. Google Ads Builder** (`build_google_ads_gemini.py`)

**Reads:**
```python
with open(structured_data_path) as f:
    data = json.load(f)

practice_context = {
    "practice": data.get("practice", {}),
    "locations": data.get("locations", []),
    "providers": data.get("providers", []),
    "services": data.get("services", []),
    "conditions": data.get("conditions", []),
    "ideal_patient": data.get("ideal_patient", {}),
    "clinical_approach": data.get("clinical_approach", {}),
    "patient_journey": data.get("patient_journey", {}),
    "pricing": data.get("pricing", {}),
    "trust_signals": data.get("trust_signals", {})
}

seo_context = data.get("seo_intel", {})
```

**Uses:**
- `practice.brand_name.value` → Campaign names
- `services[].name.value` → Ad headlines
- `conditions[].name.value` → Keyword targeting
- `clinical_approach.differentiators.value` → Ad copy USPs
- `trust_signals.awards.value` → Callout extensions
- `patient_journey.first_step_cta.verbatim` → CTA text
- `seo_intel.primary_keywords.value` → Keyword research
- `locations[].address.value` → Location targeting

**Outputs:**
- `google_ads_campaigns_{company_name}_{timestamp}.md`

---

### **2. Email Sequence Builder** (`generate_d100_email_sequence.py`)

**Reads:**
```python
with open(structured_data_path) as f:
    data = json.load(f)

# Extract key info
brand_name = data["practice"]["brand_name"]["value"]
services = [s["name"]["value"] for s in data["services"]]
conditions = [c["name"]["value"] for c in data["conditions"]]
providers = data["providers"]
trust_signals = data["trust_signals"]
```

**Uses:**
- `practice.tagline.verbatim` → Email subject lines
- `services[].name.verbatim` → Email body content
- `conditions[].name.value` → Pain point targeting
- `providers[].name.value` → Provider signature
- `trust_signals.testimonials.themes.value` → Social proof
- `patient_journey.discovery_call.description.verbatim` → CTA copy
- `pricing.transparency` → Pricing messaging

**Outputs:**
- `email_sequence_{timestamp}.md` (3 emails)

---

### **3. Health Assessment App Builder**

**Reads:**
```python
with open(structured_data_path) as f:
    data = json.load(f)

# Build assessment questions from conditions
conditions = [c["name"]["value"] for c in data["conditions"]]
services = data["services"]
booking_url = data["contact"]["booking_url"]["value"]
```

**Uses:**
- `conditions[].name.value` → Assessment questions
- `services[].target_audience.verbatim` → Personalization logic
- `contact.booking_url.value` → Form submission endpoint
- `practice.brand_name.value` → App branding
- `patient_journey.intake_forms.links.value` → Pre-fill logic

**Outputs:**
- `health_assessment_app.html`

---

### **4. SEO Audit Module** (`d100_seo_audit.py`)

**Reads:**
```python
with open(structured_data_path) as f:
    data = json.load(f)

# Extract SEO-relevant data
keywords = data["seo_intel"]["primary_keywords"]["value"]
locations = [loc["address"]["value"] for loc in data["locations"]]
services = [s["name"]["value"] for s in data["services"]]
conditions = [c["name"]["value"] for c in data["conditions"]]
```

**Uses:**
- `seo_intel.primary_keywords.value` → Keyword opportunities
- `seo_intel.location_modifiers.value` → Local SEO targeting
- `services[].name.value` → Service-based keywords
- `conditions[].name.value` → Condition-based keywords
- `practice.specialty.value` → Entity SEO modeling

**Outputs:**
- `seo_insights_{timestamp}.md`
- `brightlocal_keywords.json`

---

## 🔑 **Critical Fields Used Across ALL Modules**

These fields are referenced by **multiple downstream modules**:

| Field | Used By | Purpose |
|-------|---------|---------|
| `practice.brand_name.value` | Ads, Emails, App, SEO | Branding, campaign names |
| `services[].name.value` | Ads, Emails, App, SEO | Headlines, content, questions |
| `conditions[].name.value` | Ads, Emails, App, SEO | Targeting, pain points, keywords |
| `patient_journey.first_step_cta.verbatim` | Ads, Emails, App | CTA text |
| `contact.booking_url.value` | Ads, Emails, App | Conversion destination |
| `locations[].address.value` | Ads, SEO | Geo-targeting |
| `trust_signals.awards.value` | Ads, Emails | Social proof |
| `clinical_approach.differentiators.value` | Ads, Emails | USP messaging |

---

## ✅ **Data Quality & Validation**

### **Every Field Includes:**
1. **`value`** - The extracted data
2. **`verbatim`** - Exact on-site text (for compliance)
3. **`sources`** - Array of URLs where found
4. **`confidence`** - `high`, `medium`, or `low`

### **Missing Data Handling:**
- Missing fields → `null`
- Issues logged in `missing[]` array with:
  - `field` (JSON path)
  - `reason` (why missing)
  - `impact` (critical/moderate/minor)

### **Example:**
```json
{
  "practice": {
    "brand_name": {
      "value": "Advanced Functional Medicine",
      "verbatim": "Advanced Functional Medicine - San Diego's Largest Clinic",
      "sources": ["https://advfunctionalmedicine.com/"],
      "confidence": "high"
    }
  },
  "missing": [
    {
      "field": "pricing.prices",
      "reason": "No pricing information found on any page",
      "impact": "moderate"
    }
  ]
}
```

---

## 🚀 **The Complete Workflow**

### **Phase 1: Data Collection**
```bash
python3 d100_run.py \
  --url https://advfunctionalmedicine.com \
  --booking https://advfunctionalmedicine.com/book
```

**Outputs:**
- `scrape_data/raw_scrape.md` ← Perplexity Sonar
- `scrape_data/structured_data.json` ← Claude Sonnet ⭐

### **Phase 2: Asset Generation (Parallel)**

All modules read the same JSON:

```python
# modules/d100_ads_builder.py
with open("scrape_data/structured_data.json") as f:
    data = json.load(f)

# modules/d100_email_builder.py
with open("scrape_data/structured_data.json") as f:
    data = json.load(f)

# modules/d100_app_builder.py
with open("scrape_data/structured_data.json") as f:
    data = json.load(f)
```

**Outputs:**
- `ads/google_ads_campaigns.md`
- `emails/email_sequence.md`
- `app/health_assessment_app.html`
- `seo_data/seo_insights.md`

### **Phase 3: Compilation**

Creates `manifest.json` with paths to all assets:

```json
{
  "run_id": "20260210_144328",
  "website_url": "https://advfunctionalmedicine.com",
  "outputs": {
    "scrape_data": {
      "raw_markdown": "scrape_data/raw_scrape.md",
      "structured_json": "scrape_data/structured_data.json"
    },
    "health_app": "app/health_app.html",
    "google_ads": "ads/google_ads_campaigns.md",
    "email_sequence": "emails/email_sequence.md",
    "seo_data": "seo_data/seo_insights.md"
  }
}
```

---

## 🎯 **Summary: Why This Architecture Works**

### **1. Single Source of Truth**
- ONE JSON file feeds ALL modules
- No data duplication
- No sync issues

### **2. Schema Enforcement**
- Claude enforces exact schema compliance
- Missing data → `null` (never hallucinated)
- Validation built-in

### **3. Source-Grounded**
- Every field includes source URLs
- Verbatim text for compliance
- Confidence scoring

### **4. Automation-Ready**
- Clean JSON structure
- Consistent field naming
- Arrays always present (even if empty)

### **5. Scalable**
- Add new modules → just read the JSON
- Update schema → all modules update together
- No breaking changes

---

## 🔄 **Next: The User's New Prompt**

The user just shared an **enhanced JSON conversion prompt** with stricter rules. This is the **second prompt** in the workflow (after Perplexity Sonar scrapes).

**Current Prompt Location:** `skills/SKILL_D100_scraper.md` lines 302-824

**User's Enhanced Version:** Includes additional enforcement rules for automation pipelines.

---

**Generated:** February 11, 2026
**AIAA Agentic OS v3.0**
