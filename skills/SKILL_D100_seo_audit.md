# SKILL: Dream 100 SEO Audit

## METADATA
- **Skill Name**: Dream 100 SEO Audit
- **Version**: 2.0
- **Category**: SEO Analysis
- **API Requirements**: OpenAI GPT-4, OpenRouter (Gemini Flash 2.0)
- **Parent Skill**: SKILL_D100_orchestrator

---

## MISSION
Generate BrightLocal keywords, analyze SEMrush data, and extract actionable local SEO insights for Dream 100 outreach campaigns.

---

## INPUT REQUIREMENTS

**Required:**
- `structured_json` (object): Output from SKILL_D100_scraper
- `output_directory` (string): Path to save outputs

**Optional (provided after pause):**
- `brightlocal_pdf_path` (string): User-uploaded BrightLocal audit PDF
- `semrush_csv_path` (string): User-uploaded SEMrush keyword export CSV

---

## EXECUTION LOGIC

### STEP 1: GENERATE BRIGHTLOCAL KEYWORDS

**Use:** OpenAI GPT-4o (Direct OpenAI API)

**API Configuration:**
```bash
OPENAI_API_KEY (from .env)
Endpoint: https://api.openai.com/v1/chat/completions
Model: gpt-4o
Temperature: 0.4
Max tokens: 4000
```

**Extract from JSON:**
- Services → `structured_json.services[].name.value`
- Conditions → `structured_json.conditions[].name.value`
- Primary city → Parse from `structured_json.locations[0].address.value`
- Adjacent cities → Infer from `structured_json.seo_intel.location_modifiers.value` OR prompt user

**Prompt:**

```
You are a senior local SEO strategist preparing a BrightLocal rank-tracking and audit keyword set for a medical or healthcare practice.

TASK:
Using the company context I provide (services, conditions treated, primary city, and adjacent cities), generate a list of up to **100 UNIQUE, high-intent keywords** suitable for a BrightLocal Local SEO Audit and Rank Tracking setup.

GOAL:
Create a clean, non-duplicative keyword list that accurately reflects:
- Core commercial intent
- Local intent ("near me" and city-modified searches)
- Service-based and condition-based demand

CONTEXT:
[SERVICES]: {services_list}
[CONDITIONS]: {conditions_list}
[CITY]: {primary_city}
[ADJACENT_CITIES]: {adjacent_cities} (if not available in JSON, prompt: "Please provide 3 nearby cities for keyword expansion:")

KEYWORD RULES:
- Max 100 total keywords
- One keyword per line
- No duplicates or close variants
- Use natural, real search phrases (no keyword stuffing)
- Prioritize patient / appointment intent
- Mix singular and plural ONLY when meaningfully different
- Do NOT add extra cities beyond those provided
- Do NOT include brand terms

KEYWORD CATEGORIES TO COVER (DISTRIBUTE EVENLY):

1. SERVICES
2. CONDITIONS
3. X near me
4. SERVICES [CITY]
5. CONDITIONS [CITY]
6. X near [CITY]
7. SERVICES [ADJACENT CITY 1]
8. SERVICES [ADJACENT CITY 2]
9. SERVICES [ADJACENT CITY 3]
10. CONDITIONS [ADJACENT CITY 1]
11. CONDITIONS [ADJACENT CITY 2]
12. CONDITIONS [ADJACENT CITY 3]
13. X near me [ADJACENT CITY 1]
14. X near me [ADJACENT CITY 2]
15. X near me [ADJACENT CITY 3]

OUTPUT FORMAT (STRICT – BRIGHTLOCAL READY):
- Plain text
- One keyword per line
- No headings
- No numbering
- No explanations
- Copy & paste ready for BrightLocal
```

**Save Output:**
- Plain text → `{output_directory}/seo_data/brightlocal_keywords.txt`

**Display to user:**
```
═══════════════════════════════════════════════════════════
✓ BrightLocal Keywords Generated (100 keywords)
═══════════════════════════════════════════════════════════

[DISPLAY FIRST 20 KEYWORDS]

...and 80 more.

FULL LIST SAVED TO:
{output_directory}/seo_data/brightlocal_keywords.txt

NEXT STEPS:
1. Copy keywords from the file above
2. Go to BrightLocal and run a Local Search Audit
3. Export the audit as PDF
4. Open SEMrush: https://www.semrush.com/analytics/overview/?searchType=domain&q={website_url}
5. Export keyword rankings as CSV

═══════════════════════════════════════════════════════════
```

**Open SEMrush link in default browser:**
```bash
open "https://www.semrush.com/analytics/overview/?searchType=domain&q={website_url}"
```

---

### STEP 2: OPTIONAL - ANALYZE BRIGHTLOCAL AUDIT (v2.0 - NO PAUSE)

**v2.0 Change:** This step is now OPTIONAL. If BrightLocal PDF is provided in the initial input, analyze it. If not provided, SKIP and continue. DO NOT pause the workflow.

**Trigger:** `brightlocal_pdf_path` provided in initial input (or skip)

