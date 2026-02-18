---
name: google-maps-scraper
description: Scrape local business listings from Google Maps with filters for category, location, and rating. Use when user asks to scrape Google Maps, find businesses on Google Maps, extract local business data, or build a business list by location.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Google Maps Business Scraper

## Goal
Scrape local business listings from Google Maps by category and location, extract business data (name, address, phone, website, rating, reviews), optionally enrich with emails, and export to Google Sheets.

## Prerequisites
- `APIFY_API_TOKEN` in `.env` (for Google Maps scraping)
- Google OAuth credentials (`credentials.json`) for Sheets export
- `HUNTER_API_KEY` in `.env` (optional, for email enrichment)

## Execution Command

```bash
python3 .claude/skills/google-maps-scraper/scrape_google_maps.py \
  --query "Plumbers in Miami, FL" \
  --max_items 25 \
  --min_rating 4.0 \
  --output .tmp/gmaps_leads.json
```

### Full Pipeline (Scrape + Emails + Sheet)

```bash
python3 .claude/skills/google-maps-scraper/scrape_google_maps.py \
  --query "Dentists in Austin, TX" \
  --max_items 500 && \
python3 .claude/skills/google-maps-scraper/scrape_google_maps.py \
  --query "Dentists Austin" --output .tmp/gmaps_leads.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Define Search** - Set business category, location, and optional filters
3. **Test Scrape** - Run with 25 results to verify data quality
4. **Full Scrape** - Run complete scrape with all filters applied
5. **Email Extraction** - Optionally scrape emails from business websites
6. **Email Enrichment** - Optionally enrich via Hunter.io API
7. **Export to Sheet** - Push results to Google Sheets

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--query` | Yes | Search query (e.g., "Plumbers in Miami, FL") |
| `--max_items` | No | Maximum businesses to scrape (default varies) |
| `--min_rating` | No | Minimum Google rating filter (e.g., 4.0) |
| `--output` | No | Output file path (default: .tmp/gmaps_leads.json) |
| `--location` | No | Additional location filter |

## Quality Checklist
- [ ] Results match the specified business category
- [ ] Location accuracy verified
- [ ] Business data includes name, address, phone, website
- [ ] Rating and review count captured
- [ ] Duplicates removed by phone number
- [ ] Cost ~$0.01 per business

## Related Directives
- `directives/google_maps_scraper.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_lead_generation_mastery.md`
- `skills/SKILL_BIBLE_lead_list_building.md`
- `skills/SKILL_BIBLE_all_lead_gen_methods.md`
