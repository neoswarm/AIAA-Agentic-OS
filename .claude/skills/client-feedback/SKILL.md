---
name: client-feedback
description: Analyze and categorize client feedback with AI-powered sentiment analysis. Use when user asks to analyze feedback, process NPS responses, categorize client comments, or generate feedback reports.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Client Feedback Collector

## Goal
Analyze client feedback using AI to extract sentiment, categorize themes, identify improvement areas, and generate actionable insights with follow-up recommendations.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/client-feedback/collect_feedback.py \
  --feedback "The onboarding was great but I wish the dashboard was faster" \
  --source "quarterly_survey" \
  --output ".tmp/feedback_analysis.json"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client-specific, read `clients/{client}/*.md`
3. **Collect Feedback** - Accept feedback text directly, from file, or batch JSON
4. **AI Analysis** - Classify sentiment, identify themes, extract praise/improvement areas
5. **Score Feedback** - Assign sentiment score (-100 to 100), urgency level, and NPS estimate
6. **Generate Actions** - Create suggested follow-up actions based on analysis
7. **Save Output** - Write structured analysis to JSON

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--feedback` | Yes* | Feedback text (*or use `--file` or `--batch`) |
| `--file` | No | File containing feedback text |
| `--batch` | No | JSON file with multiple feedback items |
| `--source` | No | Feedback source (e.g., "nps_survey", "support_ticket") |
| `--output` | No | Output file path (default: `.tmp/feedback_analysis.json`) |

## Quality Checklist
- [ ] Sentiment correctly classified (positive/negative/mixed/neutral)
- [ ] Key themes extracted
- [ ] Praise points and improvement areas separated
- [ ] Feature requests captured
- [ ] Actionable follow-up suggestions provided
- [ ] Urgency level assigned

## Related Directives
- `directives/client_feedback_collector.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_hormozi_customer_retention.md`
