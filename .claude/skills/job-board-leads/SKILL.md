---
name: job-board-leads
description: Find companies hiring for specific roles as lead generation signals. Use when user asks to find job board leads, scrape job listings, find companies hiring, or identify hiring intent signals.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Job Board Lead Finder

## Goal
Scrape job boards to find companies hiring for roles that indicate buying intent (e.g., hiring SDRs = need lead generation help), then output structured lead data.

## Prerequisites
- `PERPLEXITY_API_KEY` in `.env` (for real-time job search)
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env` (for parsing results)

## Execution Command

```bash
python3 .claude/skills/job-board-leads/find_job_board_leads.py \
  --role "Marketing Manager" \
  --location "Remote" \
  --industry "SaaS" \
  --output .tmp/job_leads.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Define Target Role** - Specify the job role that signals buying intent
4. **Set Location/Industry Filters** - Narrow results by geography and vertical
5. **Run Job Search** - Script uses Perplexity AI to search active job listings
6. **Parse & Structure Results** - AI extracts company names, titles, and websites into JSON
7. **Review Output** - Verify lead quality and relevance

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--role` | Yes | Job role to search (e.g., "SDR", "Marketing Manager") |
| `--location` | No | Location filter (e.g., "Remote", "United States") |
| `--industry` | No | Industry filter (e.g., "SaaS", "E-commerce") |
| `--output` | No | Output path (default: `.tmp/job_leads.json`) |

## Quality Checklist
- [ ] Role specified matches buying intent for agency services
- [ ] Location filter applied if targeting specific geo
- [ ] Output JSON contains company name, job title, and website
- [ ] Leads reviewed for relevance before outreach
- [ ] Duplicates removed if combining with existing lists

## Related Directives
- `directives/job_board_lead_finder.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_b2b_lead_generation.md`
- `skills/SKILL_BIBLE_all_lead_gen_methods.md`
- `skills/SKILL_BIBLE_10m_lead_generation.md`
