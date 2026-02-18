---
name: monthly-report
description: Generate professional monthly client performance reports with metrics, insights, and recommendations. Use when user asks to create a monthly report, generate client report, build performance summary, or produce monthly analytics.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Monthly Report Generator

## Goal
Generate professional monthly client performance reports with metrics tables, MoM comparisons, executive summaries, and actionable recommendations.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env` (for AI-generated insights)

## Execution Command

```bash
python3 .claude/skills/monthly-report/generate_monthly_report.py \
  --client "Acme Corp" \
  --metrics '{"leads": 500, "meetings": 50, "closed": 10, "revenue": 50000}' \
  --highlights "Launched new email campaign, hit 60% open rate" \
  --challenges "Lead quality dipped in week 3" \
  --month "January 2026" \
  --output .tmp/monthly_report.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - Read `clients/{client}/*.md` for client-specific rules
3. **Gather Metrics** - Collect performance data (leads, meetings, revenue, etc.)
4. **Run Report Generator** - AI generates executive summary, metrics table, and insights
5. **Review Report** - Verify accuracy of metrics and quality of recommendations
6. **Deliver** - Upload to Google Docs and notify via Slack

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client name |
| `--metrics` | Yes | JSON string of performance metrics |
| `--highlights` | No | Key wins and highlights for the month |
| `--challenges` | No | Challenges and issues encountered |
| `--month` | No | Report month (default: last month) |
| `--output` | No | Output path (default: `.tmp/monthly_report.md`) |

## Quality Checklist
- [ ] All metrics accurately reflected in report
- [ ] Executive summary captures key takeaways
- [ ] MoM or goal comparisons included
- [ ] Actionable recommendations provided
- [ ] Report is professional and client-ready
- [ ] Minimum 800 words

## Related Directives
- `directives/monthly_reporting.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_client_reporting_dashboards.md`
