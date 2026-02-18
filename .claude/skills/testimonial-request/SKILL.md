---
name: testimonial-request
description: Generate personalized testimonial and review request emails. Use when user asks to request a testimonial, collect reviews, ask for client feedback, send review request, or gather social proof.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Testimonial Request Generator

## Goal
Generate personalized review request emails with multiple versions (direct ask, soft ask, follow-up, SMS) that drive client testimonial collection across platforms like Google, G2, and Capterra.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` - For AI-powered email generation

## Execution Command

```bash
python3 .claude/skills/testimonial-request/send_review_request.py \
  --client "John Smith" \
  --company "Acme Corp" \
  --product "Marketing Services" \
  --platform "google" \
  --results "40% increase in leads" \
  --output .tmp/review_request.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Gather Details** - Client name, company, product/service, results achieved
4. **Generate Request Emails** - Run script to create multi-version request emails
5. **Review Output** - Verify personalization, tone, and CTA clarity

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client's name |
| `--company` | No | Client's company name |
| `--product` | Yes | Product or service they used |
| `--platform` | No | Review platform: google, g2, capterra, etc. (default: google) |
| `--results` | No | Specific results achieved for personalization |
| `--output` | No | Output file path (default: .tmp/review_request.md) |

## Quality Checklist
- [ ] Direct ask email version included
- [ ] Soft ask with testimonial option included
- [ ] Follow-up email for non-responders included
- [ ] SMS version included
- [ ] All emails under 100 words
- [ ] Specific results referenced (if provided)
- [ ] Clear CTA with review link placeholder
- [ ] Tone is genuine and non-pushy

## Related Directives
- `directives/testimonial_request.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_client_retention.md`
- `skills/SKILL_BIBLE_social_proof_mastery.md`
