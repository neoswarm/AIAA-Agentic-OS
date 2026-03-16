# Topical Map Generator
## Version: 1.0 | Updated: 2026-03-12

Build a complete SEO topical authority map for any niche — pillars, clusters, articles, tools,
editorial content, programmatic SEO patterns, internal linking blueprint, and a phased
publishing calendar. Uses real DataForSEO keyword data. Outputs in 4 formats.

---

## What It Does

1. Researches ~100+ real keywords via DataForSEO API (volumes, KD, intent)
2. Optionally analyzes a competitor domain's ranking keywords
3. Generates a comprehensive topical map via Claude Opus (8 sections, not the basic 4)
4. Outputs 4 files: CSV (Google Sheets), JSON (machine-readable), Markdown (writer briefs), HTML (visual mindmap)
5. Includes a built-in post-generation action plan explaining exactly what to do next

**Core Philosophy:** Topic drives the keyword — never the other way around.
Build topical authority first; keyword rankings are the outcome, not the goal.

---

## Prerequisites

Required API keys in `.env`:
- `ANTHROPIC_API_KEY` — Claude Opus for map generation
- `DATAFORSEO_LOGIN` — mike@healthbizscale.com
- `DATAFORSEO_PASSWORD` — 58147dd55fb95d93

---

## How to Run

**IMPORTANT — Two-Stage Flow (when running inside Claude Code):**
Since Claude Code IS Claude, we skip the external API call and generate the topical map natively.

```bash
# ── STAGE 1: Keyword Research (DataForSEO only) ───────────────────────────────
python3 execution/topical_map.py \
  --topic "Work-Life Balance" \
  --audience "Remote workers and managers" \
  --goal "Newsletter signups + online course sales" \
  --phase1-only
# → Saves keyword_data.json to output dir
# → Prints the full prompt for Claude Code to use natively
# → Claude Code generates topical_map.json and saves to the same output dir

# ── STAGE 2: Generate Formatted Outputs (after JSON is saved) ─────────────────
python3 execution/topical_map.py --from-json output/topical_maps/{slug}_{timestamp}/topical_map.json
# → Writes CSV, Markdown, HTML to the SAME dir as the JSON

# ── WITH COMPETITOR ANALYSIS ──────────────────────────────────────────────────
python3 execution/topical_map.py \
  --topic "Functional Medicine" \
  --audience "Health-conscious adults 35-55" \
  --goal "Patient consultations" \
  --competitor "functionalmedicine.org" \
  --phase1-only

# ── WITH EXISTING URLs TO RESTRUCTURE ────────────────────────────────────────
python3 execution/topical_map.py \
  --topic "Porto Travel Guide" \
  --audience "Independent travelers" \
  --goal "Affiliate tour commissions" \
  --urls existing_urls.txt \
  --phase1-only

# ── REFRESH KEYWORD DATA (quarterly enrichment) ──────────────────────────────
python3 execution/topical_map.py --enrich path/to/topical_map.json
```

---

## Inputs

| Argument | Required | Description |
|----------|----------|-------------|
| `--topic` | Yes* | Broad topic (e.g., "Work-Life Balance", "CBD Oil", "Porto Travel Guide") |
| `--audience` | Yes* | Who the content is for |
| `--goal` | Yes* | What the content should convert to (sales, signups, bookings, etc.) |
| `--competitor` | No | Competitor domain (e.g., competitor.com) — triggers gap analysis |
| `--urls` | No | Path to .txt file with one existing URL per line — triggers restructuring mode |
| `--location` | No | Target country for keyword data (default: "United States") |
| `--from-json` | No* | Skip research + generation; regenerate output files from existing JSON |
| `--enrich` | No* | Refresh DataForSEO keyword data on an existing topical_map.json |
| `--output-dir` | No | Custom output directory (default: output/topical_maps/{slug}_{timestamp}) |

*Required unless `--from-json` or `--enrich` is used

---

## Process

### Phase 1: Keyword Research (DataForSEO)
1. Call `related_keywords` API with the seed topic → ~100 related keywords with volume + KD
2. If `--competitor`: Call `ranked_keywords` API for competitor domain → top 100 ranking keywords
3. Extract top 50 keywords sorted by volume for injection into prompt
4. Identify intent signals (informational / commercial / transactional) from DataForSEO

