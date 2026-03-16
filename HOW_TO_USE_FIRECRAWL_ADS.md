# 🔥 How to Use Firecrawl with Google Ads Builder

## What This Does

The enhanced Google Ads builder (`build_google_ads_gemini_firecrawl.py`) combines:
1. **Your existing D100 Ads Builder** - Generates high-converting Google Ads campaigns
2. **Firecrawl Keyword Research** - Fetches REAL search volume, CPC, and competition data
3. **"Keywords That Print Money" section** - Appends detailed keyword analysis with actual 2026 data

---

## Prerequisites

### 1. Install Firecrawl CLI
```bash
sudo npm install -g firecrawl-cli
```

### 2. Authenticate Firecrawl
```bash
firecrawl login --browser
```
This opens your browser to authenticate.

### 3. Verify It's Working
```bash
firecrawl --status
```

You should see:
```
🔥 firecrawl cli v1.0.2
● Authenticated via FIRECRAWL_API_KEY
Credits: 500,000 remaining
```

---

## Usage

### Basic Command
```bash
python3 execution/build_google_ads_gemini_firecrawl.py \
  --data-file "output/d100_runs/advfm_20260210_144328/structured_data_v2.json" \
  --primary-offer "Functional Medicine Program" \
  --annual-value 5000 \
  --primary-city "San Diego" \
  --keywords "functional medicine san diego,autoimmune disorder treatment,thyroid specialist near me,comprehensive lab testing,functional medicine telehealth" \
  --output-dir "output/d100_runs/advfm_20260210_144328/ads/"
```

### Arguments Explained

| Argument | Description | Example |
|----------|-------------|---------|
| `--data-file` | Path to your scraped practice data JSON | `output/d100_runs/advfm_20260210_144328/structured_data_v2.json` |
| `--primary-offer` | Main service/program name | `"Functional Medicine Program"` |
| `--annual-value` | Lifetime/annual value per patient | `5000` |
| `--primary-city` | Main city for geo-targeting | `"San Diego"` |
| `--keywords` | Comma-separated keywords (max 5) | `"keyword1,keyword2,keyword3"` |
| `--output-dir` | Where to save the output | `output/d100_runs/advfm_20260210_144328/ads/` |
| `--skip-firecrawl` | (Optional) Skip Firecrawl, use defaults | Add flag to skip |

---

## What Happens Step-by-Step

### Phase 1: Firecrawl Keyword Research (5-10 min)
```
🔥 FIRECRAWL KEYWORD RESEARCH
======================================================================

📊 Researching: functional medicine san diego
   ✅ Data saved to: .firecrawl/keyword_functional_medicine_san_diego.json

📊 Researching: autoimmune disorder treatment
   ✅ Data saved to: .firecrawl/keyword_autoimmune_disorder_treatment.json

📊 Researching: thyroid specialist near me
   ✅ Data saved to: .firecrawl/keyword_thyroid_specialist_near_me.json
```

For each keyword, Firecrawl:
- Searches Google for `"{keyword} search volume CPC cost per click Google Ads 2026 data"`
- Scrapes top 10 results
- Extracts CPC estimates, search volume, competition level
- Saves raw data to `.firecrawl/` folder

### Phase 2: Generate Google Ads Campaigns
```
🤖 Generating Google Ads campaigns...
🚀 Using model: anthropic/claude-opus-4...
```

Uses your existing prompt to create:
- 3 Campaign structure (Medical Mystery Solver, Condition Remission, Virtual Authority)
- Headlines, descriptions, sitelinks, callouts
- Keyword targeting strategy

### Phase 3: Append Keyword Research Data
```
💰 Adding keyword research data...
```

Adds a "Keywords That Print Money" section with REAL data:

```markdown
## 💰 The Google Ad Keywords That Print Money
### For Advanced Functional Medicine - With REAL 2026 Data

**Top 5 Must-Own:**
**Bid Strategy:** Exact Match ONLY (Control the spend).

### 1. **[functional medicine san diego]**

**💵 INVESTMENT:** $4.50 per click
**📊 SEARCH VOLUME:** 12,000 monthly searches
**🎯 COMPETITION:** High

**WHY THIS PRINTS MONEY:**
- High commercial intent keyword in healthcare vertical
- Attracts qualified leads ready for high-ticket programs
- Competition validates market demand
```

