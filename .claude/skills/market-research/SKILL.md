---
name: market-research
description: Conduct deep market and industry research using Perplexity Deep Research. Use when user asks to analyze a market, research an industry, or identify market opportunities.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Deep Market Research

## Goal
Conduct comprehensive market and industry research using Perplexity Deep Research via OpenRouter. Produces structured analysis for strategy, funnels, and content planning.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` (uses Perplexity Deep Research model)
- `OPENAI_API_KEY` as fallback

## Execution Command

```bash
python3 .claude/skills/market-research/research_market_deep.py \
  --business "Agency Accelerator" \
  --industry "Marketing Agency" \
  --audience "Agency owners doing 10-50k/month" \
  --output .tmp/market_research.json
```

## Process Steps
1. **Define Scope** - Clarify industry, business, and audience
2. **Market Size** - TAM, SAM, SOM analysis
3. **Trends** - Current and emerging market trends
4. **Competitor Landscape** - Map key players and their positioning
5. **Audience Analysis** - Demographics, psychographics, pain points
6. **Opportunity Gaps** - Underserved segments and unmet needs
7. **Pricing Analysis** - Market pricing benchmarks
8. **Synthesize** - Compile into structured research document

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--business` | Yes | Business/product name |
| `--industry` | Yes | Industry vertical |
| `--audience` | Yes | Target audience description |
| `--output` | No | Output path (default: `.tmp/market_research.json`) |

## Output Format
Structured JSON with: market overview, size estimates, trends, competitor map, audience insights, opportunity gaps, and strategic recommendations.

## Quality Checklist
- [ ] Market size estimates included (TAM/SAM/SOM)
- [ ] 5+ competitors analyzed
- [ ] Audience pain points clearly defined
- [ ] 3+ market trends identified
- [ ] Opportunity gaps highlighted
- [ ] Pricing benchmarks provided
- [ ] Actionable recommendations included

## Related Directives
- `directives/company_market_research.md`
- `directives/ultimate_niche_research.md`
