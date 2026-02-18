---
name: gmaps-leads
description: Generate B2B leads from Google Maps with deep contact enrichment via website scraping and Claude extraction. Use when user asks to scrape Google Maps leads, find local businesses, generate leads from Google Maps, or build a lead list from map data.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Google Maps Lead Generation Pipeline

## Goal
Scrape Google Maps for local businesses, enrich each by scraping their website and contact pages, use Claude to extract structured contact data (36 fields), and save everything to a persistent Google Sheet with deduplication.

## Prerequisites
- `APIFY_API_TOKEN` in `.env` (for Google Maps scraping)
- `ANTHROPIC_API_KEY` in `.env` (for Claude contact extraction)
- Google OAuth credentials (`credentials.json` + `token.json`)

## Execution Command

```bash
python3 .claude/skills/gmaps-leads/gmaps_lead_pipeline.py \
  --search "plumbers in Austin TX" \
  --limit 10
```

### Append to Existing Sheet

```bash
python3 .claude/skills/gmaps-leads/gmaps_lead_pipeline.py \
  --search "dentists in Miami FL" \
  --limit 25 \
  --sheet-url "https://docs.google.com/spreadsheets/d/..."
```

### Higher Volume

```bash
python3 .claude/skills/gmaps-leads/gmaps_lead_pipeline.py \
  --search "roofing contractors in Austin TX" \
  --limit 50 \
  --workers 5
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Google Maps Scrape** - Apify `compass/crawler-google-places` returns business listings
4. **Website Scraping** - Fetch main page + up to 5 prioritized contact pages per business
5. **Web Search Enrichment** - DuckDuckGo search for additional contact info
6. **Claude Extraction** - Claude Haiku extracts 36 structured fields from all gathered content
7. **Google Sheet Sync** - Append new leads with automatic deduplication by `lead_id`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--search` | Yes | Search query (e.g., "plumbers in Austin TX") |
| `--limit` | No | Max results to scrape (default: 10) |
| `--location` | No | Additional location filter |
| `--sheet-url` | No | Existing Google Sheet to append to |
| `--sheet-name` | No | Name for new sheet if creating |
| `--workers` | No | Parallel workers for enrichment (default: 3) |

## Quality Checklist
- [ ] Businesses match the search query and location
- [ ] Contact pages scraped (main + up to 5 contact pages)
- [ ] Emails and phone numbers extracted where available
- [ ] Owner/decision-maker info captured when found
- [ ] Social media profiles extracted
- [ ] Deduplication by lead_id prevents duplicate entries
- [ ] Cost under $0.025 per lead

## Related Directives
- `directives/gmaps_lead_generation.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_lead_generation_mastery.md`
- `skills/SKILL_BIBLE_b2b_lead_generation.md`
- `skills/SKILL_BIBLE_all_lead_gen_methods.md`
- `skills/SKILL_BIBLE_lead_list_building.md`
