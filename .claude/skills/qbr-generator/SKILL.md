---
name: qbr-generator
description: Generate quarterly business review presentations with AI insights. Use when user asks to create a QBR, generate a quarterly review, build a business review deck, or prepare client performance reports.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Client QBR Generator

## Goal
Generate professional quarterly business review presentations with performance data, AI-generated insights, strategic recommendations, and slide-ready structure.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/qbr-generator/generate_qbr.py \
  --client "Acme Corp" \
  --metrics "Revenue: $50k, Leads: 500, Conversion: 5%" \
  --wins "Launched 3 campaigns, 2x pipeline" \
  --challenges "Deliverability issues" \
  --next_quarter "Scale to 1000 leads/month" \
  --output ".tmp/qbr.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - Read `clients/{client}/*.md` for account history and goals
3. **Gather Data** - Compile quarterly metrics, wins, and challenges
4. **Generate QBR** - AI creates slide-by-slide presentation (Executive Summary, Goals vs Actuals, Key Wins, Metrics Deep Dive, Challenges, Next Quarter, Recommendations)
5. **Add Insights** - AI generates pattern analysis and strategic recommendations
6. **Save Output** - Write QBR Markdown to output file

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client name |
| `--metrics` | Yes | Key metrics achieved this quarter |
| `--wins` | No | Key wins and achievements |
| `--challenges` | No | Challenges faced this quarter |
| `--next_quarter` | No | Next quarter goals and priorities |
| `--output` | No | Output file path (default: `.tmp/qbr.md`) |

## Quality Checklist
- [ ] Executive summary covers overall performance
- [ ] Goals vs actuals comparison included
- [ ] Top 3-5 wins highlighted with impact
- [ ] Metrics deep dive with trends
- [ ] Challenges addressed with lessons learned
- [ ] Next quarter priorities and recommendations
- [ ] Strategic recommendations for growth

## Related Directives
- `directives/client_qbr_generator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_hormozi_customer_retention.md`
- `skills/SKILL_BIBLE_hormozi_profit_maximization.md`
- `skills/SKILL_BIBLE_hormozi_sales_training.md`
