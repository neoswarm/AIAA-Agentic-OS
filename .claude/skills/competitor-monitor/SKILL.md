---
name: competitor-monitor
description: Monitor competitors across web, social, ads, and SEO to generate competitive intelligence reports. Use when user asks to monitor competitors, track competitor activity, or create a competitive analysis.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Competitor Monitor

## Goal
Track competitor activity across website changes, social media, advertising, and SEO to identify opportunities and threats, generating actionable intelligence reports.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `PERPLEXITY_API_KEY` for web research

## Execution Command

```bash
python3 .claude/skills/competitor-monitor/monitor_competitors.py \
  --competitors "competitor1.com,competitor2.com,competitor3.com" \
  --focus "pricing,features,content" \
  --your_company "Acme Corp" \
  --output ".tmp/competitor_report.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_marketing_strategy_advanced.md`
4. **Configure Targets** - Set up competitor domains and focus areas
5. **Website Analysis** - Check pricing changes, feature updates, messaging shifts, new content
6. **Social Monitoring** - Track post frequency, engagement rates, content themes
7. **SEO Comparison** - Compare keyword rankings, domain authority, backlink changes
8. **Generate Report** - Executive summary with opportunities, threats, and action items
9. **Output** - Save competitive intelligence report to `.tmp/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--competitors` | Yes | Comma-separated competitor domains |
| `--focus` | No | Focus areas: pricing, features, content (default: `pricing,features,content`) |
| `--your_company` | No | Your company name for comparison |
| `--output` | No | Output file path (default: `.tmp/competitor_report.md`) |

## Quality Checklist
- [ ] All specified competitors analyzed
- [ ] Executive summary highlights key changes
- [ ] Opportunities identified from competitor weaknesses
- [ ] Threats flagged with recommended responses
- [ ] Pricing and feature comparisons included
- [ ] Content and messaging trends captured
- [ ] Actionable recommendations provided
- [ ] Data sources cited

## Related Directives
- `directives/competitor_monitor.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_marketing_strategy_advanced.md`
- `skills/SKILL_BIBLE_marketing_fundamentals_deep.md`
- `skills/SKILL_BIBLE_marketing_mastery.md`
- `skills/SKILL_BIBLE_agency_self_marketing.md`
