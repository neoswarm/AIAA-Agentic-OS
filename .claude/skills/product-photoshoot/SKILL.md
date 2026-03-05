---
name: product-photoshoot
description: Generate 5 AI product photoshoot images using Fal.ai with brand-informed prompts. Use when user asks to create product photos, generate product images, make AI photoshoot, or create product visuals.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Product Photoshoot Generator

## Goal
Generate 5 professional AI product photoshoot images across distinct styles (Hero, Lifestyle, Detail, Aspirational, Creative) using Fal.ai Nano Banana Pro, with brand-informed prompts from Perplexity research.

## Prerequisites
- `FAL_API_KEY` in `.env` (for image generation)
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env` (for prompt generation and vision analysis)
- `PERPLEXITY_API_KEY` in `.env` (for brand research)
- Optional: `SLACK_BOT_TOKEN` and `SLACK_CONTENT_CHANNEL_ID` (for notification)
- Optional: `GOOGLE_DRIVE_FOLDER_ID` (for upload)

## Execution Command

```bash
python3 .claude/skills/product-photoshoot/generate_product_photoshoot.py \
  --image "path/to/product.png" \
  --brand "Brand Name" \
  --website "brand.com" \
  --niche "Skincare"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Upload Product Image** - Upload to Fal.ai CDN
4. **Analyze Product** - GPT-4o vision analyzes the product image
5. **Research Brand** - Perplexity researches brand identity, target audience, and photography style
6. **Generate Prompts** - AI creates 5 scene-specific photoshoot prompts
7. **Create Images** - Fal.ai Nano Banana Pro generates 5 images
8. **Upload to Drive** - Upload results to Google Drive folder
9. **Notify via Slack** - Send completion notification with Drive link

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--image` | Yes | Path to product image (PNG or JPEG) |
| `--brand` | Yes | Brand name |
| `--website` | Yes | Brand website URL |
| `--niche` | Yes | Product niche (e.g., "Skincare", "Tech", "Fashion") |

## Quality Checklist
- [ ] All 5 photo styles generated (Hero, Lifestyle, Detail, Aspirational, Creative)
- [ ] Images match brand aesthetic and target audience
- [ ] Product clearly visible and recognizable in all images
- [ ] Resolution suitable for e-commerce use
- [ ] Images uploaded to Google Drive
- [ ] Slack notification sent

## Related Directives
- `directives/product_photoshoot_generator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_video_marketing_agency_video_p.md`
