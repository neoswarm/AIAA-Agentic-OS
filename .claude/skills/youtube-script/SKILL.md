---
name: youtube-script
description: Generate optimized YouTube video scripts with hooks and structure. Use when user asks to write a YouTube script, create a video script, or plan video content.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# YouTube Script Creator

## Goal
Generate optimized YouTube video scripts with attention-grabbing hooks, clear structure, and strong CTAs.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/youtube-script/generate_youtube_script.py \
  --topic "How to Build a 6-Figure Business" \
  --length "10min" \
  --style "educational" \
  --output .tmp/youtube_script.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md`, `context/brand_voice.md`
2. **Hook** - Write a 30-second attention grabber
3. **Intro** - Set up the video promise (what they'll learn)
4. **Content Sections** - 3-5 main teaching points
5. **B-Roll Notes** - Suggest visual elements per section
6. **CTA Mid-Roll** - Subscribe/like reminder mid-video
7. **Conclusion** - Recap key points
8. **End CTA** - Final call to action (subscribe, link, comment)
9. **Title & Thumbnail** - Generate 5 title options + thumbnail ideas

## Video Length Options
| Length | Sections | Word Count |
|--------|----------|------------|
| `5min` | 3 | ~750 |
| `10min` | 5 | ~1500 |
| `15min` | 7 | ~2250 |
| `20min` | 9 | ~3000 |

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--topic` | Yes | Video topic |
| `--length` | No | Target length (default: 10min) |
| `--style` | No | educational/story/tutorial/review |
| `--audience` | No | Target audience description |
| `--output` | No | Output path |

## Quality Checklist
- [ ] Hook grabs attention in first 30 seconds
- [ ] 1500+ words for 10-minute script
- [ ] Clear structure with timestamps
- [ ] B-roll suggestions included
- [ ] Mid-roll and end CTAs
- [ ] 5 title options provided
- [ ] Thumbnail concept ideas
- [ ] Follows brand voice

## Related Directives
- `directives/youtube_script_creator.md`
- `directives/youtube_script_generator.md`
