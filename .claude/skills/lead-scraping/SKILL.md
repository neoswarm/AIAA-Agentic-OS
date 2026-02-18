---
name: lead-scraping
description: Scrape B2B leads from Apify and Google Maps with filtering. Use when user asks to find leads, scrape contacts, build a lead list, or find prospects.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Lead Scraping

## Goal
Scrape B2B leads using Apify actors and Google Maps with comprehensive filtering for targeted prospecting.

## Prerequisites
- `APIFY_API_TOKEN` in `.env` (for Apify scraping)
- No API key needed for Google Maps scraping

## Execution Commands

```bash
# Apify B2B Lead Scraper (Actor ID: IoSHqwTR9YGhzccez)
python3 .claude/skills/lead-scraping/scrape_leads_apify.py \
  --fetch_count 50 \
  --contact_job_title "CEO" "Founder" \
  --contact_location "california, us" \
  --company_keywords "SaaS" \
  --seniority_level "founder" "c_suite" \
  --size "21-50" "51-100" \
  --min_revenue "1M" \
  --output_prefix "saas_founders"

# Google Maps Scraper (no API key needed)
python3 .claude/skills/google-maps-scraper/scrape_google_maps.py \
  --query "marketing agencies in Austin TX" \
  --max_results 100 \
  --output .tmp/gmaps_leads.csv
```

## Apify Scraper Filters
| Filter | Example Values |
|--------|----------------|
| `--contact_job_title` | "CEO" "Founder" "CTO" "VP Marketing" |
| `--contact_location` | "california, us", "united states", "germany" |
| `--contact_city` | "San Francisco", "New York" |
| `--company_keywords` | "SaaS" "marketing" "ecommerce" |
| `--seniority_level` | "founder" "c_suite" "director" "vp" |
| `--size` | "1-10" "11-20" "21-50" "51-100" "101-200" |
| `--min_revenue` | "1M" "5M" "10M" |
| `--fetch_count` | Number of leads to fetch (default: 50) |

## Process Steps
1. **Define ICP** - Clarify ideal customer profile with user
2. **Select Source** - Apify for B2B data, Google Maps for local businesses
3. **Configure Filters** - Set job titles, location, company size, revenue
4. **Execute Scrape** - Run the scraper script
5. **Validate Output** - Check lead quality, dedup, verify emails
6. **Export** - CSV output ready for cold email campaigns

## Quality Checklist
- [ ] ICP clearly defined before scraping
- [ ] Appropriate filters set for target audience
- [ ] Output includes name, email, company, title
- [ ] No duplicate leads
- [ ] Leads match target criteria
- [ ] Output saved to `.tmp/` as CSV

## Related Directives
- `directives/apify_lead_scraper.md`
- `directives/google_maps_scraper.md`
- `directives/build_lead_list.md`