### Phase 2: Map Generation (Claude Code Native — Zero Cost)
1. Script prints the full system prompt + user prompt to terminal (from `--phase1-only` output)
2. Claude Code generates the complete topical map JSON natively (no external API call)
3. Claude Code saves JSON directly to the output dir as `topical_map.json`
4. Validate: minimum 7 pillars, minimum 3 clusters per pillar

### Phase 3: Output Generation (4 Formats)
1. **JSON** — Full structured data (source of truth for updates)
2. **CSV** — Multi-section flat file, Google Sheets compatible
3. **Markdown** — Per-pillar writer briefs with meta title options + related keywords
4. **HTML** — Interactive collapsible mindmap, open in any browser

### Phase 4: Summary
Print run summary to terminal with output directory path and key metrics.

---

## Output Files

```
output/topical_maps/{topic-slug}_{YYYYMMDD_HHMMSS}/
├── topical_map.json       ← Source of truth — use for updates and enrichment
├── topical_map.csv        ← Import to Google Sheets (File > Import > Upload)
├── topical_map.md         ← Writer briefs, one per pillar
└── topical_map.html       ← Open in browser — visual interactive mindmap
```

---

## 8 Output Sections (vs 4 in the basic prompt)

| # | Section | What's Inside |
|---|---------|---------------|
| 1 | **Main Pillar Structure** | 7-12 pillars (info + commercial), funnel stage, intent, URL slug, keyword, volume, KD |
| 2 | **Content Clusters** | 4-7 clusters per pillar, each with 3-5 articles |
| 3 | **Tools & Free Resources** | 3-5 tools (calculators, templates, generators) with conversion potential score |
| 4 | **Editorial Content** | 4-6 thought leadership pieces with angle, persona, social hook |
| 5 | **Programmatic SEO** | 8-12 patterns with variables, page count estimates, difficulty score |
| 6 | **Internal Linking Blueprint** | 15-25 explicit source→target relationships with anchor text |
| 7 | **Publishing Calendar** | 4 phases: Quick Wins → Authority Builders → Programmatic Scale → Editorial Leadership |
| 8 | **Conversion Path Map** | Every pillar/cluster mapped to its CTA and commercial destination |
| + | **Competitor Gaps** | (If `--competitor` used) Opportunities + blue ocean topics |
| + | **Action Plan** | Immediate next steps, validation checklist, launch sequence |

---

## Post-Generation Workflow

### Step 1: Import CSV to Google Sheets
1. Go to `sheets.new`
2. File → Import → Upload → select `topical_map.csv`
3. Accept "Convert to table" prompt → easier to filter and sort
4. Rename the sheet to your topic

### Step 2: Validate the Map
- Review all pillars — do they match your business/conversion goals?
- Check pillar keyword volumes — are they substantial for your niche? (generally >500/mo)
- Open the HTML mindmap (`topical_map.html`) in a browser for visual review
- Cross-check 10-15 pillar keywords manually in DataForSEO or SEMrush
- Check SERPs for pillar keywords — do top 10 results match your intended content type?
- Replace any keywords with mismatched intent

### Step 3: Prioritize with Phase 1 Quick Wins
- In the CSV, filter "Publishing Calendar" section → Phase 1 rows
- These are high-volume, low-KD, bottom-funnel — fastest ROI
- Target: publish 3-5 Phase 1 articles before touching Phase 2
- Phase 1 = revenue first, authority second

### Step 4: Set Up Content Operations
- In the CSV Editorial Calendar section, add writer names to "Responsible" column
- Set deadlines based on Phase 1 priority
- For each article, generate a writer brief from `topical_map.md` (one section per pillar)
- Writer briefs include: H1 options, meta title options, related keywords, internal link targets

### Step 5: Build the URL Structure
- Use the `url_slug` field from JSON/CSV for every page
- Default rule: `site.com/keyword` (root URLs) unless programmatic scale requires folders
- If restructuring existing site: map old URLs to new slugs, set 301 redirects

