---
name: carousel-post
description: Generate LinkedIn or Instagram carousel posts with slide-by-slide content and captions. Use when user asks to create a carousel post, make swipeable slides, or build a LinkedIn/Instagram carousel.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Carousel Post Creator

## Goal
Generate complete LinkedIn/Instagram carousel posts including slide-by-slide content (hook, value slides, summary, CTA), design specs, and engagement-optimized captions with hashtags.

## Prerequisites
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/carousel-post/generate_carousel.py \
  --topic "5 Cold Email Mistakes" \
  --slides 8 \
  --platform linkedin \
  --output .tmp/carousel.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read content strategy and social media skill bibles
4. **Plan Slide Structure** - Map out hook slide, value slides, summary, and CTA
5. **Generate Carousel** - Run the carousel generation script with topic and platform
6. **Validate Slides** - Ensure each slide has concise text (10-20 words) and visual hierarchy
7. **Generate Caption** - Create caption with hook expansion, takeaway bullets, and hashtags
8. **Output** - Save to `.tmp/carousel.md`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--topic` | Yes | What the carousel is about |
| `--slides` | No | Number of slides, 5-10 (default: 8) |
| `--platform` | No | Target platform: linkedin or instagram (default: linkedin) |
| `--output` | No | Output path (default: `.tmp/carousel.md`) |

## Quality Checklist
- [ ] Slide 1 hook creates curiosity ("Swipe to learn...")
- [ ] Each value slide has one clear point with short text
- [ ] Summary slide recaps key takeaways
- [ ] Final slide has strong CTA (follow, save, share)
- [ ] Caption includes hook expansion and hashtags
- [ ] Design specs included (1080x1080 or 1080x1350)
- [ ] Platform-appropriate formatting (LinkedIn vs Instagram)
- [ ] Follows agency brand voice

## Related Directives
- `directives/carousel_post_creator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_content_strategy_growth.md`
- `skills/SKILL_BIBLE_social_media_marketing_agency_.md`
- `skills/SKILL_BIBLE_persuasion_speaking.md`