### Phase 4: Save Output
```
💾 Saving generated ads...
📄 Output saved to: output/d100_runs/advfm_20260210_144328/ads/google_ads_campaigns_advanced_functional_medicine_20260211_182530_firecrawl.md
```

---

## Output Files

### Main Output
```
google_ads_campaigns_{company_name}_{timestamp}_firecrawl.md
```
Contains:
- Full Google Ads campaign structure
- Keywords That Print Money section with REAL data
- Data sources and benchmarks

### Firecrawl Research Data
```
.firecrawl/
  keyword_functional_medicine_san_diego.json
  keyword_autoimmune_disorder_treatment.json
  keyword_thyroid_specialist_near_me.json
  ...
```
Contains raw Firecrawl search results for each keyword.

---

## Example: Full Advanced Functional Medicine Run

```bash
cd "/Users/neo/Documents/Claude Code/AIAA-Agentic-OS"

python3 execution/build_google_ads_gemini_firecrawl.py \
  --data-file "output/d100_runs/advfm_20260210_144328/structured_data_v2.json" \
  --primary-offer "Functional Medicine Program" \
  --annual-value 5000 \
  --primary-city "San Diego" \
  --keywords "functional medicine san diego,autoimmune disorder treatment,thyroid specialist near me,comprehensive lab testing,functional medicine telehealth" \
  --output-dir "output/d100_runs/advfm_20260210_144328/ads/"
```

**Expected runtime:** 5-8 minutes (Firecrawl takes 1-2 min per keyword)

---

## Troubleshooting

### Error: `command not found: firecrawl`
**Fix:**
```bash
sudo npm install -g firecrawl-cli
```

### Error: `Not authenticated`
**Fix:**
```bash
firecrawl login --browser
```

### Error: `OPENROUTER_API_KEY not found`
**Fix:**
Add to `.env`:
```
OPENROUTER_API_KEY=your_key_here
```

### Want to skip Firecrawl and use defaults?
```bash
python3 execution/build_google_ads_gemini_firecrawl.py \
  --data-file "..." \
  --primary-offer "..." \
  --annual-value 5000 \
  --primary-city "..." \
  --keywords "..." \
  --output-dir "..." \
  --skip-firecrawl
```

---

## What Makes This Different?

### ❌ **Old Way (No Firecrawl):**
```
Top 5 Keywords:
1. [functional medicine san diego]
   Why: High intent local search
```
No data. Just guessing.

### ✅ **New Way (With Firecrawl):**
```
### 1. **[functional medicine san diego]**

**💵 INVESTMENT:** $4.50 per click
**📊 SEARCH VOLUME:** 12,000 monthly searches
**🎯 COMPETITION:** High

**WHY THIS PRINTS MONEY:**
- High commercial intent keyword in healthcare vertical
- Attracts qualified leads ready for high-ticket programs
- Competition validates market demand
```
REAL data. Actionable insights. Doctor-friendly.

---

## Integration with D100 Orchestrator

To add this to your main D100 workflow, update `d100_run.py`:

```python
# After scraping step, before email generation
if run_ads:
    print("\n🔥 Generating Google Ads with Firecrawl research...")
    ads_cmd = [
        "python3", "execution/build_google_ads_gemini_firecrawl.py",
        "--data-file", structured_data_file,
        "--primary-offer", primary_offer,
        "--annual-value", str(annual_value),
        "--primary-city", primary_city,
        "--keywords", ",".join(keywords),
        "--output-dir", ads_output_dir
    ]
    subprocess.run(ads_cmd, check=True)
```

---

## Next Steps

1. ✅ Run the script for Advanced Functional Medicine
2. ✅ Review the output with REAL keyword data
3. ✅ Share with client (doctors love seeing actual numbers)
4. ✅ Use keyword data to inform budget allocation
5. ✅ Update D100 orchestrator to include Firecrawl by default

---

**Created:** February 11, 2026
**AIAA Agentic OS - Dream 100 Workflow**
