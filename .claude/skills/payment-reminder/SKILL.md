---
name: payment-reminder
description: Generate professional payment reminder emails with escalating tone based on days overdue. Use when user asks to send a payment reminder, create an invoice follow-up, write overdue notice, or draft collection email.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Payment Reminder Generator

## Goal
Generate professional payment reminder emails with tone that escalates based on how overdue the payment is — from friendly upcoming reminder to urgent final notice.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env` (for email generation)

## Execution Command

```bash
python3 .claude/skills/payment-reminder/send_payment_reminder.py \
  --client "Acme Corp" \
  --amount 5000 \
  --days_overdue 7 \
  --invoice_num "INV-2026-042" \
  --output .tmp/payment_reminder.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Determine Tone** - Script auto-selects tone based on days overdue (friendly → polite → firm → serious)
4. **Generate Reminder** - AI creates subject lines and email body with appropriate urgency
5. **Review Output** - Verify tone matches situation and all details are accurate
6. **Send or Save** - Deliver via email or save as draft

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client name |
| `--amount` | Yes | Amount due (numeric) |
| `--days_overdue` | No | Days past due date (default: 0 = upcoming) |
| `--invoice_num` | No | Invoice number reference |
| `--output` | No | Output path (default: `.tmp/payment_reminder.md`) |

## Quality Checklist
- [ ] Tone matches days overdue (0=friendly, 1-7=polite, 8-14=firm, 15+=serious)
- [ ] Amount and invoice number accurate
- [ ] Multiple subject line options provided
- [ ] Payment methods and next steps clearly stated
- [ ] Professional and non-threatening language
- [ ] Offer to discuss if client has issues

## Related Directives
- `directives/payment_reminder.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_agency_sales_system.md`
