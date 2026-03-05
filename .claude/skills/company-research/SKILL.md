---
name: company-research
description: Conduct deep company and offer research using Perplexity AI. Use when user asks to research a company, analyze a business, or investigate a competitor.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Company & Offer Research

## Goal
Conduct comprehensive market research on a company and its offer using Perplexity AI. Produces structured research output for downstream workflows (funnels, emails, copy).

## Prerequisites
- `PERPLEXITY_API_KEY` in `.env`
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` (optional, for synthesis)

## Execution Command

```bash
python3 .claude/skills/company-research/research_company_offer.py \
  --company "Target Company" \
  --website "https://targetcompany.com" \
  --offer "Their main product"
```

## Process Steps
1. **Load Directive** - Read `directives/company_market_research.md`
2. **Company Profile** - Research company background, size, funding, leadership
3. **Market Analysis** - Identify market size, trends, growth trajectory
4. **Competitor Mapping** - Find and analyze top 3-5 competitors
5. **Offer Analysis** - Evaluate product/service, pricing, positioning
6. **Target Audience** - Define ICP, pain points, buying triggers
7. **SWOT Analysis** - Strengths, weaknesses, opportunities, threats
8. **Synthesize** - Compile into structured research document

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--company` | Yes | Company name |
| `--website` | Yes | Company website URL |
| `--offer` | No | Specific product/service to research |
| `--output` | No | Output path (default: `.tmp/research.json`) |

## Output Format
Structured JSON/markdown with: company profile, market analysis, competitors, audience insights, SWOT, and recommended positioning.

## Quality Checklist
- [ ] 5+ data sources cited
- [ ] Competitor analysis with 3+ competitors
- [ ] Target audience clearly defined
- [ ] Pain points and buying triggers identified
- [ ] SWOT analysis complete
- [ ] Output saved to `.tmp/`

## Related Directives
- `directives/company_market_research.md`
- `directives/ultimate_niche_research.md`
