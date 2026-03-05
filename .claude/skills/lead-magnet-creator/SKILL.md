---
name: lead-magnet-creator
description: Create high-value lead magnets with landing pages and nurture email sequences for lead capture. Use when user asks to create a lead magnet, build a PDF guide, generate a checklist, make a template download, or set up a lead capture funnel.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Lead Magnet Creator

## Goal
Generate complete lead magnet systems including the downloadable resource content (checklist, PDF guide, template, calculator, or mini-course), landing page copy, thank-you page content, nurture email sequences, and promotion strategy.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` — AI content generation
- `GOOGLE_APPLICATION_CREDENTIALS` — Google Docs creation

## Execution Command

```bash
python3 .claude/skills/lead-magnet-creator/generate_landing_page.py \
  --product "7-Point Agency Audit Checklist" \
  --target-audience "Agency owners at $10-50K/month" \
  --website "https://youragency.com" \
  --cta-text "Download Free Checklist" \
  --research
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bibles** - Read `skills/SKILL_BIBLE_lead_generation_mastery.md` and `skills/SKILL_BIBLE_lead_magnet_ad_funnels.md`
4. **Choose Lead Magnet Type** - Select optimal format: checklist, PDF guide, template/swipe file, calculator, or mini-course
5. **Generate Lead Magnet Content** - Create the downloadable resource with compelling title, introduction, actionable items, and CTA
6. **Create Landing Page Copy** - Write headline, subheadline, bullet points, form, and CTA button text
7. **Generate Thank-You Page** - Delivery confirmation, download link, and next-step CTA
8. **Build Nurture Email Sequence** - 5-email sequence: delivery (Day 0), quick win (Day 1), case study (Day 3), common mistake (Day 5), soft pitch (Day 7)
9. **Create Promotion Strategy** - Channels, ad copy, and distribution plan
10. **Deliver Assets** - Save all content to `.tmp/lead_magnets/` and optionally create Google Docs

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--product` | Yes | Lead magnet title/product name |
| `--target-audience` | No | Who the lead magnet is for |
| `--headline` | No | Main headline (AI generates if not provided) |
| `--subheadline` | No | Supporting subheadline |
| `--website` | No | Company website for research |
| `--style` | No | Page style: modern-gradient, minimal, bold, corporate (default: modern-gradient) |
| `--research` | No | Enable AI research on the topic (flag) |
| `--cta-text` | No | CTA button text |
| `--cta-url` | No | CTA button URL |
| `--output-dir` | No | Output directory |

## Quality Checklist
- [ ] Lead magnet solves a specific problem
- [ ] Provides a quick win (consumable in <10 min)
- [ ] High perceived value for the target audience
- [ ] Landing page headline is benefit-driven
- [ ] Form captures name + email minimum
- [ ] Email sequence has 5+ emails over 7-14 days
- [ ] Each email provides standalone value
- [ ] CTA leads to clear next step (call/purchase)

## Related Directives
- `directives/ultimate_lead_magnet_creator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_lead_generation_mastery.md`
- `skills/SKILL_BIBLE_lead_magnet_ad_funnels.md`
- `skills/SKILL_BIBLE_email_sequence_writing.md`
- `skills/SKILL_BIBLE_landing_page_copywriting.md`
