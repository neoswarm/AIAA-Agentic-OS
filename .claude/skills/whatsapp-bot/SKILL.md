---
name: whatsapp-bot
description: Generate AI-powered WhatsApp support bot responses. Use when user asks to set up WhatsApp support, create chatbot responses, build WhatsApp bot, or automate WhatsApp customer service.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# WhatsApp Support Bot

## Goal
Generate AI-powered support responses for WhatsApp customer inquiries using knowledge base context, with automatic escalation triggers and multilingual support capabilities.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` - For AI response generation
- `TWILIO_SID` and `TWILIO_AUTH_TOKEN` - For WhatsApp Business API (production)
- `PINECONE_API_KEY` - For knowledge base vector search (optional)

## Execution Command

```bash
python3 .claude/skills/whatsapp-bot/generate_ticket_response.py \
  --ticket "How do I reset my password?" \
  --category "account" \
  --customer_name "Maria" \
  --tone "friendly" \
  --output .tmp/whatsapp_response.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Classify Inquiry** - Determine category and escalation need
4. **Generate Response** - AI creates contextual response from knowledge base
5. **Check Escalation** - Flag if human handoff needed (billing, complaints, complex issues)
6. **Review Response** - Verify response is under 300 characters, clear, and helpful

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--ticket` | Yes | Customer's WhatsApp message content |
| `--category` | No | Category: billing, technical, account, feature, bug, general (default: general) |
| `--customer_name` | No | Customer's name for personalization |
| `--tone` | No | Response tone: friendly, formal, empathetic (default: friendly) |
| `--output` | No | Output file path (default: .tmp/whatsapp_response.md) |

## Quality Checklist
- [ ] Response under 300 characters (WhatsApp best practice)
- [ ] Simple language used (no jargon)
- [ ] Solution or next steps clearly provided
- [ ] Escalation triggers identified (billing, refunds, complaints, 3+ failed attempts)
- [ ] Human handoff option offered when appropriate
- [ ] Tone matches brand voice guidelines

## Related Directives
- `directives/whatsapp_support_bot.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_customer_support.md`
- `skills/SKILL_BIBLE_chatbot_design.md`
