---
name: video-ad-script
description: Generate video ad scripts with hook variations, shot lists, and A/B test variants for Meta, YouTube, and TikTok. Use when user asks to write a video ad, create ad scripts, generate UGC scripts, build TikTok ad copy, or produce video ad variations.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Video Ad Script Generator

## Goal
Create complete video ad script systems for Meta, YouTube, TikTok, and UGC-style ads. Produces attention-grabbing hook variations, full scripts in 15/30/60-second formats, shot-by-shot breakdowns, multiple ad angles, A/B test variations, and thumbnail concepts.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` — AI script generation

## Execution Command

```bash
python3 .claude/skills/video-ad-script/generate_ad_creative.py \
  --product "Fitness App" \
  --audience "Busy professionals wanting to get fit" \
  --platform "facebook" \
  --goal "conversions" \
  --offer "7-day free trial" \
  --generate-images
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bibles** - Read `skills/SKILL_BIBLE_ad_creative_hooks.md` and `skills/SKILL_BIBLE_ad_copywriting.md`
4. **Generate Hook Variations** - Create 5+ hooks per variation across 6 categories: question, controversial, story, result, fear, curiosity
5. **Write Full Scripts** - Structure scripts for target length (15s, 30s, or 60s) with hook → problem → solution → proof → CTA
6. **Create Shot Lists** - Define camera angles, B-roll suggestions, text overlays, audio/music cues, and talent direction for each section
7. **Develop Ad Angles** - Generate multiple angles targeting different pain points, proof points, and presenter styles
8. **Build A/B Variations** - Create test variants with different hooks, CTAs, and proof elements
9. **Generate Thumbnail Concepts** - Design thumbnail ideas that complement the video content
10. **Deliver Scripts** - Save all scripts and production materials to `.tmp/ad_creative/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--product` | Yes | Product/service name |
| `--audience` | Yes | Target audience description |
| `--platform` | No | facebook, instagram, youtube, tiktok (default: facebook) |
| `--goal` | No | conversions, traffic, engagement, awareness (default: conversions) |
| `--offer` | No | Special offer or discount |
| `--generate-images` | No | Generate actual ad images (flag) |
| `--output` | No | Output directory (default: .tmp/ad_creative) |

## Quality Checklist
- [ ] Hook grabs attention in first 3 seconds
- [ ] Script matches platform style and norms
- [ ] CTA is clear and specific
- [ ] Timing matches target length (15s/30s/60s)
- [ ] Proof points are accurate and compelling
- [ ] Language matches target audience
- [ ] No ad policy violations
- [ ] Shot list is production-ready
- [ ] At least 3 script variations created

## Related Directives
- `directives/ultimate_video_ad_script.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_ad_creative_hooks.md`
- `skills/SKILL_BIBLE_vsl_writing_production.md`
- `skills/SKILL_BIBLE_ad_copywriting.md`
- `skills/SKILL_BIBLE_youtube_script_writing.md`
