---
name: case-study
description: Generate client case studies from results data. Use when user asks to write a case study, document client results, or create a success story.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Case Study Generator

## Goal
Generate compelling client case studies from results data, following the Challenge → Solution → Results framework.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/case-study/generate_case_study.py \
  --client "Acme Corp" \
  --industry "SaaS" \
  --challenge "Low conversion rates" \
  --solution "Implemented AI-powered funnels" \
  --results "300% increase in conversions" \
  --output .tmp/case_study.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md`, `context/brand_voice.md`
2. **Client Background** - Company overview and initial situation
3. **Challenge** - Define the problem in detail with data
4. **Solution** - Describe what was implemented step-by-step
5. **Results** - Quantify outcomes with specific metrics
6. **Testimonial** - Include client quote (real or template)
7. **Key Takeaways** - Lessons and insights
8. **CTA** - Drive reader to take next step

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client company name |
| `--industry` | Yes | Client's industry |
| `--challenge` | Yes | Problem they faced |
| `--solution` | Yes | What was implemented |
| `--results` | Yes | Quantified outcomes |
| `--output` | No | Output path (default: `.tmp/case_study.md`) |

## Quality Checklist
- [ ] 1500+ words
- [ ] Clear Challenge → Solution → Results flow
- [ ] Specific metrics and data points
- [ ] Client testimonial included
- [ ] Before/after comparison
- [ ] Key takeaways section
- [ ] CTA at the end
- [ ] Follows brand voice

## Related Directives
- `directives/case_study_generator.md`
- `directives/ultimate_case_study_generator.md`
