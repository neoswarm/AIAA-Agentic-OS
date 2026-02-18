---
name: vsl-script
description: Generate high-converting VSL scripts using proven direct response frameworks. Use when user asks to write a VSL, create a video sales letter, generate VSL script, or write sales video copy.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# VSL Script Writer

## Goal
Generate complete Video Sales Letter scripts using the proven 10-part framework from VSL skill bibles, with multiple hook options, delivery notes, and timestamps optimized for B2B service businesses selling $1K-$20K offers.

## Prerequisites
- `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY` - For Claude Opus script generation
- Skill bibles: `skills/SKILL_BIBLE_vsl_writing_production.md`, `skills/SKILL_BIBLE_vsl_script_mastery_fazio.md`

## Execution Command

```bash
python3 .claude/skills/vsl-script/generate_vsl_script.py \
  --research .tmp/research/company_research.json \
  --length "medium" \
  --style "education" \
  --output .tmp/vsl/vsl_script.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bibles** - Read VSL writing frameworks from `skills/SKILL_BIBLE_vsl_writing_production.md` and `skills/SKILL_BIBLE_vsl_script_mastery_fazio.md`
4. **Prepare Research** - Ensure market research dossier is available (JSON from research workflow)
5. **Generate Hooks** - Create 3 hook options with different psychological triggers
6. **Generate Full Script** - Write complete 10-part VSL script following framework
7. **Quality Validation** - Verify word count, structure adherence, and proof elements

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--research` | Yes | Path to research JSON dossier from company research workflow |
| `--length` | No | VSL length: mini (1000+ words), medium (3000+ words), long (10000+ words) (default: medium) |
| `--style` | No | VSL style: education, story, case-study (default: education) |
| `--output` | No | Output file path (default: .tmp/vsl/vsl_script.md) |

## Quality Checklist
- [ ] Hook stops scroll within 3 seconds
- [ ] Problem agitation is specific (not generic platitudes)
- [ ] Mechanism has unique name/insight
- [ ] At least 3 proof/case study elements included
- [ ] Price anchored with value stack
- [ ] CTA is clear and specific (book call)
- [ ] Script meets minimum word count (mini: 1000, medium: 3000, long: 10000)
- [ ] All 10 parts present: Hook, Problem, Credibility, Solution, Mechanism, Social Proof, Offer, Urgency, Guarantee, CTA
- [ ] Delivery notes and graphics cues included

## Related Directives
- `directives/vsl_script_writer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_vsl_writing_production.md`
- `skills/SKILL_BIBLE_vsl_script_mastery_fazio.md`
- `skills/SKILL_BIBLE_funnel_copywriting_mastery.md`
