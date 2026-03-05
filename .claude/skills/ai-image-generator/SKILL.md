---
name: ai-image-generator
description: Generate AI image prompts for DALL-E, Midjourney, and Stable Diffusion. Use when user asks to create image prompts, generate AI images, design ad creatives, or create visual content.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# AI Image Generator

## Goal
Generate detailed, platform-optimized image prompts for AI image tools (Midjourney, DALL-E, Stable Diffusion, Ideogram) for use in content, ads, and social media.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/ai-image-generator/generate_image_prompt.py \
  --concept "Professional businessman smiling, corporate headshot" \
  --style "photorealistic" \
  --platform "midjourney" \
  --variations 5 \
  --output ".tmp/image_prompts.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md` for brand guidelines
3. **Define Concept** - Clarify image description, use case, and style preferences
4. **Select Platform** - Choose target platform (midjourney, dalle, stable_diffusion, ideogram)
5. **Generate Prompts** - AI creates detailed prompts with style, lighting, composition, mood
6. **Output Variations** - Saves multiple prompt variations with negative prompts and platform settings

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--concept` | Yes | What you want to create |
| `--style` | No | Style: photorealistic, illustration, 3d, cartoon, abstract, minimalist (default: photorealistic) |
| `--platform` | No | Target platform: midjourney, dalle, stable_diffusion, ideogram (default: midjourney) |
| `--variations` | No | Number of prompt variations (default: 5) |
| `--output` | No | Output file path (default: `.tmp/image_prompts.md`) |

## Quality Checklist
- [ ] Each prompt includes subject, style, lighting, composition, and mood
- [ ] Negative prompts included to avoid unwanted elements
- [ ] Platform-specific parameters included (e.g., --ar, --v for Midjourney)
- [ ] Multiple variations provided with different approaches
- [ ] Prompts are detailed and production-ready

## Related Directives
- `directives/ai_image_generator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_ai_image_generation.md`
