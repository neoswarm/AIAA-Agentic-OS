---
name: static-ad
description: Generate static ad concepts with copy and optional AI images for Meta, Google, and LinkedIn. Use when user asks to create static ads, generate ad images, build ad creatives, or design ad concepts.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Static Ad Generator

## Goal
Generate static ad concepts with compelling copy, visual descriptions, and optional AI-generated images for Meta, Google, LinkedIn, and Instagram ad platforms.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `FAL_KEY` in `.env` (optional, for AI image generation)

## Execution Command

```bash
python3 .claude/skills/static-ad/generate_static_ad.py \
  --product "AI Lead Generation Platform" \
  --offer "Free 14-day trial" \
  --platform "facebook" \
  --audience "B2B SaaS founders" \
  --variations 5 \
  --generate-images \
  --output ".tmp/static_ads"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_meta_ads_manager_technical.md`
4. **Research Audience** - Understand target audience pain points and desires
5. **Generate Ad Concepts** - Create 3-5 ad concepts with headlines, body copy, and CTAs
6. **Create Visual Descriptions** - Detailed image prompts for each concept
7. **Generate Images** - (Optional) Create AI-generated ad images using FAL
8. **Format for Platform** - Ensure copy fits platform character limits
9. **Output** - Save concepts with copy and images to `.tmp/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--product` / `-p` | Yes | Product or service name |
| `--offer` / `-o` | No | Special offer or promotion |
| `--platform` | No | Target platform: `facebook`, `instagram`, `linkedin`, `google` (default: `facebook`) |
| `--audience` / `-a` | No | Target audience description |
| `--variations` / `-v` | No | Number of ad variations (default: 5) |
| `--generate-images` | No | Flag to generate actual AI ad images |
| `--output` | No | Output directory (default: `.tmp/static_ads`) |

## Quality Checklist
- [ ] At least 3 unique ad concepts generated
- [ ] Headlines are attention-grabbing and benefit-driven
- [ ] Body copy follows platform character limits
- [ ] Clear CTA in every ad variation
- [ ] Visual descriptions are detailed and actionable
- [ ] Ad concepts target specified audience pain points
- [ ] Copy follows platform best practices (Meta, Google, LinkedIn)
- [ ] Brand colors and style guidelines referenced

## Related Directives
- `directives/static_ad_generator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_meta_ads_manager_technical.md`
- `skills/SKILL_BIBLE_ad_creative_hooks.md`
- `skills/SKILL_BIBLE_paid_advertising_mastery.md`
- `skills/SKILL_BIBLE_n8n_ad_creative_automation.md`
