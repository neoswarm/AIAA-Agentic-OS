---
name: webinar-funnel
description: Generate complete webinar funnel assets including registration page, slide deck, email sequences, and thank you page. Use when user asks to create a webinar funnel, build webinar assets, or generate webinar content.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Webinar Funnel Generator

## Goal
Generate a complete webinar funnel package: registration page copy, webinar slide outline, pre/post-webinar email sequences, thank you page, and slide deck outline.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `GOOGLE_APPLICATION_CREDENTIALS` for Google Docs export (optional)

## Execution Command

```bash
python3 .claude/skills/webinar-funnel/generate_webinar_funnel.py \
  --topic "How to 10x Your Agency Revenue with AI" \
  --offer "AI Growth Accelerator Program" \
  --price "$997" \
  --audience "Agency owners doing $10K-$50K/mo" \
  --duration "90" \
  --teaching_style "Educational with soft pitch" \
  --guarantee "30-day money-back guarantee" \
  --output_dir ".tmp/webinar_output"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_webinar_funnel_launch.md`
4. **Generate Webinar Script** - Create full webinar presentation script with hook, content, and pitch sections
5. **Create Registration Page** - High-converting registration page copy with headline, bullet points, urgency elements
6. **Build Email Sequences** - Pre-webinar (3-5 emails) and post-webinar (5-7 emails) sequences
7. **Create Slide Deck Outline** - Slide-by-slide outline with speaker notes
8. **Generate Thank You Page** - Post-registration page to maximize live attendance
9. **Output** - Save all assets to output directory

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--topic` | Yes | Webinar topic or title |
| `--offer` | Yes | Product/service being offered |
| `--price` | Yes | Price point (e.g., `$997`) |
| `--audience` | Yes | Target audience description |
| `--duration` | No | Webinar duration in minutes (default: `90`) |
| `--datetime` | No | Webinar date and time |
| `--fast_action_bonus` | No | Fast action bonus description |
| `--teaching_style` | No | Teaching style (default: `Educational with soft pitch`) |
| `--guarantee` | No | Guarantee offered (default: `30-day money-back guarantee`) |
| `--output_dir` | No | Output directory (default: `.tmp/webinar_output`) |

## Quality Checklist
- [ ] Registration page has compelling headline and 3+ bullet points
- [ ] Webinar script follows hook → content → pitch structure
- [ ] Pre-webinar email sequence builds anticipation (3-5 emails)
- [ ] Post-webinar sequence includes replay, objection handling, urgency (5-7 emails)
- [ ] Slide deck outline covers full presentation flow
- [ ] Thank you page maximizes live attendance
- [ ] CTA and offer are clear throughout
- [ ] Min 1500 words for webinar script

## Related Directives
- `directives/webinar_funnel_generator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_webinar_funnel_launch.md`
- `skills/SKILL_BIBLE_webinar_funnel_building.md`
- `skills/SKILL_BIBLE_webinar_mastery.md`
- `skills/SKILL_BIBLE_webinar_live_events.md`
- `skills/SKILL_BIBLE_landing_page_ai_mastery.md`
- `skills/SKILL_BIBLE_funnel_copywriting_mastery.md`
