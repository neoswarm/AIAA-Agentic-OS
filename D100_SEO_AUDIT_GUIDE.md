# 📊 Dream 100 SEO Audit - Complete Guide

## ✅ **What I Just Built For You**

A **doctor-friendly SEO analysis module** that:
1. Takes SEMrush screenshot + keyword CSV at the **beginning** of D100 workflow
2. Uses **Claude Sonnet 3.7** to analyze the screenshot
3. Generates insights using **your exact prompt** (zero jargon, ELI5-level)
4. Outputs Gamma-ready markdown for busy doctors

---

## 📥 **Inputs Required (At The Beginning)**

### **1. SEMrush Site Overview Screenshot**
**What to capture:**
- Go to SEMrush → Domain Overview
- Enter the practice's website
- Take screenshot of full dashboard showing:
  - Organic traffic trend graph
  - Domain authority score
  - Referring domains count
  - Keyword rankings count
  - Any visible AI/SERP features

**Format:** PNG or JPG
**File name example:** `advfm_semrush_overview.png`

---

### **2. SEMrush Keywords CSV Export**
**How to export:**
- SEMrush → Organic Research → Positions
- Click "Export" button
- Select "CSV" format
- Save file

**Required columns:**
- Keyword
- Position
- Search Volume
- Traffic (optional)

**File name example:** `advfm_keywords.csv`

---

## 🚀 **How to Use It**

### **Full D100 Run with SEO Audit:**

```bash
python3 d100_run.py \
  --url https://advfunctionalmedicine.com \
  --booking https://advfunctionalmedicine.com/book \
  --semrush-screenshot "path/to/semrush_screenshot.png" \
  --semrush-csv "path/to/keywords.csv"
```

### **Example with Real Files:**

```bash
python3 d100_run.py \
  --url https://advfunctionalmedicine.com \
  --booking https://advfunctionalmedicine.com/book \
  --semrush-screenshot "~/Downloads/advfm_semrush_feb2026.png" \
  --semrush-csv "~/Downloads/advfm_keywords_export.csv"
```

---

## 📋 **Workflow Execution Order**

```
User provides inputs:
  - Website URL ✓
  - Booking URL ✓
  - SEMrush Screenshot ✓
  - SEMrush CSV ✓
         ↓
═══════════════════════════════════════════════════════════
PHASE 1: WEBSITE SCRAPING
═══════════════════════════════════════════════════════════
  🔍 Scraping with Perplexity Sonar...
  ✅ Website scraped (45 pages)

  🔄 Converting to JSON with Claude Sonnet...
  ✅ Structured JSON generated
         ↓
═══════════════════════════════════════════════════════════
PHASE 1.5: BRIGHTLOCAL KEYWORDS
═══════════════════════════════════════════════════════════
  📊 Generating 100 local SEO keywords...
  ✅ 100 keywords generated
  💾 Saved to: seo_data/brightlocal_keywords.txt
  📢 Sent to Slack!
         ↓
═══════════════════════════════════════════════════════════
PHASE 2: SEO ANALYSIS FOR DOCTORS
═══════════════════════════════════════════════════════════
  📈 Analyzing SEMrush data with Claude Sonnet 3.7...
     Screenshot: ~/Downloads/advfm_semrush.png
     Keywords CSV: ~/Downloads/advfm_keywords.csv

  ✅ Doctor-friendly SEO analysis generated
  💾 Saved to: seo_data/seo_analysis_for_doctors.md
         ↓
═══════════════════════════════════════════════════════════
PHASE 3: GENERATING ASSETS (PARALLEL)
═══════════════════════════════════════════════════════════
  🏥 Building health assessment app...
  📢 Building Google Ads campaigns...
  📧 Building email sequence...
```

---

## 📊 **What Gets Generated**

### **SEO Analysis Output:**
**File:** `seo_data/seo_analysis_for_doctors.md`

**Structure (EXACTLY as you specified):**

