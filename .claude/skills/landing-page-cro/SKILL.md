---
name: landing-page-cro
description: Analyze landing pages for conversion rate optimization with AI-powered recommendations. Use when user asks to analyze a landing page, audit CRO, review a funnel page, or optimize conversions.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Landing Page CRO Analyzer

## Goal
Analyze landing pages for conversion rate optimization opportunities, providing actionable copy, layout, and UX recommendations with AI-powered insights.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/landing-page-cro/analyze_landing_page.py \
  --url "https://example.com/landing" \
  --client "Acme Corp" \
  --funnel_type "VSL" \
  --industry "SaaS" \
  --metrics "2% conversion, 45% bounce rate" \
  --output_dir ".tmp/cro_analysis" \
  --deep
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_landing_page_ai_mastery.md`
4. **Fetch Page** - Retrieve and convert landing page to markdown for analysis
5. **Analyze Copy** - Evaluate headline, subheadline, body copy, CTAs for persuasion and clarity
6. **Analyze Layout** - Review above-the-fold content, visual hierarchy, trust elements
7. **CRO Element Check** - Audit social proof, urgency, risk reversal, objection handling
8. **Generate Recommendations** - Prioritized improvements with estimated impact
9. **Output** - Save CRO analysis report to output directory

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--url` | Yes | Landing page URL to analyze |
| `--client` | No | Client name |
| `--funnel_type` | No | Type of funnel (VSL, Webinar, Lead Magnet, etc.) |
| `--industry` | No | Industry or niche |
| `--metrics` | No | Current funnel metrics (conversion rate, bounce rate, etc.) |
| `--output_dir` | No | Output directory (default: `.tmp/cro_analysis`) |
| `--deep` | No | Include deep copy analysis (flag) |

## Quality Checklist
- [ ] Headline and subheadline evaluated for clarity and persuasion
- [ ] CTA analyzed for visibility, copy, and placement
- [ ] Social proof elements identified and assessed
- [ ] Above-the-fold content reviewed
- [ ] Mobile responsiveness considered
- [ ] Recommendations prioritized by estimated impact
- [ ] Specific rewrite suggestions included (not just "improve X")
- [ ] Current metrics acknowledged in analysis

## Related Directives
- `directives/landing_page_cro_analyzer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_landing_page_ai_mastery.md`
- `skills/SKILL_BIBLE_landing_page_copywriting.md`
- `skills/SKILL_BIBLE_high_converting_landing_pages_.md`
- `skills/SKILL_BIBLE_funnel_copywriting_mastery.md`
- `skills/SKILL_BIBLE_landing_page_design_tutorial_h.md`
