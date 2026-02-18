---
name: prospect-research
description: Generate comprehensive prospect dossiers for sales calls and outreach. Use when user asks to research a prospect, prepare for a meeting, or build a prospect profile.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Prospect Research Agent

## Goal
Generate comprehensive dossiers on prospects and companies for personalized outreach and meeting preparation.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `PERPLEXITY_API_KEY` for deep web research

## Execution Command

```bash
python3 .claude/skills/prospect-research/research_prospect_deep.py \
  --name "John Smith" \
  --company "Acme Corp" \
  --domain "acmecorp.com" \
  --output .tmp/dossier.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` for positioning context
2. **Person Research** - LinkedIn profile, background, career history
3. **Company Research** - Company overview, recent news, funding
4. **Pain Point Analysis** - Identify likely challenges based on role/industry
5. **Connection Points** - Find shared interests, mutual connections
6. **Talking Points** - Generate personalized conversation starters
7. **Compile Dossier** - Structured output with all findings

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--name` | Yes | Prospect's full name |
| `--company` | Yes | Prospect's company |
| `--domain` | No | Company domain for web research |
| `--title` | No | Job title for context |
| `--output` | No | Output path (default: `.tmp/dossier.json`) |

## Output Format
Structured dossier with: prospect bio, company overview, pain points, talking points, connection opportunities, and recommended approach.

## Quality Checklist
- [ ] Prospect background verified from multiple sources
- [ ] Company context included
- [ ] 3+ personalized talking points
- [ ] Pain points mapped to our services
- [ ] Recommended outreach approach
- [ ] Output saved to `.tmp/`

## Related Directives
- `directives/ai_prospect_researcher.md`
- `directives/booked_meeting_alert_prospect_research.md`
