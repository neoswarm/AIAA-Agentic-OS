---
name: serp-scraper
description: Scrape Google search results to extract business leads with contact info and confidence scores. Use when user asks to scrape Google search results, find leads from SERP, extract contacts from search results, or build leads from Google organic results.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Google SERP Lead Scraper

## Goal
Scrape Google search results for local businesses, fetch their websites, extract 100+ contact fields using GPT with confidence scores, and store structured leads in Google Sheets with outreach icebreakers.

## Prerequisites
- `APIFY_API_TOKEN` or `SERP_API_KEY` or `VALUESERP_API_KEY` in `.env`
- `OPENAI_API_KEY` in `.env` (for GPT contact extraction)
- Google OAuth credentials (`credentials.json`) for Sheets output

## Execution Command

```bash
python3 .claude/skills/serp-scraper/scrape_serp.py \
  --query "marketing agencies in Austin" \
  --num_results 50 \
  --output .tmp/serp_leads.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Define Search Query** - Set target query, location, and result count
3. **Google Search** - Search via SerpAPI, ValueSERP, or Apify actor
4. **Fetch Websites** - Retrieve each result URL and convert to markdown
5. **GPT Extraction** - Extract 100+ fields per lead including emails, phones, social profiles
6. **Confidence Scoring** - Tier scores from 1.0 (schema.org) down to 0.4 (heuristic)
7. **Icebreaker Generation** - Pre-formatted outreach opener per lead
8. **Google Sheets Output** - Append to tracking sheet

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--query` | Yes | Search query (e.g., "marketing agencies in Austin") |
| `--num_results` | No | Number of results to fetch (default: 50) |
| `--output` | No | Output file path (default: .tmp/serp_leads.json) |

## Quality Checklist
- [ ] Search results match the target query
- [ ] Organic and local results both captured
- [ ] Contact fields extracted with confidence scores
- [ ] Best email and phone recommended per lead
- [ ] Icebreaker line generated for outreach
- [ ] Fields below 0.6 confidence flagged for review

## Related Directives
- `directives/google_serp_lead_scraper.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_lead_generation_mastery.md`
- `skills/SKILL_BIBLE_lead_list_building.md`
- `skills/SKILL_BIBLE_b2b_lead_generation.md`
