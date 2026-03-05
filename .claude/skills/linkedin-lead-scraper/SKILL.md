---
name: linkedin-lead-scraper
description: Scrape LinkedIn profiles by job title, industry, and location using Apify, then enrich with emails. Use when user asks to scrape LinkedIn leads, find LinkedIn profiles, build a prospect list from LinkedIn, or generate B2B leads from LinkedIn.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# LinkedIn Lead Scraper + Email Finder

## Goal
Automate B2B lead generation by scraping LinkedIn profiles matching your ideal customer profile, then enriching with verified email addresses for cold outreach campaigns.

## Prerequisites
- `APIFY_API_TOKEN` in `.env` (for LinkedIn scraping)
- `HUNTER_API_KEY` or `APOLLO_API_KEY` in `.env` (for email enrichment)
- `GOOGLE_APPLICATION_CREDENTIALS` in project root (for Google Sheets export)

## Execution Command

```bash
python3 .claude/skills/linkedin-lead-scraper/scrape_linkedin_apify.py \
  --titles "CEO,Founder,VP Sales" \
  --industries "SaaS,Marketing Agency" \
  --locations "United States" \
  --company_size "11-50" \
  --max_items 500 \
  --output .tmp/linkedin_leads.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Define ICP** - Specify target job titles, industries, locations, company size
4. **Configure Apify Actor** - Set up LinkedIn profile search scraper with residential proxies
5. **Run Scraper** - Execute Apify actor and collect profile data
6. **Process Results** - Extract name, title, company, location, LinkedIn URL
7. **Enrich with Emails** - Use Hunter or Apollo to find verified business emails
8. **Export to Sheets** - Upload complete lead list to Google Sheets
9. **Deduplicate** - Remove duplicates before outreach

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--titles` | Yes | Comma-separated job titles (e.g., "CEO,Founder,VP Sales") |
| `--industries` | No | Comma-separated industries (e.g., "SaaS,Marketing Agency") |
| `--locations` | No | Comma-separated locations (default: "United States") |
| `--company_size` | No | Company size filter (e.g., "11-50", "51-200") |
| `--max_items` | No | Maximum profiles to scrape (default: 100) |
| `--output` | No | Output path (default: `.tmp/linkedin_leads.json`) |

## Quality Checklist
- [ ] ICP criteria clearly defined before scraping
- [ ] Apify token and credits verified
- [ ] Results contain full profile data (name, title, company, URL)
- [ ] Email enrichment rate above 40%
- [ ] Duplicates removed from final list
- [ ] Data exported to Google Sheets for team access

## Related Directives
- `directives/linkedin_lead_scraper.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_b2b_lead_generation.md`
- `skills/SKILL_BIBLE_all_lead_gen_methods.md`
- `skills/SKILL_BIBLE_cold_email_mastery.md`
