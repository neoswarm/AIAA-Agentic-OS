---
name: thumbnail-generator
description: Generate click-worthy YouTube thumbnail concepts and designs. Use when user asks to create thumbnails, design YouTube thumbnails, generate thumbnail ideas, or optimize video thumbnails.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# YouTube Thumbnail Generator

## Goal
Generate click-worthy YouTube thumbnail concepts with optimized text overlays, color schemes, facial expressions, and composition based on proven high-CTR patterns.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/thumbnail-generator/generate_thumbnail_ideas.py \
  --title "5 Cold Email Mistakes Killing Your Replies" \
  --niche "business" \
  --style "bold" \
  --output ".tmp/thumbnail_ideas.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Analyze Title** - Parse video title for thumbnail angles and hooks
4. **Generate Concepts** - Create 5 thumbnail concepts with layout, text, colors, and psychology
5. **Output Specs** - Save design-ready specifications including text overlay rules (max 5 words, high contrast)

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--title` | Yes | Video title to create thumbnails for |
| `--niche` | No | Content niche (default: "general") |
| `--style` | No | Thumbnail style preference (e.g., bold, clean, dramatic, minimal) |
| `--output` | No | Output file path (default: `.tmp/thumbnail_ideas.md`) |

## Quality Checklist
- [ ] 5 distinct thumbnail concepts generated
- [ ] Each concept includes visual layout, text overlay, color scheme, and psychology explanation
- [ ] Text overlays are 3-5 words max
- [ ] Color schemes use high-contrast, attention-grabbing combinations
- [ ] Facial expression guidance included where applicable
- [ ] Concepts follow proven thumbnail formulas (before/after, number+benefit, question, statement)

## Related Directives
- `directives/ai_thumbnail_generator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_youtube_growth_mastery.md`
