---
name: sales-page
description: Generate long-form sales page copy for products and services. Use when user asks to write a sales page, create landing page copy, or build a product page.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Sales Page Generator

## Goal
Generate high-converting long-form sales page copy with proven copywriting frameworks (AIDA, PAS).

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- Research file or VSL script (optional but recommended)

## Execution Command

```bash
python3 .claude/skills/sales-page/generate_sales_page.py \
  --research-file ".tmp/research.json" \
  --vsl-file ".tmp/vsl_script.md" \
  --output ".tmp/sales_page.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md`, `context/brand_voice.md`
2. **Load Skill Bible** - Read `skills/SKILL_BIBLE_landing_page_ai_mastery.md`
3. **Headline** - Write attention-grabbing headline with benefit
4. **Problem Section** - Agitate the pain points
5. **Solution** - Present the product/service as the answer
6. **Benefits** - Feature-to-benefit breakdown
7. **Social Proof** - Testimonials, case studies, numbers
8. **Offer Stack** - Everything they get with perceived value
9. **Risk Reversal** - Guarantee or risk-free trial
10. **CTA** - Clear, compelling call to action
11. **FAQ** - Address common objections

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--research-file` | No | Research data JSON path |
| `--vsl-file` | No | VSL script for alignment |
| `--output` | No | Output path (default: `.tmp/sales_page.md`) |

## Quality Checklist
- [ ] 2000+ words
- [ ] Compelling headline with primary benefit
- [ ] Problem-agitation-solution flow
- [ ] 3+ testimonials or proof points
- [ ] Offer stack with perceived value
- [ ] Risk reversal / guarantee
- [ ] Multiple CTAs throughout
- [ ] FAQ section with 5+ questions
- [ ] Follows brand voice

## Related Directives
- `directives/vsl_sales_page_writer.md`
- `directives/funnel_copywriter.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_funnel_copywriting_mastery.md`
- `skills/SKILL_BIBLE_landing_page_ai_mastery.md`
