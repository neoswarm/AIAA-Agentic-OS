---
name: funding-tracker
description: Track recent funding rounds and identify newly funded companies as sales leads. Use when user asks to track funding rounds, find recently funded startups, monitor funding announcements, or generate leads from funding news.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Funding Round Tracker

## Goal
Monitor recent funding announcements to identify newly funded companies as high-intent sales leads with buying signals, and generate personalized outreach templates.

## Prerequisites
- `PERPLEXITY_API_KEY` in `.env` (for real-time funding data)

## Execution Command

```bash
python3 .claude/skills/funding-tracker/track_funding_rounds.py \
  --stage "seed,series_a,series_b" \
  --industry "saas" \
  --days 30 \
  --output .tmp/funded_companies.json
```

### Daily Cron (Last 7 Days)

```bash
python3 .claude/skills/funding-tracker/track_funding_rounds.py \
  --stage "series_a,series_b" \
  --days 7
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Define Filters** - Set funding stages, industries, and lookback period
3. **Search Funding News** - Query Perplexity for recent funding announcements
4. **Parse Results** - Extract company name, funding amount, stage, investors, and description
5. **Score Leads** - Assess fit based on stage, industry, and growth signals
6. **Generate Outreach** - Create personalized email templates referencing funding round
7. **Output** - Save to JSON and optionally push to Google Sheets or Slack

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--stage` / `-s` | No | Funding stages, comma-separated (default: seed,series_a,series_b) |
| `--industry` / `-i` | No | Industry filter (e.g., "saas", "fintech") |
| `--days` / `-d` | No | Days to look back (default: 30) |
| `--output` / `-o` | No | Output file path (default: .tmp/funded_companies.json) |

## Quality Checklist
- [ ] Results include company name, funding amount, stage, and investors
- [ ] Results filtered to specified stages and industries
- [ ] Output JSON is valid and well-structured
- [ ] At least 3 funded companies returned per search

## Related Directives
- `directives/funding_round_tracker.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_lead_generation_mastery.md`
- `skills/SKILL_BIBLE_b2b_lead_generation.md`
- `skills/SKILL_BIBLE_10m_lead_generation.md`
