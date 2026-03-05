---
name: email-deliverability
description: Check email deliverability, blacklist status, SPF/DKIM/DMARC records, and get AI recommendations. Use when user asks to check email deliverability, audit domain health, verify DNS records, monitor email reputation, or fix deliverability issues.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Email Deliverability & Reputation Manager

## Goal
Monitor and assess email deliverability by checking blacklist status, validating SPF/DKIM/DMARC records, scoring overall deliverability, and providing AI-powered remediation recommendations.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/email-deliverability/enrich_emails.py \
  --sheet-url "https://docs.google.com/spreadsheets/d/..." \
  --domain "yourdomain.com"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Identify Domain** - Get the domain to check
4. **Check Blacklists** - Verify domain isn't on major blacklists (MXToolbox)
5. **Validate DNS Records** - Check SPF, DKIM, and DMARC configuration
6. **AI Analysis** - Score deliverability 1-100 and generate recommendations
7. **Alert** - Send critical alerts for immediate issues via Slack
8. **Report** - Generate status report with remediation steps

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--sheet-url` | No | Google Sheet URL with domains to check |
| `--domain` | No | Single domain to check |

## Quality Checklist
- [ ] Blacklist check completed against major providers
- [ ] SPF, DKIM, and DMARC records validated
- [ ] Deliverability score (1-100) generated
- [ ] Critical issues flagged with immediate action items
- [ ] Specific remediation steps provided
- [ ] Risk assessment for email campaigns included

## Related Directives
- `directives/email_deliverability_reputation_manager.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_email_deliverability.md`
- `skills/SKILL_BIBLE_email_deliverability_mastery.md`
- `skills/SKILL_BIBLE_email_deliverability_ecom.md`
- `skills/SKILL_BIBLE_cold_email_infrastructure.md`
