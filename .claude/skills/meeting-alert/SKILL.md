---
name: meeting-alert
description: Research prospects when meetings are booked and create prep documents. Use when user asks to prepare for a meeting, research a prospect, create meeting prep, or handle a booked meeting alert.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Booked Meeting Alert + Prospect Research

## Goal
When a meeting is booked, research the prospect with AI, generate a meeting prep document with talking points and questions, and notify via Slack.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `PERPLEXITY_API_KEY` in `.env` (for prospect research)

## Execution Command

```bash
python3 .claude/skills/meeting-alert/alert_booked_meeting.py \
  --name "John Smith" \
  --company "Acme Corp" \
  --meeting_time "2026-01-15 2:00 PM" \
  --meeting_type "discovery" \
  --output ".tmp/meeting_prep.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If existing client, read `clients/{client}/*.md`
3. **Research Prospect** - Use Perplexity to research company and person (what they do, news, background)
4. **Generate Prep Sheet** - AI creates quick facts, pre-call checklist, talking points, and questions
5. **Save Document** - Write prep doc to `.tmp/meeting_prep.md`
6. **Notify** - Optionally send Slack alert with meeting details and prep summary

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--name` | Yes | Prospect's full name |
| `--company` | Yes | Prospect's company name |
| `--meeting_time` | Yes | Meeting date and time |
| `--meeting_type` | No | Type of meeting (default: "discovery") |
| `--output` | No | Output file path (default: `.tmp/meeting_prep.md`) |

## Quality Checklist
- [ ] Company overview included with recent news
- [ ] Prospect background researched
- [ ] 5+ personalized talking points generated
- [ ] 3+ thoughtful questions to ask
- [ ] Potential pain points identified
- [ ] Meeting strategy outlined

## Related Directives
- `directives/booked_meeting_alert_prospect_research.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_sales_call_preparation.md`
- `skills/SKILL_BIBLE_prospect_research.md`