```markdown
# What's Actually Happening With Your Website

## Bottom Line
2-3 sentence verdict on trust, visibility, and patient demand.

## What the Data Shows
Bulleted, simple language explaining:
- Organic traffic trend
- Keyword footprint
- Authority / backlinks
- AI visibility (AI Overviews, Gemini)

Translated into: patients, trust, demand.

## What Changed And Why It Matters
How Google + AI answer patient questions directly.
Analogies doctors understand.
Authority without clicks.

## The Real Problem
How the practice helps Google educate patients
without sending those patients to the practice.
Real cost, no alarmism.

## Why This Is Actually an Opportunity
Contrast against competitors:
- Most: declining traffic, zero AI visibility
- You: AI trust but poor conversion

Leverage position, not rebuild.

## If Nothing Changes
Ranges and plain consequences:
- Patient inquiries
- Cost of ads
- Competitive positioning

Reality, no fear-mongering.

## If This Is Handled Correctly
Clear, credible upside:
- Recapture demand answered by AI
- Become the named authority AI recommends
- Turn visibility into booked appointments
```

---

## 🎯 **Key Features**

### **1. Uses Your EXACT Prompt**
✅ Zero jargon unless explained
✅ ELI5-level clarity
✅ Written for 90-second attention span
✅ Gamma-ready formatting
✅ No parentheses, no brackets, no placeholders

### **2. Claude Sonnet 3.7 Analyzes Screenshot**
✅ Reads traffic graphs
✅ Interprets domain authority
✅ Extracts backlink data
✅ Identifies AI visibility signals

### **3. CSV Data Integrated**
✅ Top 10 keywords analyzed
✅ Position tracking
✅ Search volume context
✅ Ranking trends

### **4. Practice Context from JSON**
✅ Practice name
✅ Specialty
✅ Primary market
✅ Services + conditions

---

## 🔍 **Example Analysis Output**

Based on your prompt, here's what a busy doctor would see:

```markdown
# What's Actually Happening With Your Website

## Bottom Line

Your site ranks for 347 healthcare keywords and gets 2,400 patient
searches per month. Google trusts your content enough to answer
questions about thyroid treatment and hormone therapy using your
articles. The problem is that patients are getting their answers
without clicking through to book appointments.

## What the Data Shows

Your organic traffic has declined 18% in the past six months despite:
- More keywords ranking (347, up from 312)
- Higher domain authority (42, considered strong for local healthcare)
- 89 referring domains (quality medical blogs and directories)
- Appearing in 12 AI Overview results for thyroid and autoimmune queries

This means Google values your expertise more than ever, but patients
are calling you less. That disconnect is the entire opportunity.

## What Changed And Why It Matters

Think of Google like a medical resident. Two years ago, when patients
asked about thyroid treatment, the resident said "go see this doctor."
Now, the resident learned enough from your content to answer the
question directly and only sends patients when they need a prescription
or appointment.

Your content trained the AI. The AI now competes with you for patient
attention.

...
```

---

## ✅ **Verification Checklist**

Before running, confirm:

- [ ] SEMrush screenshot shows full domain overview dashboard
- [ ] Screenshot is clear and readable (PNG/JPG, not blurry)
- [ ] CSV has columns: Keyword, Position, Search Volume
- [ ] CSV has at least 10 keywords exported
- [ ] Both files are saved locally (not in cloud/temporary location)
- [ ] File paths have no spaces (or wrapped in quotes)

---

## 🚨 **Common Issues & Fixes**

### **Issue 1: "Need BOTH screenshot AND CSV"**
**Cause:** Only provided one file, not both
**Fix:** Provide both `--semrush-screenshot` AND `--semrush-csv`

### **Issue 2: "Could not parse CSV"**
**Cause:** CSV format incorrect or missing required columns
**Fix:** Re-export from SEMrush → Organic Research → Positions → Export CSV

### **Issue 3: "Cannot encode image"**
**Cause:** Screenshot file not found or wrong format
**Fix:** Verify file path exists, use PNG or JPG format

