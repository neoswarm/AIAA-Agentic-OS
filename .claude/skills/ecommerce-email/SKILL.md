---
name: ecommerce-email
description: Generate high-converting e-commerce email campaigns using proven methodology. Use when user asks to create ecommerce emails, write product launch emails, build abandoned cart sequences, or generate promotional email campaigns.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# E-commerce Email Campaign Generator

## Goal
Generate high-converting e-commerce email campaigns (product launches, sales, abandoned cart, back in stock, loyalty, seasonal, VIP) using AI research and proven $40M email marketing methodology.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` (for AI copy generation)
- `PERPLEXITY_API_KEY` for brand research (optional)
- `GOOGLE_APPLICATION_CREDENTIALS` for Google Docs delivery (optional)
- `SLACK_WEBHOOK_URL` for notifications (optional)

## Execution Command

```bash
python3 .claude/skills/ecommerce-email/generate_ecom_emails.py \
  --campaign_type "product_launch" \
  --product "Hydrating Face Serum" \
  --brand "GlowSkin" \
  --discount "20% off launch week" \
  --urgency "Limited first batch" \
  --output .tmp/ecom_campaign.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bibles** - Read `skills/SKILL_BIBLE_ecommerce_email_marketing.md` and `skills/SKILL_BIBLE_ecom_email_copywriting.md`
4. **Research Brand** - Use Perplexity for brand voice, products, and audience insights
5. **Select Campaign Type** - Map to appropriate email framework
6. **Generate Campaign Ideas** - Create 5 campaign concepts using proven methodology
7. **Write Email Copy** - Full email for each campaign (subject line, body, CTA)
8. **Review Quality** - Verify against SCE Framework (Skimmable, Clear, Engaging)
9. **Deliver** - Save to `.tmp/` and optionally push to Google Docs + Slack

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--campaign_type` | Yes | `product_launch`, `sale`, `abandoned_cart`, `back_in_stock`, `loyalty`, `seasonal`, or `vip` |
| `--product` | Yes | Product name or collection |
| `--brand` | Yes | Brand name |
| `--discount` | No | Discount or offer details |
| `--urgency` | No | Urgency/scarcity angle |
| `--output` | No | Output file path |

## Quality Checklist
- [ ] Subject line is compelling and under 50 characters
- [ ] Email follows one-email-one-topic rule
- [ ] Copy is skimmable, punchy, and educational
- [ ] Brand voice and tone are consistent
- [ ] CTA is clear and immediately visible
- [ ] Mobile-friendly formatting
- [ ] Urgency/scarcity used appropriately (not forced)
- [ ] Min 300 words per email

## Related Directives
- `directives/ecom_email_campaign_generator_agent.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_ecommerce_email_marketing.md`
- `skills/SKILL_BIBLE_ecom_email_copywriting.md`
- `skills/SKILL_BIBLE_ecom_email_campaign.md`
- `skills/SKILL_BIBLE_ecom_email_advanced_strategies.md`
- `skills/SKILL_BIBLE_high_converting_email_design.md`
- `skills/SKILL_BIBLE_email_campaign_mastery.md`
- `skills/SKILL_BIBLE_black_friday_email_campaigns.md`
