---
name: utm-generator
description: Generate consistent UTM-tagged URLs for campaign tracking. Use when user asks to create UTM links, generate tracking URLs, tag campaign links, or set up UTM parameters.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# UTM Link Generator

## Goal
Generate consistent, properly formatted UTM-tagged URLs following naming conventions, with optional content variants and link shortening for campaign attribution tracking.

## Prerequisites
- No API keys required for basic UTM generation (local script)

## Execution Command

```bash
python3 .claude/skills/utm-generator/generate_utm.py \
  --url "https://example.com/landing" \
  --source "linkedin" \
  --medium "social" \
  --campaign "q1_launch" \
  --content "video_ad_v1" \
  --variants "carousel_v1,static_v1,story_v1" \
  --output .tmp/utm_urls.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Gather Parameters** - Base URL, source, medium, campaign name, content variants
4. **Generate UTM URLs** - Run script to create tagged URLs with proper naming conventions
5. **Review Output** - Verify parameter consistency and naming standards

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--url` | Yes | Base landing page URL |
| `--source` | Yes | Traffic source (google, linkedin, facebook, email) |
| `--medium` | Yes | Channel type (cpc, social, email, paid_social, organic_social) |
| `--campaign` | Yes | Campaign name (use lowercase, underscores) |
| `--term` | No | UTM term for keyword tracking |
| `--content` | No | UTM content for ad/post variation |
| `--variants` | No | Comma-separated content variants to generate multiple URLs |
| `--output` | No | Output file path (default: .tmp/utm_urls.md) |

## Quality Checklist
- [ ] All UTM parameters lowercase with no spaces
- [ ] Naming convention consistent (source_medium_campaign format)
- [ ] Base URL properly encoded
- [ ] Variants generated if requested
- [ ] Campaign parameter table included in output
- [ ] URLs are valid and clickable

## Related Directives
- `directives/utm_generator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_marketing_analytics.md`
- `skills/SKILL_BIBLE_campaign_tracking.md`
