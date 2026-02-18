---
name: campaign-report
description: Generate email campaign performance reports with AI insights. Use when user asks to create a campaign report, analyze email metrics, check campaign performance, or generate campaign analytics.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Email Campaign Performance Report

## Goal
Generate automated campaign performance reports with KPI calculations, benchmark comparisons, domain health tracking, and AI-powered recommendations.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- Campaign metrics data (JSON file from email platform)
- `SLACK_WEBHOOK_URL` for Slack delivery (optional)

## Execution Command

```bash
python3 .claude/skills/campaign-report/generate_campaign_report.py \
  --campaign "Q1 Cold Email Campaign" \
  --metrics ".tmp/stats.json" \
  --period "Last 30 days" \
  --output ".tmp/campaign_report.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_cold_email_analytics.md`
4. **Fetch Metrics** - Load campaign stats from JSON or pull from platform API
5. **Calculate KPIs** - Delivery rate, open rate, reply rate, positive rate, bounce rate
6. **Benchmark Comparison** - Compare against industry benchmarks (>95% delivery, >50% open, >5% reply)
7. **Generate AI Insights** - Analyze trends, identify issues, recommend improvements
8. **Format Report** - Create structured report with executive summary, campaign breakdown, domain health, and alerts
9. **Deliver** - Save to `.tmp/` and optionally send via Slack

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--campaign` / `-c` | Yes | Campaign name |
| `--metrics` / `-m` | Yes | Metrics JSON file path |
| `--period` / `-p` | No | Reporting period (default: "Last 30 days") |
| `--output` / `-o` | No | Output file (default: `.tmp/campaign_report.md`) |

## Quality Checklist
- [ ] Executive summary with key takeaways
- [ ] All KPIs calculated and compared to benchmarks
- [ ] Domain health status (green/yellow/red)
- [ ] Campaign-by-campaign breakdown included
- [ ] Alerts flagged for metrics outside thresholds
- [ ] AI recommendations are actionable
- [ ] Report formatted as clean markdown
- [ ] Period-over-period comparison when data available

## Related Directives
- `directives/email_campaign_report.md`
- `directives/daily_campaign_reports_health_metrics_bounce_rate_alerts.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_cold_email_analytics.md`
- `skills/SKILL_BIBLE_email_campaign_mastery.md`
- `skills/SKILL_BIBLE_client_reporting_dashboards.md`
- `skills/SKILL_BIBLE_email_deliverability.md`
