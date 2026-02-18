---
name: client-report
description: Generate automated client performance reports with AI insights. Use when user asks to create a client report, generate a performance summary, or build a monthly report.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Client Report Generator

## Goal
Generate professional client performance reports with data-driven metrics, AI-powered insights, period-over-period comparisons, and actionable recommendations.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` (for AI insights)
- `GOOGLE_APPLICATION_CREDENTIALS` for Google Docs delivery (optional)
- Performance data (manual JSON or API-connected)

## Execution Command

```bash
# Monthly report
python3 .claude/skills/client-report/generate_client_report.py \
  --client "Acme Corp" \
  --period "monthly" \
  --start-date "2026-01-01" \
  --end-date "2026-01-31" \
  --service "meta_ads" \
  --format "markdown"

# Weekly report with all services
python3 .claude/skills/client-report/generate_client_report.py \
  --client "Acme Corp" \
  --period "weekly" \
  --service "all" \
  --format "google_doc"

# From manual data file
python3 .claude/skills/client-report/generate_client_report.py \
  --client "Acme Corp" \
  --data-file performance_data.json \
  --format "pdf"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - Read `clients/{client}/*.md` for client-specific details
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_client_reporting_dashboards.md`
4. **Collect Data** - Pull metrics from data file or connected platforms
5. **Calculate Metrics** - Period-over-period changes, trends, benchmarks
6. **Generate AI Insights** - What happened, why, and what to do next
7. **Build Report** - Executive summary, dashboard, detailed breakdown, recommendations
8. **Deliver** - Save to `.tmp/` and optionally push to Google Docs

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client name |
| `--period` | No | `weekly`, `monthly`, or `quarterly` |
| `--start-date` | No | Reporting period start (YYYY-MM-DD) |
| `--end-date` | No | Reporting period end (YYYY-MM-DD) |
| `--service` | No | `meta_ads`, `google_ads`, `seo`, or `all` |
| `--format` | No | `markdown`, `pdf`, or `google_doc` |
| `--data-file` | No | Path to manual data JSON |
| `--no-recommendations` | No | Skip AI recommendations section |

## Quality Checklist
- [ ] All key metrics included (spend, conversions, ROAS, CPA)
- [ ] Period-over-period comparisons accurate
- [ ] AI insights are specific and actionable (not generic)
- [ ] Executive summary on first page
- [ ] Recommendations are prioritized and relevant
- [ ] Charts/data visualizations rendering correctly
- [ ] Client branding applied
- [ ] Report formatted professionally

## Related Directives
- `directives/ultimate_client_reporting.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_client_reporting_dashboards.md`
- `skills/SKILL_BIBLE_client_communication_setup.md`
- `skills/SKILL_BIBLE_client_operations_retention.md`
- `skills/SKILL_BIBLE_roi_calculator_sales_tools.md`
