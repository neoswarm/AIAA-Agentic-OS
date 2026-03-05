---
name: contract-renewal
description: Generate contract renewal outreach and reminder sequences. Use when user asks to create renewal reminders, generate renewal emails, prepare renewal outreach, or track contract expirations.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Contract Renewal Reminder

## Goal
Generate compelling contract renewal outreach with value-focused emails, renewal talking points, proposal outlines, and follow-up sequences starting 90/60/30 days before expiration.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/contract-renewal/remind_contract_renewal.py \
  --client "Acme Corp" \
  --days_until 60 \
  --value 50000 \
  --wins "Launched 3 campaigns, 2x pipeline growth" \
  --output ".tmp/renewal_reminder.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - Read `clients/{client}/*.md` for account history and results
3. **Calculate Timeline** - Determine expiry date and appropriate outreach cadence
4. **Generate Renewal Email** - Create initial outreach email with value recap and CTA
5. **Generate Follow-up** - Create shorter, direct follow-up for non-responders
6. **Create Talking Points** - ROI metrics, delivered value, new features, upsell opportunities
7. **Draft Proposal Outline** - Executive summary, results, continued benefits, pricing, next steps
8. **Save Output** - Write complete renewal package to Markdown file

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client name |
| `--days_until` | Yes | Days until contract expiry |
| `--value` | No | Contract value in dollars (default: 0) |
| `--wins` | No | Key wins/results achieved during contract |
| `--output` | No | Output file path (default: `.tmp/renewal_reminder.md`) |

## Quality Checklist
- [ ] Initial renewal email is value-focused (not pushy)
- [ ] Follow-up email is shorter and more direct
- [ ] Talking points include ROI metrics and delivered value
- [ ] Upsell/expansion opportunities identified
- [ ] Objection handling points included
- [ ] Renewal proposal outline covers all key sections
- [ ] Tone matches urgency level (90 vs 60 vs 30 days)

## Related Directives
- `directives/contract_renewal_reminder.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_hormozi_customer_retention.md`
- `skills/SKILL_BIBLE_hormozi_sales_training.md`
