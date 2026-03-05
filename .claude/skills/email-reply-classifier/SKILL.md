---
name: email-reply-classifier
description: Classify email replies by intent and sentiment using AI. Use when user asks to classify email responses, sort inbox replies, or triage campaign replies.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Email Reply Classifier

## Goal
Automatically classify email replies by intent (interested, meeting request, not interested, out of office, unsubscribe) and route them for appropriate follow-up action.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
# Classify a single email
python3 .claude/skills/email-reply-classifier/classify_email_reply.py \
  --email "Thanks for reaching out! I'd love to learn more about your service. Can we schedule a call?" \
  --output .tmp/classification.json

# Classify from a file
python3 .claude/skills/email-reply-classifier/classify_email_reply.py \
  --file .tmp/reply.txt \
  --output .tmp/classification.json

# Batch classify multiple emails
python3 .claude/skills/email-reply-classifier/classify_email_reply.py \
  --batch replies.json \
  --output .tmp/batch_classification.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Receive Email Content** - Get email text, file, or batch JSON
4. **Classify Intent** - Run `.claude/skills/email-reply-classifier/classify_email_reply.py` for AI classification
5. **Route by Category** - Map classification to follow-up action
6. **Output** - Save classifications to `.tmp/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--email` | No* | Email text to classify (inline) |
| `--file` | No* | File containing email text |
| `--batch` | No* | JSON file with multiple emails |
| `--output` | No | Output file path |

*One of `--email`, `--file`, or `--batch` is required.

## Quality Checklist
- [ ] Classification confidence score above 0.8
- [ ] Correct intent category assigned (interested, meeting, question, not interested, OOO, unsubscribe)
- [ ] Sentiment analysis included (positive, neutral, negative)
- [ ] Suggested response or action provided
- [ ] Priority level assigned correctly
- [ ] Key phrases extracted from email

## Related Directives
- `directives/email_reply_classifier.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_cold_email_mastery.md`
- `skills/SKILL_BIBLE_cold_email_inbox_mgmt.md`
- `skills/SKILL_BIBLE_cold_email_analytics.md`
- `skills/SKILL_BIBLE_email_deliverability.md`
