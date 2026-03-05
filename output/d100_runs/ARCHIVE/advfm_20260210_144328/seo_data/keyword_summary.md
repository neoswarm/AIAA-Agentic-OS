# BrightLocal Keyword Generation Summary

**Generated:** 2026-02-10
**Practice:** Advanced Functional Medicine
**Location:** San Diego, CA
**Model Used:** OpenAI GPT-4o
**Temperature:** 0.4
**Total Keywords:** 99

---

## Data Sources

### Input Data
- **Source:** `/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/output/d100_runs/advfm_20260210_144328/scrape_data/structured_data_v2.json`
- **Services Extracted:** 11 services
- **Conditions Extracted:** 17 conditions
- **Primary City:** San Diego
- **Adjacent Cities:** La Jolla, Del Mar, Encinitas

### Services Used
1. Comprehensive Lab Testing
2. Personalized Plan of Action
3. Functional Medicine
4. Female Health
5. Autoimmune Disorders
6. Hormone Replacement Therapy
7. Digestive Disorders
8. Thyroid Issues
9. Weight Loss
10. Diabetes
11. Fertility

### Conditions Used
1. Hormonal imbalances
2. Chronic fatigue
3. Digestive disorders
4. Metabolic dysfunction
5. Autoimmune disorders
6. Thyroid issues
7. High blood pressure
8. Diabetes
9. Weight loss challenges
10. Fertility issues
11. Headaches
12. GI issues
13. Anxiety
14. Inflammation
15. Osteoarthritis
16. Acid reflux
17. Asthma

---

## Keyword Distribution by Category

### 1. Core Services (11 keywords)
- Lines 1-11: Pure service terms without location modifiers

### 2. Core Conditions (13 keywords)
- Lines 12-24: Pure condition/treatment terms without location modifiers

### 3. "Near Me" Searches (10 keywords)
- Lines 25-34: Service-based "near me" searches

### 4. San Diego Primary (23 keywords)
- Lines 35-57: Services + conditions with "San Diego" modifier

### 5. La Jolla Adjacent (11 keywords)
- Lines 58-65, 82-84, 91-93: La Jolla location variations

### 6. Del Mar Adjacent (11 keywords)
- Lines 66-73, 85-87, 94-96: Del Mar location variations

### 7. Encinitas Adjacent (11 keywords)
- Lines 74-81, 88-90, 97-99: Encinitas location variations

### 8. Near Me + City Variations (9 keywords)
- Lines 91-99: "Near me [city]" combinations

---

## Keyword Quality Metrics

✓ **High Commercial Intent:** All keywords focus on services/treatments (not informational)
✓ **Local Intent:** 75+ keywords include geo-modifiers
✓ **Patient Focus:** Appointment/treatment intent language
✓ **No Duplicates:** Each keyword unique
✓ **No Brand Terms:** Practice name excluded
✓ **Natural Phrasing:** Real search phrases, not keyword stuffing
✓ **BrightLocal Ready:** Plain text, one per line, no formatting

---

## Example High-Value Keywords

**Service + Location:**
- functional medicine San Diego
- hormone replacement therapy San Diego
- digestive disorder specialist San Diego
- thyroid specialist San Diego

**Condition + Location:**
- autoimmune disorder treatment San Diego
- chronic fatigue treatment San Diego
- fertility issues San Diego
- diabetes management San Diego

**Near Me Variations:**
- functional medicine near me
- hormone therapy near me
- fertility clinic near me
- thyroid specialist near me

**Adjacent City Coverage:**
- functional medicine La Jolla
- hormone therapy Del Mar
- weight loss Encinitas

---

## Files Generated

1. **Keyword List (TXT):**
   `/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/output/d100_runs/advfm_20260210_144328/seo_data/brightlocal_keywords.txt`
   - Plain text format
   - Copy-paste ready for BrightLocal
   - 99 unique keywords

2. **Generation Script (Python):**
   `/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/output/d100_runs/advfm_20260210_144328/seo_data/generate_brightlocal_keywords.py`
   - Reusable script for future runs
   - Contains exact GPT-4o prompt
   - Can be modified for other practices

3. **Summary Document (Markdown):**
   `/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/output/d100_runs/advfm_20260210_144328/seo_data/keyword_summary.md`
   - This file
   - Breakdown and analysis

---

## Next Steps for BrightLocal Implementation

1. **Upload Keywords to BrightLocal:**
   - Log into BrightLocal account
   - Navigate to "Rank Tracking" or "Local Search Audit"
   - Copy all 99 keywords from `brightlocal_keywords.txt`
   - Paste into keyword import field

2. **Configure Location Settings:**
   - Primary location: San Diego, CA 92121
   - Additional locations (if tracking separately):
     - La Jolla, CA
     - Del Mar, CA
     - Encinitas, CA

3. **Set Tracking Frequency:**
   - Recommended: Weekly for all 99 keywords
   - Or: Daily for top 20-30 priority keywords

4. **Create Segments:**
   - Service-based keywords
   - Condition-based keywords
   - "Near me" searches
   - City-specific terms

5. **Monitor & Optimize:**
   - Track ranking changes
   - Identify quick wins (page 2 keywords)
   - Optimize for low-hanging fruit
   - Add new keywords based on performance

---

## Prompt Used (Exact GPT-4o Prompt)

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
[SERVICES]: Comprehensive Lab Testing, Personalized Plan of Action, Functional Medicine, Female Health, Autoimmune Disorders, Hormone Replacement Therapy, Digestive Disorders, Thyroid Issues, Weight Loss, Diabetes, Fertility
[CONDITIONS]: Hormonal imbalances, Chronic fatigue, Digestive disorders, Metabolic dysfunction, Autoimmune disorders, Thyroid issues, High blood pressure, Diabetes, Weight loss challenges, Fertility issues, Headaches, GI issues, Anxiety, Inflammation, Osteoarthritis, Acid reflux, Asthma
[CITY]: San Diego
[ADJACENT_CITIES]: La Jolla, Del Mar, Encinitas

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

---

## API Configuration

- **Model:** gpt-4o
- **Temperature:** 0.4 (balanced creativity/consistency)
- **Max Tokens:** 4000
- **API Key Source:** `.env` file (`OPENAI_API_KEY`)

---

**End of Summary**