### Step 6: Publish with Internal Links
- Use the "Internal Linking Blueprint" section in the CSV
- When publishing each article, add the links listed in that section
- Highest priority: links from homepage or category pages (they pass the most authority)
- Add contextual internal links within the body copy — NOT sidebar widgets

### Step 7: Build Conversion Paths
- Follow the "Conversion Paths" section in the CSV
- Every editorial cluster must funnel into a commercial page via CTA
- Deploy products/commercial pages FIRST (Prague strategy), then editorial

### Step 8: Monitor and Iterate
- After 30-60 days: check Google Search Console impressions on pillar keywords
- Getting impressions but not clicks → optimize meta titles (H1 ≠ Meta Title)
- Ranking page 2-3 → strengthen internal links + publish more supporting cluster articles
- No impressions after 60 days → check indexation, add manual signals (newsletter, PPC, social)

---

## Updating the Topical Map

### Option A: Update in Chat (Claude-Assisted)
1. Open `topical_map.json` in a text editor, copy contents
2. Paste into Claude chat: "Here is my topical map JSON: [paste]. Add a new pillar for [topic] targeting [audience goal]"
3. Claude edits the JSON — copy the updated version, save as new `topical_map.json`
4. Regenerate outputs: `python3 execution/topical_map.py --from-json topical_map.json`

### Option B: Update in Google Sheets (Offline)
1. Edit the CSV directly in Google Sheets — add/remove rows, change keywords
2. Export as CSV (File → Download → CSV)
3. Regenerate JSON + Markdown: `python3 execution/topical_map.py --from-csv updated.csv`

### Option C: Quarterly Keyword Enrichment
Re-fetch fresh DataForSEO data for all keywords in an existing map:
```bash
python3 execution/topical_map.py --enrich output/topical_maps/work-life-balance_20260312_150000/topical_map.json
```
Creates a new timestamped run dir with refreshed volumes + KD scores.

### When to Update the Map
- New product/service launched → add commercial pillar
- Keyword volumes shift significantly (quarterly check)
- New competitor enters the space → re-run competitor gap analysis
- Existing pillar hits page 1 → expand its cluster depth
- Search intent shifts (Google updates, AI search changes)

---

## Quality Gates

- [ ] Minimum 7 pillars generated
- [ ] Each pillar has at least 3 clusters
- [ ] All 4 publishing phases have content
- [ ] Conversion paths exist for every commercial pillar
- [ ] Internal linking blueprint has 15+ relationships
- [ ] CSV imports cleanly to Google Sheets (no merge errors)
- [ ] JSON is valid (no parse errors)
- [ ] HTML mindmap opens and renders in browser

---

## Edge Cases

- **DataForSEO returns no results** → Script falls back to Claude-estimated volumes, adds `"estimated": true` flag to affected keywords
- **Competitor domain not found** → Logs warning, skips competitor section, continues with rest of map
- **JSON response truncated** → Script detects incomplete JSON, retries with prompt asking for fewer pillars
- **Very niche topic with low search volume** → Volumes will be lower; map is still valid; note this is a "depth-first" strategy not a "breadth-first" strategy
- **Existing URLs file not found** → Logs error, asks user to check file path, exits cleanly

---

## Related Directives
- `company_market_research.md` — Use to research competitor before running topical map
- `content_brief_generator.md` — Generate full writer briefs from the topical map output
- D100 workflow — Topical map output can feed into D100 content briefs

---

## Version History

**1.1** — 2026-03-12
- Added `--phase1-only` mode: DataForSEO research only, prints prompt for Claude Code native generation
- Fixed `--from-json` to write outputs to the same dir as source JSON (not a new timestamped dir)
- Eliminated external Claude API calls — Claude Code generates map natively (zero API cost)
- Two-stage flow now matches D100 pattern (data collection → native generation → format outputs)

**1.0** — 2026-03-12
- Initial release
- DataForSEO integration (related_keywords + ranked_keywords APIs)
- 8-section topical map (vs 4 in basic prompt)
- 4 output formats: CSV, JSON, Markdown, HTML
- 3 update modes: --from-json, --from-csv (future), --enrich
- Built-in post-generation action plan
