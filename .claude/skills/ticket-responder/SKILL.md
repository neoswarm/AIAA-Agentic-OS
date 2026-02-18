---
name: ticket-responder
description: Generate AI-powered support ticket responses. Use when user asks to respond to a support ticket, draft ticket reply, create support response, or handle customer inquiry.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Ticket Auto-Responder

## Goal
Generate concise, solution-focused support ticket responses with initial reply, follow-up escalation path, and internal notes using AI classification by category and tone.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` - For AI response generation

## Execution Command

```bash
python3 .claude/skills/ticket-responder/generate_ticket_response.py \
  --ticket "I can't log into my account" \
  --category "account" \
  --customer_name "Jane Doe" \
  --tone "empathetic" \
  --output .tmp/ticket_response.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Classify Ticket** - Determine category, priority, and appropriate tone
4. **Generate Response** - Run script with ticket content and classification
5. **Review Output** - Verify solution accuracy and tone appropriateness

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--ticket` | Yes | Ticket content / customer message |
| `--category` | No | Category: billing, technical, account, feature, bug, general (default: general) |
| `--customer_name` | No | Customer's name for personalization |
| `--tone` | No | Response tone: friendly, formal, empathetic (default: friendly) |
| `--output` | No | Output file path (default: .tmp/ticket_response.md) |

## Quality Checklist
- [ ] Response acknowledges the customer's issue
- [ ] Clear solution steps or clarifying questions provided
- [ ] Response under 150 words
- [ ] Timeframe expectations set
- [ ] Follow-up/escalation path included
- [ ] Internal notes with category tags and priority
- [ ] Tone matches specified style

## Related Directives
- `directives/ticket_auto_responder.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_customer_support.md`
- `skills/SKILL_BIBLE_client_communication.md`