**Validate PDF:**
- File exists and is readable
- File size > 10KB (not empty)
- If invalid: Re-prompt

**Use:** OpenAI o1 (Direct OpenAI API - Reasoning Model)

**Prompt:**

```
You are a senior local SEO auditor and healthcare growth strategist specializing in functional medicine and medical practices.

TASK:
Analyze the attached Local Search Audit PDF report as your PRIMARY INPUT and extract the 3 most critical revenue-blocking issues affecting patient acquisition from Google Search and Google Maps.

INPUT:
- Local Search Audit PDF (directory coverage, GBP, on-site SEO, speed, mobile, authority, reviews)
- Assume this report reflects the CURRENT live state of the practice

OBJECTIVE:
Translate technical SEO findings into a **plain-English, executive-level diagnostic** that clearly explains:
- What is broken
- Why it matters in terms of lost patient calls
- Exactly what needs to be fixed to increase consultations

AUDIENCE:
Practice owner / medical director (non-technical, revenue-focused)

ANALYSIS RULES:
- Prioritize issues that directly impact phone calls, form fills, and map visibility
- Ignore minor technical nitpicks unless they materially affect conversions
- Tie each issue to REAL-WORLD patient loss (missed calls, lower map pack exposure, lower trust)
- Use assertive, confident language (authority tone, not apologetic)
- ENSURE IT DOES NOT CONTRADICT THE PREVIOUS SEO INSIGHTS FOR THE SAME WEBSITE

OUTPUT FORMAT (STRICT — FOLLOW EXACTLY):

I ran a full technical audit of your practice's local search presence across Google Business Profile, local directories, website performance, and mobile usability.

The short version: you're visible for a few core terms, but there are 3 critical gaps costing you patient calls every month.

Critical Issue #1:
Current state:
[Explain what the audit shows, referencing findings from the PDF in simple terms]

What this costs you:
[Explain the real-world impact in lost calls, visibility, or trust]

The fix:
[Clear, specific corrective action — no tools, no fluff]

Critical Issue #2:
Current state:
[Explain the issue]

What this costs you:
[Revenue / lead loss explanation]

The fix:
[Actionable solution]

Critical Issue #3:
Current state:
[Explain the issue]

What this costs you:
[Revenue / lead loss explanation]

The fix:
[Actionable solution]

CONSTRAINTS:
- No technical jargon unless absolutely necessary
- No bullet points inside sections
- No numbers unless tied to impact
- No recommendations outside the 3 issues
- Output must be ready to paste into a Loom script, email, or sales audit doc

RETURN:
Text only.
No commentary.
No explanations about the PDF.
No summaries outside the defined structure.
```

**API Call:**
```bash
# Upload PDF to OpenAI Files API
file_id=$(curl -X POST "https://api.openai.com/v1/files" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F "purpose=assistants" \
  -F "file=@{brightlocal_pdf_path}" \
  | jq -r '.id')

# Use o1 reasoning model with file
curl -X POST "https://api.openai.com/v1/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "o1",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "[PROMPT ABOVE]"
          },
          {
            "type": "file",
            "file_id": "'$file_id'"
          }
        ]
      }
    ],
    "max_completion_tokens": 3000
  }'
```

**Save Output:**
- Markdown → `{output_directory}/seo_data/local_audit_insights.md`

---

### STEP 3: OPTIONAL - ANALYZE SEMRUSH DATA (v2.0 - NO PAUSE)

**v2.0 Change:** This step is now OPTIONAL. If SEMrush CSV is provided in the initial input, analyze it. If not provided, SKIP and continue. DO NOT pause the workflow.

**Trigger:** `semrush_csv_path` provided in initial input (or skip)

**Validate CSV:**
- File exists and is readable
- Contains columns: "Keyword", "Position", "Search Volume", "Traffic %", "URL"
- If invalid: Re-prompt

**Use:** OpenAI o1 (Direct OpenAI API - Reasoning Model)

**Parse CSV and extract:**
- Total organic keywords
- Keywords ranking in top 3
- Keywords ranking 4-10
- Keywords ranking 11-20
- Keywords with high volume (>1000/mo)
- Top ranking pages

**Prompt:**

