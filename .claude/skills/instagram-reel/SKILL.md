---
name: instagram-reel
description: Generate scroll-stopping Instagram Reel scripts with hooks, timing markers, and captions. Use when user asks to write a reel script, create an Instagram Reel, or generate short-form video content for Instagram.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Instagram Reel Script Creator

## Goal
Generate complete Instagram Reel scripts with scroll-stopping hooks, structured content with timing markers, text overlay suggestions, and engagement-optimized captions with hashtags.

## Prerequisites
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/instagram-reel/generate_instagram_reel.py \
  --topic "How to write cold emails that get replies" \
  --length 30 \
  --style educational \
  --output .tmp/reel_script.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read relevant content strategy and social media skill bibles
4. **Choose Hook Formula** - Select pattern interrupt style (question, statement, controversy)
5. **Generate Script** - Run `.claude/skills/instagram-reel/generate_instagram_reel.py` with topic and length
6. **Validate Structure** - Ensure hook (0-3s), setup, value, and CTA sections are present
7. **Generate Caption** - Include hook expansion, value bullets, save CTA, and hashtags
8. **Output** - Save to `.tmp/reel_script.md`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--topic` | Yes | What the reel is about |
| `--length` | No | Duration in seconds: 15, 30, 60, or 90 (default: 30) |
| `--style` | No | Content style: educational, entertaining, motivational, story (default: educational) |
| `--output` | No | Output path (default: `.tmp/reel_script.md`) |

## Quality Checklist
- [ ] Hook grabs attention in first 3 seconds
- [ ] Script matches target length with timing markers
- [ ] Text overlay suggestions included for each section
- [ ] Caption includes hook expansion and value bullets
- [ ] Hashtags are relevant and mix broad + niche
- [ ] CTA is clear and action-oriented
- [ ] Follows agency brand voice

## Related Directives
- `directives/instagram_reel_script.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_content_strategy_growth.md`
- `skills/SKILL_BIBLE_persuasion_speaking.md`
- `skills/SKILL_BIBLE_social_media_marketing_agency_.md`
