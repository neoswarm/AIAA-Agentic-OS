---
name: ticket-triage
description: Auto-classify and prioritize support tickets with AI. Use when user asks to triage tickets, classify support requests, prioritize incoming tickets, or route customer issues.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Ticket Triage

## Goal
Automatically classify support tickets by category (billing, technical, bug, etc.), priority (critical/high/medium/low), and sentiment, then route to the appropriate team with SLA tracking and suggested responses.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` - For AI classification

## Execution Command

```bash
python3 .claude/skills/ticket-triage/triage_tickets.py \
  --ticket "My payment won't go through" \
  --subject "Payment issue" \
  --output .tmp/triage.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Submit Ticket** - Provide ticket content (text or file)
4. **Run Triage** - Script classifies category, priority, sentiment, complexity
5. **Review Results** - Verify classification accuracy and routing suggestion

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--ticket` | Yes* | Ticket text content (*required if no --file) |
| `--subject` | No | Ticket subject line |
| `--file` | No | File containing ticket text (alternative to --ticket) |
| `--output` | No | Output file path (default: .tmp/triage.json) |

## Quality Checklist
- [ ] Category correctly classified (billing, technical, feature_request, account, bug, general, urgent)
- [ ] Priority assigned (critical, high, medium, low)
- [ ] Sentiment detected (angry, frustrated, neutral, positive)
- [ ] Complexity assessed (simple, moderate, complex)
- [ ] Suggested assignee team identified
- [ ] Auto-response possibility flagged
- [ ] Related tickets referenced if applicable
- [ ] JSON output valid and complete

## Related Directives
- `directives/ticket_triage.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_customer_support.md`
- `skills/SKILL_BIBLE_helpdesk_automation.md`
