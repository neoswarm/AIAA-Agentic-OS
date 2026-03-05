---
name: ecom-email-calendar
description: Generate 30-day e-commerce email content calendars with campaign themes and strategies. Use when user asks to create an email calendar, plan ecommerce email campaigns, generate email schedule, or build a 30-day email plan.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# E-commerce Email Content Calendar Generator

## Goal
Generate a comprehensive 30-day email campaign calendar for e-commerce brands with campaign themes, send dates, optimal timing, and strategies based on proven 8-figure methodologies.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- Google OAuth credentials (`credentials.json`) for Google Sheets output

## Execution Command

```bash
python3 .claude/skills/ecom-email-calendar/generate_ecom_emails.py \
  --campaign_type "seasonal" \
  --product "Summer Collection" \
  --brand "Fashion Brand" \
  --output .tmp/ecom_emails.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_sturtevant_email_master_system.md` for proven methodology
4. **Gather Brand Info** - Collect brand name, website, niche, key dates, and personalization notes
5. **Run Generator** - Execute `.claude/skills/ecom-email-calendar/generate_ecom_emails.py` to create email campaigns
6. **Review Calendar** - Verify 3-4 emails/week, optimal send days, campaign variety
7. **Deliver** - Save to `.tmp/` and optionally create Google Sheet

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--campaign_type` / `-t` | Yes | Campaign type: product_launch, sale, abandoned_cart, back_in_stock, loyalty, seasonal, vip |
| `--product` / `-p` | Yes | Product or collection name |
| `--brand` / `-b` | Yes | Brand name |
| `--discount` / `-d` | No | Discount details (e.g., "20% off") |
| `--urgency` | No | Urgency level for the campaign |
| `--output` / `-o` | No | Output file path (default: .tmp/ecom_emails.md) |

## Quality Checklist
- [ ] 3-4 emails per week scheduled (never more than 1/day)
- [ ] Optimal send days used (Tues/Wed/Thurs primarily)
- [ ] Campaign types are varied (not repetitive)
- [ ] Key dates are anchored with teaser/reminder sequences
- [ ] Each email includes subject lines, preview text, and body copy
- [ ] Mix of promotional and value-driven content

## Related Directives
- `directives/ecom_email_content_calendar_generator_agent.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_ecom_email_copywriting.md`
- `skills/SKILL_BIBLE_ecom_email_campaign.md`
- `skills/SKILL_BIBLE_ecom_email_marketing_v2.md`
- `skills/SKILL_BIBLE_ecom_email_advanced_strategies.md`
- `skills/SKILL_BIBLE_email_campaign_mastery.md`
