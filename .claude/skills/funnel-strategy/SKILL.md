---
name: funnel-strategy
description: Generate comprehensive funnel strategy blueprints with architecture recommendations and implementation roadmaps. Use when user asks to plan a funnel, create a funnel strategy, design a funnel architecture, or build a funnel outline.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Funnel Outline & Strategy Agent

## Goal
Analyze business inputs and generate a comprehensive funnel strategy blueprint with funnel type recommendation, page-by-page outlines, traffic strategy, and implementation roadmap.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- Google OAuth credentials (`credentials.json`) for Google Docs output

## Execution Command

```bash
python3 .claude/skills/funnel-strategy/generate_funnel_strategy.py \
  --business "Company Name" \
  --business_type "info_product" \
  --industry "Marketing" \
  --audience "Agency owners" \
  --objective "lead_gen" \
  --price "$997" \
  --pain_points "Low conversion rates,High CAC,No automation" \
  --differentiator "AI-powered funnel optimization"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_funnel_copywriting_mastery.md` for funnel expertise
4. **Gather Business Profile** - Collect all business inputs and pain points
5. **Research Phase** - AI researches optimal funnel type for the business
6. **Strategy Phase** - Generate funnel architecture, page outlines, and traffic strategy
7. **Format** - Convert to clean markdown with proper hierarchy
8. **Deliver** - Save to `.tmp/` and create Google Doc

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--business` | Yes | Business or product name |
| `--business_type` | No | Business type: info_product, saas, ecommerce, agency, coaching, consulting |
| `--industry` | No | Industry or niche |
| `--audience` | No | Target audience description |
| `--objective` | No | Funnel objective: lead_gen, sales, webinar, application, challenge |
| `--price` | No | Core offer price |
| `--pain_points` | No | Top customer pain points (comma-separated) |
| `--differentiator` | No | Unique differentiator |
| `--output_dir` | No | Output directory (default: .tmp/funnel_strategy) |

## Quality Checklist
- [ ] Funnel type recommendation with rationale
- [ ] Page-by-page outline for each funnel step
- [ ] Traffic strategy with channel recommendations
- [ ] Implementation roadmap with timeline
- [ ] Tech stack recommendations
- [ ] KPIs and success metrics defined

## Related Directives
- `directives/funnel_outline_strategy_agent.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_funnel_copywriting_mastery.md`
- `skills/SKILL_BIBLE_agency_funnel_building.md`
- `skills/SKILL_BIBLE_sales_funnel_structure.md`
- `skills/SKILL_BIBLE_call_funnel_mastery.md`
- `skills/SKILL_BIBLE_digital_product_funnel.md`
