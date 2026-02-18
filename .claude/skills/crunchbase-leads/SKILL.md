---
name: crunchbase-leads
description: Find recently funded startups from Crunchbase by industry, funding stage, and location. Use when user asks to find funded companies, search Crunchbase, find startups by funding, or generate leads from funding data.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Crunchbase Startup Lead Finder

## Goal
Search for recently funded startups based on industry, funding stage, location, and employee count, then output structured lead data for sales outreach.

## Prerequisites
- `PERPLEXITY_API_KEY` in `.env` (for search-based discovery)

## Execution Command

```bash
python3 .claude/skills/crunchbase-leads/scrape_crunchbase.py \
  --industry "saas" \
  --funding "series_a" \
  --location "san francisco" \
  --output .tmp/crunchbase_leads.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Define Search Criteria** - Gather industry, funding stage, location, and employee count filters
3. **Run Search** - Execute `.claude/skills/crunchbase-leads/scrape_crunchbase.py` to find matching companies via Perplexity
4. **Review Results** - Check output JSON for company names, funding amounts, descriptions
5. **Enrich Contacts** - Optionally run `enrich_contacts.py` on the output
6. **Export** - Optionally push to Google Sheets with `update_sheet.py`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--industry` / `-i` | Yes | Target industry (e.g., "saas", "fintech", "healthtech") |
| `--funding` / `-f` | No | Funding stage filter (e.g., "series_a", "seed") |
| `--location` / `-l` | No | Geographic filter (e.g., "san francisco", "new york") |
| `--employees` / `-e` | No | Employee count range (e.g., "10-50", "100+") |
| `--output` / `-o` | No | Output file path (default: .tmp/crunchbase_leads.json) |

## Quality Checklist
- [ ] Results include company name, website, funding amount, and description
- [ ] Results match specified industry and funding stage
- [ ] Output JSON is valid and well-structured
- [ ] At least 5 companies returned per search

## Related Directives
- `directives/crunchbase_lead_finder.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_lead_generation_mastery.md`
- `skills/SKILL_BIBLE_b2b_lead_generation.md`
- `skills/SKILL_BIBLE_lead_list_building.md`