### **Issue 4: Analysis mentions brackets/placeholders**
**Cause:** Prompt not being followed correctly
**Fix:** This shouldn't happen - the prompt explicitly forbids it. Check output file.

---

## 📂 **Output File Locations**

All outputs saved to timestamped run directory:

```
output/d100_runs/{timestamp}/
├── seo_data/
│   ├── brightlocal_keywords.txt       # 100 local SEO keywords
│   ├── brightlocal_keywords.json      # Keyword data + metadata
│   └── seo_analysis_for_doctors.md    # 🔥 Doctor-friendly SEO insights
│
├── ads/
│   └── google_ads_campaigns.md
│
├── emails/
│   └── email_sequence.md
│
└── app/
    └── health_assessment_app.html
```

---

## 🎯 **Real-World Example**

### **Command:**
```bash
python3 d100_run.py \
  --url https://advfunctionalmedicine.com \
  --booking https://advfunctionalmedicine.com/book \
  --semrush-screenshot "~/Desktop/advfm_semrush_feb11.png" \
  --semrush-csv "~/Desktop/advfm_keywords_export.csv"
```

### **Expected Output:**
```
🚀 DREAM 100 AUTOMATION - STARTING

📍 Website: https://advfunctionalmedicine.com
📅 Run ID: 20260211_140530
💾 Output: output/d100_runs/20260211_140530

═══════════════════════════════════════════════════════════
PHASE 1: WEBSITE SCRAPING
═══════════════════════════════════════════════════════════

🔍 Scraping website with Perplexity Sonar...
✅ Website scraped (52 pages)

🔄 Converting to structured JSON with Claude Sonnet...
✅ Structured JSON generated

═══════════════════════════════════════════════════════════
PHASE 1.5: BRIGHTLOCAL KEYWORDS
═══════════════════════════════════════════════════════════

📊 Generating 100 local SEO keywords...
✅ 100 keywords generated
💾 Saved to: seo_data/brightlocal_keywords.txt
📢 Sent to Slack!

═══════════════════════════════════════════════════════════
PHASE 2: SEO ANALYSIS FOR DOCTORS
═══════════════════════════════════════════════════════════

📈 Analyzing SEMrush data with Claude Sonnet 3.7...
   Screenshot: ~/Desktop/advfm_semrush_feb11.png
   Keywords CSV: ~/Desktop/advfm_keywords_export.csv

✅ Doctor-friendly SEO analysis generated
💾 Saved to: seo_data/seo_analysis_for_doctors.md

═══════════════════════════════════════════════════════════
PHASE 3: GENERATING ASSETS (PARALLEL)
═══════════════════════════════════════════════════════════

[...continues with ads, emails, app generation...]
```

---

## 📝 **Summary**

### **What Changed:**
1. ✅ Added `--semrush-screenshot` argument (accepts PNG/JPG)
2. ✅ Added `--semrush-csv` argument (accepts CSV file)
3. ✅ Created `D100SEOAudit` module with your exact prompt
4. ✅ Integrated into main workflow (runs after BrightLocal keywords)
5. ✅ Uses Claude Sonnet 3.7 to analyze screenshot
6. ✅ Outputs Gamma-ready markdown with zero jargon

### **Verification:**
- ✅ Prompt structure: EXACT match to your specifications
- ✅ Headings: EXACT (7 mandatory sections)
- ✅ Tone: Calm, confident, direct, slightly urgent
- ✅ Audience: Busy doctors, zero marketing background
- ✅ Constraints: No jargon, no parentheses, no brackets, no placeholders
- ✅ Format: Gamma-ready, large text blocks, strong headings

---

**Your D100 workflow now accepts SEMrush screenshot + CSV at the beginning and generates doctor-friendly SEO insights using your exact prompt!** 🎉

---

**Generated:** February 11, 2026
**AIAA Agentic OS v3.0**
