---
name: email-validator
description: Validate email lists for deliverability before campaigns. Use when user asks to validate emails, check email deliverability, clean email lists, verify email addresses, or remove invalid emails.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Bulk Email Validator

## Goal
Validate email lists before campaigns to remove invalid addresses, detect spam traps, disposable emails, and role-based addresses, improving deliverability rates.

## Prerequisites
- `HUNTER_API_KEY` or `ZEROBOUNCE_API_KEY` in `.env` (optional, for deep validation)

## Execution Command

```bash
python3 .claude/skills/email-validator/validate_emails.py \
  --input "leads.csv" \
  --email_column "email" \
  --api "basic" \
  --output ".tmp/validated_emails.json"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Email List** - Read input file (CSV or JSON format)
3. **Syntax Validation** - Check email format with regex
4. **Disposable Detection** - Flag disposable email providers (tempmail, mailinator, etc.)
5. **API Validation** - If `--api hunter` or `--api zerobounce`, verify mailbox existence via API
6. **Categorize Results** - Classify as valid, invalid, risky, or unknown
7. **Save Output** - Write validated results with status and deliverability scores

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--input` | Yes | Input file (CSV or JSON) |
| `--email_column` | No | Column name containing emails (default: "email") |
| `--api` | No | Validation level: basic, hunter, zerobounce (default: "basic") |
| `--output` | No | Output file path (default: `.tmp/validated_emails.json`) |

## Quality Checklist
- [ ] All emails checked for syntax validity
- [ ] Disposable email providers detected
- [ ] Role-based emails flagged (info@, support@)
- [ ] Results categorized (valid/invalid/risky/unknown)
- [ ] Summary stats included (total, valid %, invalid count)

## Related Directives
- `directives/bulk_email_validator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_email_deliverability.md`