```
You are a senior healthcare growth strategist who specializes in explaining SEO, AI search, and patient acquisition to BUSY DOCTORS who do NOT understand marketing.

TASK:
Evaluate this medical/healthcare website using the SEMrush keyword rankings data provided.

Your job is to translate this data into **Dream 100–level insights** that are:
- Extremely clear
- Honest (no hype, no jargon)
- Engaging and slightly provocative
- Easy enough to understand at an ELI5 level
- Written for a physician who has 90 seconds of attention

PRIMARY GOAL:
Help the doctor understand:
1) What is ACTUALLY happening with their site
2) Why traffic/patients are going up or down
3) How Google + AI are changing patient behavior
4) Whether this is a threat, an opportunity, or both
5) What happens if they do nothing vs act correctly

AUDIENCE:
- Busy doctors
- Practice owners
- Medical executives
- Zero marketing background
- Care about patients, authority, and revenue — not SEO terms

INPUT DATA:
- Total organic keywords: {total_keywords}
- Top 3 rankings: {top3_count}
- Position 4-10: {position_4_10_count}
- Position 11-20: {position_11_20_count}
- High-volume keywords (>1000/mo): {high_volume_keywords}
- Top ranking pages: {top_pages}

CONSTRAINTS:
- NO marketing jargon unless immediately explained in plain English
- NO tactical how-to steps
- NO selling services
- NO fluff, buzzwords, or generic SEO explanations
- Tone: calm, confident, direct, slightly urgent
- Write like a trusted advisor, not a marketer

STRUCTURE (MANDATORY):

1. HEADLINE
"What's Actually Happening With Your Website"

2. BOTTOM LINE (2–3 sentences max)
Plain-English verdict on trust, visibility, and patient demand.

3. WHAT THE DATA SHOWS (Bulleted, simple language)
Explain ONLY what matters from:
- Organic traffic trend
- Keyword footprint
- Authority / backlinks
- AI visibility (AI Overviews, Gemini, etc.)
Translate metrics into real-world meaning (patients, trust, demand).

4. WHAT CHANGED (AND WHY IT MATTERS)
Explain how Google and AI now answer patient questions directly.
Use analogies a doctor would understand.
Emphasize "authority without clicks" and "answers without visits."

5. THE REAL PROBLEM (ELI5)
Clearly state how the practice is helping Google educate patients
without sending those patients to the practice.
Make the cost feel real but not alarmist.

6. WHY THIS IS ACTUALLY AN OPPORTUNITY
Contrast the practice against competitors:
- Most have declining traffic AND zero AI visibility
- This site has AI trust but poor conversion/control
Explain why this is a leverage position, not a rebuild.

7. IF NOTHING CHANGES (Forecast)
Use ranges and plain consequences:
- Patient inquiries
- Cost of ads
- Competitive positioning
No fear-mongering, just reality.

8. IF THIS IS HANDLED CORRECTLY
Paint a clear, credible upside:
- Recapturing demand already being answered by AI
- Becoming the named authority AI systems recommend
- Turning visibility into booked appointments

OUTPUT RULES:
- Write in short paragraphs
- Use bold for emphasis sparingly
- Speak directly to "you"
- No emojis
- No disclaimers
- No marketing terminology unless explained like you're talking to a busy doctor

Return ONLY the final narrative. No explanations. No meta commentary.
```

**Save Output:**
- Markdown → `{output_directory}/seo_data/seo_insights.md`

---

## COMBINED OUTPUT

**Create master SEO report:**
`{output_directory}/seo_data/seo_master_report.md`

```markdown
# Dream 100 SEO Intelligence Report

**Website:** {website_url}
**Analysis Date:** {timestamp}
**Run ID:** {run_id}

---

## Executive Summary

[Auto-generate 3-sentence summary combining BrightLocal + SEMrush insights]

---

## BrightLocal Keywords (100)

[Full keyword list]

---

## Local Search Audit Findings

[Content from local_audit_insights.md]

---

## Organic SEO Performance Analysis

[Content from seo_insights.md]

---

## Recommended Actions

**Immediate (0-7 days):**
- [Extract from local audit fixes]

**Short-term (1-4 weeks):**
- [Extract from SEO insights]

**Long-term (1-3 months):**
- [Strategic recommendations]

---

## Keyword Opportunities

**High-Intent, Low-Competition:**
[Extract from SEMrush data where volume >500, position >10]

**Quick Wins (Already Ranking 4-10):**
[Extract keywords in position 4-10 with volume >200]

---

_Report generated by AIAA Dream 100 Automation v1.0_
```

---

## OUTPUT

**Success:**
```json
{
  "status": "success",
  "brightlocal_keywords_path": "string",
  "local_audit_path": "string",
  "seo_insights_path": "string",
  "master_report_path": "string",
  "keywords_count": 100,
  "critical_issues_found": 3,
  "timestamp": "ISO-8601"
}
```

**Failure:**
```json
{
  "status": "failed",
  "error": "string",
  "partial_outputs": ["array of completed files"],
  "timestamp": "ISO-8601"
}
```

---

## ERROR HANDLING

**Missing adjacent cities:**
- Prompt user: "Please provide 3 nearby cities for keyword expansion (comma-separated):"
- Wait for input, validate (3 cities required)
- Re-prompt if invalid

**Invalid PDF/CSV:**
- Display error with file path and issue
- Re-prompt for correct file
- Max 3 attempts before HALT

**API failures:**
- Retry with exponential backoff (max 3 attempts)
- If persistent failure: Log error and continue with partial data
- Mark affected sections as "ANALYSIS INCOMPLETE - API ERROR"

---

## VERSION HISTORY

**1.0** - Initial release
- BrightLocal keyword generation (OpenAI GPT-4o)
- Local audit analysis (ChatGPT-4o with PDF)
- SEMrush insights (OpenAI o1 reasoning)
- Combined master report generation
