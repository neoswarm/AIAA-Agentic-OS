---
name: upwork-scraper
description: Scrape Upwork jobs and generate AI-personalized proposals. Use when user asks to find Upwork jobs, scrape freelance listings, generate Upwork proposals, or apply to Upwork gigs.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Upwork Job Scraper & Proposal Generator

## Goal
Scrape Upwork jobs matching AI/automation keywords using Apify, generate AI-personalized cover letters and proposals with Claude Opus, discover contact names, and output everything to a Google Sheet with one-click apply links.

## Prerequisites
- `APIFY_API_TOKEN` - For Upwork job scraping (free tier)
- `OPENROUTER_API_KEY` - For Claude Opus cover letter and proposal generation
- `GOOGLE_APPLICATION_CREDENTIALS` - For Google Sheets and Docs output
- Google OAuth configured (`client_secrets.json`)

## Execution Command

```bash
# Step 1: Scrape jobs
python3 .claude/skills/upwork-scraper/upwork_apify_scraper.py \
  --limit 50 \
  --days 1 \
  --verified-payment \
  -o .tmp/upwork_jobs_batch.json

# Step 2: Generate proposals and upload to Sheet
python3 .claude/skills/upwork-scraper/upwork_apify_scraper.py \
  --input .tmp/upwork_jobs_batch.json \
  --workers 5 \
  --output .tmp/upwork_jobs_with_proposals.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Scrape Jobs** - Run Apify scraper with keyword and date filters
3. **Filter Results** - Post-filter by budget, experience, verified payment
4. **Generate Proposals** - AI creates personalized cover letters + proposal Google Docs
5. **Output to Sheet** - Upload all data with apply links to Google Sheets

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--limit` | No | Max jobs to fetch (default: 50) |
| `--days` | No | Only jobs from last N days (default: 1) |
| `--keyword` | No | Specific keyword filter |
| `--verified-payment` | No | Only clients with verified payment |
| `--min-fixed` | No | Minimum fixed-price budget |
| `--min-hourly` | No | Minimum hourly rate |
| `--experience` | No | Experience levels: entry, intermediate, expert |
| `--workers` | No | Parallel AI calls (default: 5) |
| `-o` | No | Output file path |

## Quality Checklist
- [ ] Jobs scraped successfully from Apify
- [ ] Post-filters applied correctly
- [ ] Cover letters under 35 words (above-the-fold)
- [ ] Proposals written in conversational first-person tone
- [ ] Contact name discovery attempted for each job
- [ ] Google Sheet created with all columns (Apply Link, Cover Letter, Proposal Doc)
- [ ] Proposal Google Docs created with retry/backoff

## Related Directives
- `directives/upwork_scrape_apply.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_freelance_proposal_writing.md`
- `skills/SKILL_BIBLE_upwork_success.md`
