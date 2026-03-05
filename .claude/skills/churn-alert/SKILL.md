---
name: churn-alert
description: Identify clients at risk of churning with risk scores and retention alerts. Use when user asks to check churn risk, identify at-risk clients, calculate churn scores, or create retention alerts.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Churn Risk Alert

## Goal
Monitor client engagement, payments, and support data to calculate churn risk scores, classify risk levels, and trigger proactive retention alerts with recommended actions.

## Prerequisites
- No API keys required for basic risk calculation (uses local data)

## Execution Command

```bash
python3 .claude/skills/churn-alert/alert_churn_risk.py \
  --clients "clients.json" \
  --output ".tmp/churn_alerts.json"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Data** - Read client metrics from input JSON file
3. **Calculate Risk Scores** - Score each client based on engagement, support tickets, usage decline, payment issues, NPS, and contract renewal proximity
4. **Classify Risk Level** - Categorize as critical (60+), high (40-59), medium (20-39), or low (0-19)
5. **Generate Alerts** - Create alert report with risk factors and recommended actions per client
6. **Save Output** - Write risk scores and alerts to output JSON

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--clients` | Yes | JSON file with client data (engagement_score, support_tickets_30d, usage_change_pct, payment_status, nps_score, days_to_renewal) |
| `--output` | No | Output file path (default: `.tmp/churn_alerts.json`) |

## Quality Checklist
- [ ] All clients scored on 6+ risk indicators
- [ ] Risk levels correctly classified (critical/high/medium/low)
- [ ] Specific risk factors listed for each client
- [ ] Actionable recommendations provided per risk level
- [ ] MRR at risk calculated where data available

## Related Directives
- `directives/churn_risk_alert.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_hormozi_customer_retention.md`
- `skills/SKILL_BIBLE_hormozi_sales_training.md`
- `skills/SKILL_BIBLE_hormozi_profit_maximization.md`
