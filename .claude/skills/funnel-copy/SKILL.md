---
name: funnel-copy
description: Generate complete funnel copy including sales pages, email sequences, and ad copy using AI research. Use when user asks to write funnel copy, create a sales funnel, build funnel content, or generate sales page and email sequences.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Funnel Copywriter

## Goal
Generate complete funnel copy (sales page, email sequences, and ad copy) using AI market research and proven copywriting frameworks like PROPS, PAS, and AIDA.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `PERPLEXITY_API_KEY` in `.env` (for market research step)
- `GOOGLE_APPLICATION_CREDENTIALS` in project root (for Google Docs delivery)

## Execution Command

```bash
python3 .claude/skills/funnel-copy/generate_funnel_copy.py \
  --business "Company Name" \
  --industry "SaaS" \
  --audience "Marketing agency owners" \
  --funnel_type "VSL" \
  --benefits "benefit1,benefit2,benefit3" \
  --pain_points "pain1,pain2,pain3" \
  --value_prop "Unique value proposition" \
  --brand_voice "Professional but conversational" \
  --output_dir .tmp/funnel_output
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read funnel copywriting and sales funnel skill bibles
4. **Market Research** - AI researches audience pain points, competitors, and positioning
5. **Funnel Strategy** - Generate funnel blueprint with Power of One analysis
6. **Sales Page Copy** - Generate high-converting sales page following PROPS formula
7. **Email Sequence** - Generate value-dense email flow integrated with funnel strategy
8. **Output** - Save all assets to `.tmp/funnel_output/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--business` | No | Business or product name |
| `--industry` | No | Industry or business type |
| `--audience` | No | Target audience description |
| `--funnel_type` | No | Funnel type: VSL, Webinar, Sales Page (default: Sales Page) |
| `--benefits` | No | Comma-separated top product benefits |
| `--pain_points` | No | Comma-separated pain points solved |
| `--value_prop` | No | Unique value proposition |
| `--brand_voice` | No | Brand voice and tone (default: Professional but conversational) |
| `--offers` | No | Special offers or urgency elements |
| `--output_dir` | No | Output directory (default: `.tmp/funnel_output`) |
| `--skip_research` | No | Flag to skip market research step |
| `--research_file` | No | Path to pre-generated market research JSON |

## Quality Checklist
- [ ] Market research dossier includes audience personas and VOC phrases
- [ ] Funnel strategy has Power of One analysis (one problem, desire, method, promise)
- [ ] Sales page follows PROPS structure with 3-layer problem depth
- [ ] Unique mechanism is named and differentiated
- [ ] Offer stack with value breakdown included
- [ ] Email sequence is 5+ emails with value-driven content
- [ ] Each email has compelling subject line and clear CTA
- [ ] Sales page is 2000+ words
- [ ] Each email is 300+ words
- [ ] Follows agency brand voice

## Related Directives
- `directives/funnel_copywriter.md`
- `directives/ai_landing_page_generator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_funnel_copywriting_mastery.md`
- `skills/SKILL_BIBLE_sales_funnel_structure.md`
- `skills/SKILL_BIBLE_sales_funnel_building_high_con.md`
- `skills/SKILL_BIBLE_landing_page_copywriting.md`
- `skills/SKILL_BIBLE_copywriting_fundamentals.md`
- `skills/SKILL_BIBLE_copywriting_agency_direct_resp.md`
- `skills/SKILL_BIBLE_agency_funnel_building.md`
- `skills/SKILL_BIBLE_vsl_funnel_structure_sales_pag.md`
