---
name: review-collector
description: Generate personalized review request emails to collect client testimonials across Google, G2, Capterra, and other platforms. Use when user asks to request a review, collect testimonials, send review requests, or get client feedback.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Review Collector

## Goal
Generate personalized review request emails that get responses. Creates multiple email versions (direct ask, soft ask, follow-up) and an optional SMS version for collecting reviews on Google, G2, Capterra, and other platforms.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env` (for email generation)

## Execution Command

```bash
python3 .claude/skills/review-collector/send_review_request.py \
  --client "John Smith" \
  --company "Acme Corp" \
  --product "Marketing Services" \
  --platform google \
  --results "Increased leads by 300% in 3 months" \
  --output .tmp/review_request.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Identify Happy Client** - Confirm client satisfaction before requesting review
4. **Choose Platform** - Select review platform (Google, G2, Capterra, Trustpilot)
5. **Generate Emails** - AI creates direct ask, soft ask, and follow-up versions
6. **Generate SMS** - Optional brief text message version
7. **Review Output** - Verify personalization and tone
8. **Send or Save** - Deliver via email or save as drafts

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client contact name |
| `--company` | No | Client company name |
| `--product` | Yes | Product or service they used |
| `--platform` | No | Review platform: google, g2, capterra, trustpilot (default: google) |
| `--results` | No | Specific results achieved for this client |
| `--output` | No | Output path (default: `.tmp/review_request.md`) |

## Quality Checklist
- [ ] Emails are personalized with client name and results
- [ ] Multiple versions provided (direct ask, soft ask, follow-up)
- [ ] Each email under 100 words
- [ ] Clear CTA with review link placeholder
- [ ] Tone is genuine, not pushy
- [ ] SMS version is brief and actionable

## Related Directives
- `directives/review_collection.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_agency_sales_system.md`
