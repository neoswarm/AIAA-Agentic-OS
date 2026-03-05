# SKILL_D100_seo_analysis
## Purpose: Generate the Digital Health Report from raw SEMrush data
## Called by: Claude Code after Phase 1 of d100_v3_runner.py --phase1-only

---

## When to Use This Skill

Invoke this skill when:
- `d100_v3_runner.py --phase1-only` has completed for a site
- `semrush_data.json` exists in the run directory
- You need to generate the `seo_report.md` file before running Phase 2-4

---

## Input Files (read from run_dir)

| File | Purpose |
|---|---|
| `{run_dir}/semrush_data.json` | Full SEMrush API response — all numbers used verbatim |
| `{run_dir}/scrape_data/raw_scrape.md` | Website content for E-E-A-T context |
| `{run_dir}/crawl_data.json` | robots.txt AI status, llms.txt, sitemap |

---

## Output

Write the completed Digital Health Report to:
```
{run_dir}/seo_report.md
```

This file is then read by the runner in Phase 2 and injected verbatim into `gamma_content.digital_health_report`.

---

## Execution Steps

1. Read `semrush_data.json` — extract all fields
2. Read `raw_scrape.md` — skim for practice name, specialty, location, provider names
3. Read `crawl_data.json` — note AI crawler status and llms.txt
4. Generate the 7-section Digital Health Report using the template below
5. Write result to `seo_report.md` in the same run directory
6. Print confirmation: "✓ SEO report written: {run_dir}/seo_report.md"

---

## Report Template (EXACT FORMAT — follow precisely)

```
🔎 DIGITAL SEO HEALTH REPORT — {domain}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 DOMAIN SNAPSHOT
──────────────────
| Metric              | Value                         |
|---------------------|-------------------------------|
| Global Rank         | #{domain_rank:,}              |
| Keywords Ranked     | {unique_keywords:,}           |
| Monthly Traffic     | ~{estimated_traffic:,} visits |
| Traffic Value       | ${traffic_value:,}/mo         |
| Keywords in Top 10  | {pos1_3_count + pos4_10_count}|
| SERP Features Traffic| ~{serp_features_traffic:,}/mo |


🔑 THE CORE FINDING: [WRITE A TITLE IN CAPS — the single most striking insight]
──────────────────────────────────────────────────────
[Lead with the most striking number from position distribution.
 Example: "1,800 keywords ranked. Only 1,139 monthly visitors."]

Position Breakdown:
• Pos #1: {pos1_count} keywords (top-of-page, ~28% CTR)
• Pos #2-3: {pos2_3_count} keywords (~15% CTR)
• Pos #4-10: {pos4_10_count} keywords (page 1, ~3-8% CTR)  ← ACTION ZONE
• Pos #11-20: {pos11_20_count} keywords (page 2, <1% CTR)
• Pos #21+: ~{remainder} keywords (invisible)

[One sentence interpreting what this means for the practice — connect it to
 the gap between rankings and actual traffic.]

The CTR reality: Positions 1-3 capture 54% of all clicks. Position 4-10 gets 3-8%.
Moving {pos4_10_count} keywords from pos 4-10 to pos 1-3 could 6-8× their traffic contribution.


🤖 AI SEARCH GAP
──────────────────
[Include this section only if ai_overview_serp_count > 0]

• {ai_overview_serp_count} of your ranked keywords trigger Google AI Overviews on search results
• Your practice is cited in {ai_overview_cited_count} of those AI-generated answers
[If ai_overview_cited_count == 0:]
→ You're invisible in AI-powered search despite {ai_overview_serp_count} opportunities.
   Practices cited in AI Overviews receive 20-30% more qualified traffic from those searches.
[If ai_overview_cited_count > 0:]
→ You're cited in {ai_overview_cited_count} AI Overviews — build on this with deeper content.


🎯 BIGGEST OPPORTUNITY: [KEYWORD CLUSTER NAME IN CAPS]
──────────────────────────────────────────────────────
[Identify the single highest-value non-branded keyword cluster from top_by_volume.
 Look for: a theme with multiple keywords all ranking low (pos 8-20) but with strong volume.
 Example clusters: MTHFR, Functional Medicine, Weight Loss, TRT, PANS/PANDAS, Hormone Therapy]

Total cluster search volume: [X,XXX/mo]

[List top 5-7 keywords in this cluster in EXACT format:]
[pos X] keyword phrase — X,XXX/mo  KD:XX
[pos X] keyword phrase — X,XXX/mo  KD:XX
...

[One sentence: why do they have the authority but not the ranking?
 Example: "You treat MTHFR patients but your content doesn't match how patients search."]

Opportunity: Moving cluster from pos {avg_pos} → pos 3 = ~{estimated_traffic_gain:,} additional visits/mo


⚡ WITHIN STRIKING DISTANCE (pos 4-10)
──────────────────────────────────────
[List top 5-6 quick-win keywords — highest volume, pos 4-10. EXACT format:]
[pos X] keyword phrase — X,XXX searches/mo
[pos X] keyword phrase — X,XXX searches/mo
...

→ Highest priority: "[keyword]" at pos {best_pos} — {best_vol:,}/mo searches.
  [One sentence on why this is the best single quick win.]


🏆 VS YOUR TOP COMPETITOR
──────────────────────────
[Use competitor data. Show head-to-head:]

{competitor_domain}:
  Keywords: {comp_keywords:,}  |  Traffic: {comp_traffic:,}/mo  |  Value: ${comp_traffic_value:,}/mo
  Traffic efficiency: {comp_traffic/comp_keywords:.1f} visits per keyword

{practice_domain}:
  Keywords: {unique_keywords:,}  |  Traffic: {estimated_traffic:,}/mo  |  Value: ${traffic_value:,}/mo
  Traffic efficiency: {estimated_traffic/unique_keywords:.1f} visits per keyword

[One punchy conclusion. Examples:
 "They have 4× fewer keywords but the same traffic — their content is doing more work."
 "You have 2× more keywords but 40% less traffic — a content optimization problem, not a volume problem."]


🎯 3-PRIORITY ATTACK PLAN
──────────────────────────
[Ground every item in actual numbers from above. Be specific, not generic.]

1. [PRIORITY NAME IN CAPS]
   [One-line tactic tied to a specific finding above]
   Target: [Specific measurable outcome] within [Realistic timeframe]

2. [PRIORITY NAME IN CAPS]
   [One-line tactic tied to a specific finding above]
   Target: [Specific measurable outcome] within [Realistic timeframe]

3. [PRIORITY NAME IN CAPS]
   [One-line tactic tied to a specific finding above]
   Target: [Specific measurable outcome] within [Realistic timeframe]
```

