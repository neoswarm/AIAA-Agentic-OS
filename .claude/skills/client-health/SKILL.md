---
name: client-health
description: Calculate client health scores across engagement, results, relationship, and financial dimensions. Use when user asks to check client health, calculate health scores, assess account health, or prioritize client retention.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Client Health Score Calculator

## Goal
Calculate weighted health scores for client accounts based on engagement, NPS, usage, support tickets, payment status, and growth to classify clients as Healthy, Stable, At Risk, or Critical.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env` (optional, for insights)

## Execution Command

```bash
python3 .claude/skills/client-health/calculate_client_health.py \
  --client "Acme Corp" \
  --metrics '{"engagement": 80, "nps": 7, "usage": 60, "support_tickets": 2, "payment_status": "current", "growth": 15}' \
  --output ".tmp/health_score.json"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - Read `clients/{client}/*.md` for account history
3. **Gather Metrics** - Collect engagement, NPS, usage, support, payment, and growth data
4. **Calculate Weighted Score** - Apply weights (engagement 25%, NPS 20%, usage 20%, support 15%, payment 10%, growth 10%)
5. **Classify Status** - Healthy (80+), Stable (60-79), At Risk (40-59), Critical (<40)
6. **Generate Recommendations** - Provide action items based on classification
7. **Save Output** - Write health score breakdown and recommendations to JSON

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client name |
| `--metrics` | Yes | JSON string with metrics (engagement, nps, usage, support_tickets, payment_status, growth) |
| `--output` | No | Output file path (default: `.tmp/health_score.json`) |

## Quality Checklist
- [ ] All 6 metric dimensions scored
- [ ] Weighted score correctly calculated
- [ ] Status classification matches score range
- [ ] Factor-by-factor breakdown included
- [ ] Actionable recommendations based on status
- [ ] Risk factors highlighted for at-risk/critical clients

## Related Directives
- `directives/client_health_score.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_hormozi_customer_retention.md`
- `skills/SKILL_BIBLE_hormozi_profit_maximization.md`
