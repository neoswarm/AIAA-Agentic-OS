---
name: linkedin-group-scraper
description: Extract member profiles from LinkedIn groups with filtering by title, company, and location. Use when user asks to scrape LinkedIn group members, extract group profiles, or get leads from LinkedIn groups.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# LinkedIn Group Scraper

## Goal
Extract member profiles from LinkedIn groups using Apify, with filtering by job title, company, and location for targeted outreach lists.

## Prerequisites
- `APIFY_API_TOKEN` in `.env` (for LinkedIn scraping)

## Execution Command

```bash
python3 .claude/skills/linkedin-group-scraper/scrape_linkedin_apify.py \
  --titles "CEO,Founder,VP Sales" \
  --industries "SaaS,Marketing Agency" \
  --locations "United States" \
  --max_items 500 \
  --output .tmp/linkedin_group_leads.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Define Target Criteria** - Specify job titles, industries, and locations
4. **Configure Apify Actor** - Set up LinkedIn scraper with filters and proxy settings
5. **Run Scraper** - Script executes Apify actor and waits for results
6. **Process Results** - Extract name, title, company, location, LinkedIn URL
7. **Export Leads** - Save structured lead data to JSON

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--titles` | Yes | Comma-separated job titles to target |
| `--industries` | No | Comma-separated industry filters |
| `--locations` | No | Comma-separated location filters (default: "United States") |
| `--company_size` | No | Company size filter (e.g., "11-50", "51-200") |
| `--max_items` | No | Maximum profiles to scrape (default: 100) |
| `--output` | No | Output path (default: `.tmp/linkedin_leads.json`) |

## Quality Checklist
- [ ] Apify token verified before running
- [ ] Job title filters match target ICP
- [ ] Results contain name, title, company, and LinkedIn URL
- [ ] No duplicate profiles in output
- [ ] Lead count matches expected volume

## Related Directives
- `directives/linkedin_group_scraper.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_b2b_lead_generation.md`
- `skills/SKILL_BIBLE_all_lead_gen_methods.md`