---

## Rules

1. **Use every number verbatim from semrush_data.json** — never estimate, round, or fabricate
2. **Doctor's report tone** — confident, analytical, plain English. Not SEO jargon.
3. **One cluster only** in Section 4 — the highest-value, most actionable one
4. **Competitor section** — only include if `competitors` array is non-empty; if empty, skip the section
5. **AI search gap section** — include only if `ai_overview_serp_count > 0`; if N/A or 0, omit
6. **No padding** — if a number isn't available (CSV fallback mode), say "data not available" and skip that line
7. **Length target** — 400-600 words total. Dense, not fluffy.

---

## Example Quick Wins Section (for reference)

```
⚡ WITHIN STRIKING DISTANCE (pos 4-10)
──────────────────────────────────────
[pos 5] functional medicine doctor near me — 2,400 searches/mo
[pos 7] mthfr specialist — 1,900 searches/mo
[pos 6] integrative medicine pittsburgh — 880 searches/mo
[pos 9] hormone therapy for women — 720 searches/mo
[pos 8] gut health doctor — 590 searches/mo

→ Highest priority: "functional medicine doctor near me" at pos 5 — 2,400/mo searches.
  One 300-word page update focused on this exact phrase could move it to pos 1-3 within 90 days.
```

---

## After Writing seo_report.md

Print the following to confirm next steps:
```
✓ SEO report written: {run_dir}/seo_report.md

To complete the D100 run:
  python3 scripts/d100_v3_runner.py \
    --csv <your_csv> \
    --site-index <N> \
    --run-dir {run_dir} \
    --seo-report {run_dir}/seo_report.md
```
