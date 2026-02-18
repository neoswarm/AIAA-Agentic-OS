---
name: ad-creative
description: Generate ad copy and creative concepts for Meta, Google, and LinkedIn with A/B variations. Use when user asks to create ad copy, generate Facebook ads, write Google ads, build LinkedIn ad campaigns, or make ad creatives.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Ad Creative Generator

## Goal
Generate platform-specific ad copy and creative concepts for Meta (Facebook/Instagram), Google Search, and LinkedIn ads with multiple headline/body variations for A/B testing.

## Prerequisites
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `.env`
- `FAL_KEY` in `.env` (optional, for generating ad images)

## Execution Command

```bash
python3 .claude/skills/ad-creative/generate_ad_creative.py \
  --product "AI Lead Generation Tool" \
  --audience "Marketing agency owners" \
  --platform facebook \
  --goal conversions \
  --offer "Free 14-day trial" \
  --output .tmp/ad_creative
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read ad copywriting and paid ads skill bibles
4. **Select Copy Formula** - Choose problem-solution, social proof, curiosity, or direct offer
5. **Generate Ad Copy** - Run the ad creative script with product and platform
6. **Create Variations** - Generate 3-5 headline and body copy variants for A/B testing
7. **Suggest Visuals** - Describe image/video concepts for each ad
8. **Output** - Save ad sets to `.tmp/ad_creative/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--product` | Yes | Product or service being advertised |
| `--audience` | Yes | Target audience description |
| `--platform` | No | Ad platform: facebook, google, linkedin, tiktok (default: facebook) |
| `--goal` | No | Campaign goal: conversions, traffic, awareness, leads (default: conversions) |
| `--offer` | No | Special offer or discount |
| `--generate-images` | No | Flag to generate actual ad images |
| `--output` | No | Output path (default: `.tmp/ad_creative`) |

## Quality Checklist
- [ ] Ad copy respects platform character limits (Meta: 125 primary, 40 headline; Google: 30 headline, 90 description)
- [ ] 3-5 headline variations for A/B testing
- [ ] 3-5 body copy variations per ad set
- [ ] Each ad has clear, action-oriented CTA
- [ ] Visual concept described for each ad
- [ ] Copy matches campaign goal (conversions vs awareness)
- [ ] No policy-violating claims or language
- [ ] Follows agency brand voice

## Related Directives
- `directives/ad_creative_generator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_ad_copywriting.md`
- `skills/SKILL_BIBLE_ad_creative_hooks.md`
- `skills/SKILL_BIBLE_meta_ads_manager_technical.md`
- `skills/SKILL_BIBLE_paid_advertising_mastery.md`
- `skills/SKILL_BIBLE_paid_ads_scaling_500k.md`
- `skills/SKILL_BIBLE_facebook_ad_copywriting_direct.md`
- `skills/SKILL_BIBLE_four_ad_funnel_types.md`
