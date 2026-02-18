---
name: meeting-prep
description: Auto-prepare for Calendly sales calls with AI research and talking points. Use when user asks to prepare for a Calendly meeting, research a booked call, generate meeting prep, or create a sales call prep document.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Calendly Meeting Prep

## Goal
Automatically prepare for sales calls when someone books a Calendly meeting — research the prospect and company, generate personalized talking points, create a Google Doc prep sheet, and notify via Slack.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env`
- `PERPLEXITY_API_KEY` in `.env` (for research)
- `SLACK_WEBHOOK_URL` in `.env` (for notifications)
- `GOOGLE_OAUTH_TOKEN_JSON` in `.env` (optional, for Google Doc creation)
- `CALENDLY_API_KEY` in `.env` (optional, for webhook integration)

## Execution Command

```bash
python3 .claude/skills/meeting-prep/calendly_meeting_prep.py \
  --test \
  --email "prospect@company.com" \
  --name "John Smith" \
  --company "Acme Corp"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If existing client, read `clients/{client}/*.md`
3. **Receive Trigger** - Calendly webhook fires on booking, or run manually with `--test`
4. **Extract Company** - Parse company name from Calendly form or email domain
5. **Send Instant Alert** - Slack notification with prospect details and meeting time
6. **Research Prospect** - Perplexity researches company (what they do, size, news) and person (role, background)
7. **Generate Talking Points** - Claude creates 5 personalized talking points, 3 questions, pain points, and strategy
8. **Create Google Doc** - Format research into prep document in shared folder
9. **Send Summary** - Slack message with brief summary and link to full doc

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--test` | No | Run in test mode (flag) |
| `--email` | Yes* | Prospect email (*required in test mode) |
| `--name` | Yes* | Prospect name (*required in test mode) |
| `--company` | No | Company name (extracted from email if not provided) |

## Quality Checklist
- [ ] Company name extracted correctly
- [ ] Perplexity research returns relevant data
- [ ] 5+ personalized talking points generated
- [ ] 3+ thoughtful questions included
- [ ] Pain points identified and addressable
- [ ] Google Doc formatted properly (if enabled)
- [ ] Slack alerts sent (immediate + summary)

## Related Directives
- `directives/calendly_meeting_prep.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_sales_call_preparation.md`
- `skills/SKILL_BIBLE_prospect_research.md`
