---
name: product-description
description: Generate SEO-optimized e-commerce product descriptions with benefit-focused copy. Use when user asks to write a product description, create product listings, generate e-commerce copy, or write Shopify/Amazon/Etsy descriptions.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Product Description Writer

## Goal
Generate compelling e-commerce product descriptions optimized for SEO and conversions, including benefit-focused copy, meta tags, and platform-specific formatting for Shopify, Amazon, Etsy, or general use.

## Prerequisites
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/product-description/generate_product_description.py \
  --product "Premium Wireless Headphones" \
  --features "Active noise cancellation, 40hr battery, Bluetooth 5.3, memory foam cushions" \
  --audience "Remote workers and commuters" \
  --tone professional \
  --platform shopify \
  --output .tmp/product_desc.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Analyze Product** - Parse features and identify key benefits for target audience
4. **Select Tone** - Match tone to product category (premium, casual, technical, playful)
5. **Generate Description** - Run `.claude/skills/product-description/generate_product_description.py` with product details
6. **Create SEO Elements** - Generate meta title (50-60 chars), meta description (150-160 chars), alt text
7. **Format for Platform** - Apply Shopify HTML, Amazon bullet points, or Etsy story format
8. **Output** - Save to `.tmp/product_desc.md`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--product` | Yes | Product name |
| `--features` | Yes | Key product features (comma-separated or descriptive) |
| `--audience` | No | Target audience description |
| `--tone` | No | Writing tone: premium, casual, technical, playful (default: professional) |
| `--platform` | No | E-commerce platform: shopify, amazon, etsy, general (default: shopify) |
| `--output` | No | Output path (default: `.tmp/product_desc.md`) |

## Quality Checklist
- [ ] Headline is benefit-focused, not just feature-listing
- [ ] Features translated into customer benefits
- [ ] Opening hook addresses customer need or desire
- [ ] SEO meta title is 50-60 characters
- [ ] SEO meta description is 150-160 characters
- [ ] Keywords naturally integrated (no stuffing)
- [ ] Formatted correctly for target platform
- [ ] Specifications section with concrete details
- [ ] Clear CTA with urgency if applicable
- [ ] Follows agency brand voice

## Related Directives
- `directives/product_description_writer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_ecommerce_agency_shopify_agenc.md`
- `skills/SKILL_BIBLE_ecommerce_email_marketing.md`
- `skills/SKILL_BIBLE_copywriting_fundamentals.md`
- `skills/SKILL_BIBLE_persuasion_speaking.md`
