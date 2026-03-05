---
name: email-autoreply
description: Generate AI-powered contextual replies to Instantly email campaign responses using campaign knowledge bases. Use when user asks to set up email auto-reply, configure Instantly autoreply, create AI email responses, or automate campaign reply handling.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Instantly Email Autoreply

## Goal
Receive Instantly email reply webhooks, look up the campaign-specific knowledge base, research the prospect, and generate contextual AI-powered replies that match campaign tone and objectives.

## Prerequisites
- `INSTANTLY_API_KEY` in `.env`
- `ANTHROPIC_API_KEY` in `.env` (for Claude reply generation)
- Google OAuth credentials (`credentials.json` + `token.json`) for knowledge base sheet access
- Knowledge base sheet: `1QS7MYDm6RUTzzTWoMfX-0G9NzT5EoE2KiCE7iR1DBLM`

## Execution Command

```bash
python3 .claude/skills/email-autoreply/instantly_autoreply.py \
  --campaign_id "abc123" \
  --email_id "email-uuid"
```

## Process Steps
1. **Parse Reply** - Extract email content, sender, campaign ID from webhook payload
2. **Get Conversation History** - Optionally fetch prior emails from Instantly API
3. **Lookup Knowledge Base** - Find campaign-specific context from Google Sheet by campaign ID
4. **Skip Check** - If no knowledge base found, skip (no reply sent)
5. **Research Prospect** - Web search for prospect and company info (used to tailor reply)
6. **Generate Reply** - Claude generates contextual reply following campaign tone rules
7. **Filter Empty** - If reply is empty or prospect explicitly negative, do NOT send
8. **Send Reply** - Send via Instantly API with proper threading (reply_to_uuid)

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--campaign_id` | Yes | Instantly campaign ID |
| `--email_id` | Yes | Email ID to reply to (used as reply_to_uuid) |

## Quality Checklist
- [ ] Reply matches campaign knowledge base tone
- [ ] Prospect research incorporated without mentioning it
- [ ] Reply is 3-8 sentences (concise, non-corporate)
- [ ] No em dashes, no hype, no filler
- [ ] Explicit unsubscribe/negative replies are NOT responded to
- [ ] Empty/logistical replies are skipped gracefully
- [ ] Reply sent via Instantly API with proper threading

## Related Directives
- `directives/instantly_autoreply.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_cold_email_mastery.md`
- `skills/SKILL_BIBLE_cold_email_inbox_mgmt.md`
- `skills/SKILL_BIBLE_cold_email_script_writing.md`
- `skills/SKILL_BIBLE_email_nurture_sequences_sales_.md`
