---
name: niche-research
description: Conduct deep niche research with market analysis, ICP profiles, competitive landscape, and go-to-market strategy. Use when user asks to research a niche, validate a market, analyze an industry, build an ICP, or create a go-to-market plan.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Niche Research System

## Goal
Complete niche research and validation system for agencies exploring new markets. Produces comprehensive market analysis, ideal customer profiles (ICP), competitive landscape mapping, demand validation, pricing analysis, and go-to-market strategy with 30/60/90 day launch plans.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` — AI analysis
- `PERPLEXITY_API_KEY` in `.env` — Market research

## Execution Command

```bash
python3 .claude/skills/niche-research/research_market_deep.py \
  --business "AI Marketing Agency" \
  --industry "Digital marketing for dental practices" \
  --audience "Dental practice owners with 2-10 locations" \
  --competitors "SmileMarketing,DentalMarketing.net" \
  --output ".tmp/niche_research/dental_practices"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bibles** - Read `skills/SKILL_BIBLE_agency_positioning_niching.md` and `skills/SKILL_BIBLE_competitive_analysis.md`
4. **Market Analysis** - Research total addressable market, serviceable market, growth trends, industry dynamics, and key players
5. **ICP Development** - Build firmographic profile (company size, industry, tech stack) and buyer persona (title, goals, pain points, buying triggers)
6. **Competitive Analysis** - Map direct and indirect competitors with pricing, positioning, strengths, weaknesses, and differentiation opportunities
7. **Demand Validation** - Check Google search volume, social media discussions, industry forums, job postings, and funding activity
8. **Go-to-Market Strategy** - Create positioning, unique value proposition, lead generation channels, pricing strategy, and 30/60/90 day launch plan
9. **Deliver Research** - Save all research documents to output directory

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--business` | Yes | Business/product name |
| `--industry` | Yes | Industry/market to research |
| `--audience` | Yes | Target audience description |
| `--competitors` | No | Known competitors (comma-separated) |
| `--output` | No | Output path without extension (default: .tmp/market_research) |
| `--quick` | No | Quick mode with fewer research queries (flag) |

## Quality Checklist
- [ ] Market size quantified (TAM $1B+)
- [ ] Growth rate identified (5%+ YoY minimum)
- [ ] ICP clearly defined with firmographics and buyer persona
- [ ] 5+ competitors analyzed with pricing
- [ ] Demand validated through multiple signals
- [ ] Pricing researched against market rates
- [ ] GTM plan is actionable with specific milestones
- [ ] Differentiation opportunities identified

## Related Directives
- `directives/ultimate_niche_research.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_agency_positioning_niching.md`
- `skills/SKILL_BIBLE_competitive_analysis.md`
- `skills/SKILL_BIBLE_offer_positioning.md`
- `skills/SKILL_BIBLE_competitive_advantage_strategy.md`
