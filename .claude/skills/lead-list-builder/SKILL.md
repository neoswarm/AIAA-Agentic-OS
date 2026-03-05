---
name: lead-list-builder
description: Build qualified lead lists from multiple sources with email enrichment. Use when user asks to build a lead list, scrape leads, find prospects, generate leads, or create a prospect list.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Lead List Builder

## Goal
Build qualified lead lists using Perplexity-powered search for SaaS founders/CEOs, generate icebreakers, and optionally upload to Instantly for cold email campaigns.

## Prerequisites
- `PERPLEXITY_API_KEY` in `.env` (for lead discovery)
- `INSTANTLY_API_KEY` in `.env` (optional, for campaign upload)
- `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY` in `.env` (for icebreakers)

## Execution Command

```bash
python3 .claude/skills/lead-list-builder/fast_lead_pipeline.py \
  --location "San Francisco" \
  --limit 50 \
  --campaign_name "SF SaaS Outreach"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Define ICP** - Clarify target industry, location, company size, and decision-maker role
4. **Discover Leads** - Use Perplexity to find SaaS founders/CEOs in target location
5. **Generate Icebreakers** - AI creates personalized opening lines for each lead
6. **Deduplicate** - Remove duplicate entries based on email/company
7. **Upload to Instantly** - Optionally create campaign and upload leads (unless `--skip_instantly`)
8. **Save Output** - Leads saved to `.tmp/leads/` as JSON and CSV

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--location` | No | Target location (default: "San Francisco") |
| `--limit` | No | Number of leads to find (default: 50) |
| `--campaign_name` | No | Instantly campaign name for upload |
| `--skip_instantly` | No | Skip Instantly upload (flag) |

## Quality Checklist
- [ ] Leads match target ICP (industry, location, role)
- [ ] Each lead has name, title, company, and website
- [ ] Icebreakers are personalized and specific
- [ ] No duplicates in final list
- [ ] Output files saved to `.tmp/leads/`

## Related Directives
- `directives/build_lead_list.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_hormozi_lead_generation.md`
- `skills/SKILL_BIBLE_hormozi_customer_acquisition_fast.md`
- `skills/SKILL_BIBLE_monetizable_agentic_workflows.md`
