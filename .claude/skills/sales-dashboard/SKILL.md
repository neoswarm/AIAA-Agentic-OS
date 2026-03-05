---
name: sales-dashboard
description: Generate sales pipeline dashboard with deal stages, values, velocity metrics, and AI-powered insights. Use when user asks to create a sales dashboard, analyze the pipeline, generate pipeline report, or review deal stages.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Sales Pipeline Dashboard

## Goal
Generate a visual sales pipeline dashboard from deal data showing stage distribution, total value, velocity metrics, and AI-powered actionable insights.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env` (for AI analysis)

## Execution Command

```bash
python3 .claude/skills/sales-dashboard/generate_sales_dashboard.py \
  --deals deals.json \
  --period "Current Month" \
  --output .tmp/sales_dashboard.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Deal Data** - Read deals from JSON file or inline JSON
4. **Calculate Metrics** - Aggregate by stage, count deals, sum values
5. **AI Analysis** - Generate pipeline health assessment and recommendations
6. **Build Dashboard** - Formatted markdown with tables, metrics, and insights
7. **Identify At-Risk Deals** - Flag stale or at-risk opportunities
8. **Save Report** - Output to markdown file

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--deals` | Yes | Path to deals JSON file or inline JSON string |
| `--period` | No | Reporting period label (default: "Current Month") |
| `--output` | No | Output path (default: `.tmp/sales_dashboard.md`) |

### Deals JSON Format
```json
[
  {
    "name": "Acme Corp",
    "stage": "Proposal",
    "value": 15000,
    "owner": "John",
    "created": "2026-01-10"
  }
]
```

## Quality Checklist
- [ ] All deals loaded and categorized by stage
- [ ] Total pipeline value calculated correctly
- [ ] Stage distribution shown with counts and values
- [ ] AI insights are actionable and specific
- [ ] At-risk deals identified with recommendations
- [ ] Report is presentation-ready

## Related Directives
- `directives/sales_pipeline_dashboard.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_crm_pipeline_management.md`
- `skills/SKILL_BIBLE_agency_sales_system.md`
