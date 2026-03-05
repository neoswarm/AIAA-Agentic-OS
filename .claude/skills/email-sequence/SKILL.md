---
name: email-sequence
description: Generate multi-email nurture sequences for funnels and campaigns. Use when user asks to create an email sequence, write follow-up emails, or build a nurture campaign.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Email Sequence Generator

## Goal
Generate 7-email nurture sequences for VSL funnels, product launches, and lead nurturing campaigns.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- Research file from prior research step (optional but recommended)

## Execution Command

```bash
python3 .claude/skills/email-sequence/generate_email_sequence.py \
  --research-file ".tmp/research.json" \
  --vsl-file ".tmp/vsl_script.md" \
  --sales-page-file ".tmp/sales_page.md" \
  --sequence-length 7 \
  --output ".tmp/email_sequence.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md`, `context/brand_voice.md`
2. **Load Research** - Import research data for audience understanding
3. **Map Sequence** - Plan email flow: welcome → value → proof → urgency → close
4. **Write Emails** - Generate 300-500 words per email
5. **Subject Lines** - Create compelling subject lines with A/B variants
6. **CTAs** - Clear call-to-action in every email
7. **Quality Gate** - Verify word counts, sequence flow, CTA presence
8. **Output** - Save to `.tmp/`

## Email Sequence Structure
| Email # | Purpose | Focus |
|---------|---------|-------|
| 1 | Welcome | Introduce, set expectations |
| 2 | Value | Share key insight or framework |
| 3 | Story | Client success story or case study |
| 4 | Education | Deep-dive on main benefit |
| 5 | Social Proof | Testimonials and results |
| 6 | Objection | Address top concerns |
| 7 | Urgency/Close | Final CTA with deadline |

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--research-file` | No | Path to research JSON |
| `--vsl-file` | No | Path to VSL script |
| `--sequence-length` | No | Number of emails (default: 7) |
| `--output` | No | Output path |

## Quality Checklist
- [ ] 7 emails minimum in sequence
- [ ] 300+ words per email
- [ ] Compelling subject lines
- [ ] CTA in every email
- [ ] Logical flow from welcome to close
- [ ] Total sequence 2500-3500 words
- [ ] No spam trigger words

## Related Directives
- `directives/vsl_email_sequence_writer.md`
- `directives/email_flow_writer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_cold_email_mastery.md`
- `skills/SKILL_BIBLE_email_campaign_copy_design.md`
