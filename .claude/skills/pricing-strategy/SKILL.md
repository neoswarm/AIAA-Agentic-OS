---
name: pricing-strategy
description: Create complete pricing and packaging systems with tiers, ROI calculators, value stacks, and objection handlers. Use when user asks to design pricing, create packages, build a pricing strategy, generate a ROI calculator, or optimize agency pricing.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Agency Pricing Strategy

## Goal
Create complete pricing and packaging systems for agencies optimizing their revenue. Produces market pricing analysis, multi-tier package structures, value stacks, ROI calculators, value propositions, and objection handlers for sales conversations.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` — AI analysis
- `PERPLEXITY_API_KEY` in `.env` — Market research

## Execution Command

```bash
python3 .claude/skills/pricing-strategy/create_proposal.py \
  proposal_data.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bibles** - Read `skills/SKILL_BIBLE_pricing_strategy.md`, `skills/SKILL_BIBLE_premium_pricing_strategy.md`, and `skills/SKILL_BIBLE_high_ticket_offer_creation.md`
4. **Market Analysis** - Research competitor pricing, market rates, value perception, and willingness to pay
5. **Define Pricing Models** - Evaluate retainer, performance, project, and hybrid models for the service
6. **Create Package Structure** - Design 3-tier packages: Starter (entry), Growth (most popular), and Scale (premium)
7. **Build Value Stack** - Define core service, add-ons, bonuses, and risk reducers for each tier
8. **Generate ROI Calculator** - Create inputs (current metrics, benchmarks) and outputs (projected ROI, break-even, monthly/annual returns)
9. **Write Value Propositions** - Craft unique value propositions for each tier and audience segment
10. **Create Objection Handlers** - Write responses for "too expensive", "competitor charges less", "need to think about it", and "what if it doesn't work"
11. **Deliver Strategy** - Save all materials to `.tmp/pricing_strategy/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `input_file` | Yes | JSON file with proposal/pricing data (or pass via stdin) |

## Quality Checklist
- [ ] Market rates researched for the service category
- [ ] Value quantified with ROI projections
- [ ] 3 pricing tiers clearly differentiated
- [ ] Each tier has defined deliverables and pricing
- [ ] ROI calculator shows clear return on investment
- [ ] 4+ objection handlers written
- [ ] Value stack includes bonuses and risk reducers
- [ ] Close rate target: 25%+

## Related Directives
- `directives/ultimate_pricing_strategy.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_pricing_strategy.md`
- `skills/SKILL_BIBLE_premium_pricing_strategy.md`
- `skills/SKILL_BIBLE_pricing_psychology_negotiation.md`
- `skills/SKILL_BIBLE_offer_creation_pricing.md`
- `skills/SKILL_BIBLE_high_ticket_offer_creation.md`
- `skills/SKILL_BIBLE_roi_calculator_creation.md`
