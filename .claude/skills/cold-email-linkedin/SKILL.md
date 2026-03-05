---
name: cold-email-linkedin
description: End-to-end cold email campaign with LinkedIn post-based personalization. Use when user asks to create a cold email campaign with LinkedIn personalization, scrape leads and personalize, or build an Instantly campaign with icebreakers.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Cold Email Campaign with LinkedIn Personalization

## Goal
Run end-to-end cold email campaigns: scrape leads from target industry/location via Apify, scrape actual LinkedIn posts for each lead, generate truly personalized first lines based on real post content, and create campaigns in Instantly.

## Prerequisites
- `APIFY_API_TOKEN` in `.env` (for lead and LinkedIn scraping)
- `INSTANTLY_API_KEY` in `.env` (for campaign creation and upload)
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env` (for personalization)

## Execution Command

```bash
python3 .claude/skills/cold-email-linkedin/cold_email_pipeline.py \
  --industry "SaaS" \
  --location "california, us" \
  --city "San Francisco" \
  --job_titles "CEO" "Founder" \
  --seniority "founder" "c_suite" \
  --sizes "21-50" "51-100" "101-200" \
  --min_revenue "1M" \
  --limit 25 \
  --campaign_name "SF SaaS Founders - Jan 2026"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Verify API Keys** - Check APIFY_API_TOKEN, INSTANTLY_API_KEY, and LLM key
4. **Scrape Leads** - Use Apify Apollo-style actor to find leads matching ICP filters
5. **Scrape LinkedIn Posts** - Fetch recent posts from each lead's LinkedIn profile
6. **Generate First Lines** - AI writes personalized icebreakers referencing specific post content
7. **Create Instantly Campaign** - Set up campaign with proper email template variables
8. **Upload Leads** - Push personalized leads to Instantly with variable mapping
9. **Save Output** - Raw leads, personalized leads saved to `.tmp/leads/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--industry` | Yes | Target industry (e.g., "SaaS") |
| `--location` | Yes | State/country format for Apify (e.g., "california, us") |
| `--city` | No | City-level filter (e.g., "San Francisco") |
| `--job_titles` | No | Target job titles (multiple allowed) |
| `--seniority` | No | Seniority levels: founder, c_suite, vp, director, etc. |
| `--sizes` | No | Company size ranges: "21-50", "51-100", etc. |
| `--min_revenue` | No | Minimum revenue filter (e.g., "1M") |
| `--limit` | No | Number of leads (default: 25) |
| `--campaign_name` | No | Instantly campaign name |
| `--skip_instantly` | No | Skip Instantly upload (flag) |

## Quality Checklist
- [ ] Leads match ICP criteria (industry, location, seniority)
- [ ] LinkedIn posts scraped for personalization
- [ ] Icebreakers reference specific post content (not generic)
- [ ] Instantly campaign created with correct variable mapping
- [ ] Leads uploaded with firstName, companyName, personalization fields
- [ ] Cost estimate within budget (~$2-3 per 25-lead campaign)

## Related Directives
- `directives/cold_email_linkedin_personalization.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_cold_email_mastery.md`
- `skills/SKILL_BIBLE_hormozi_email_marketing_complete.md`
- `skills/SKILL_BIBLE_hormozi_lead_generation.md`
