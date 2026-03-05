---
name: invoice-generator
description: Generate professional PDF invoices with payment links. Use when user asks to create an invoice, bill a client, or generate billing documents.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Invoice Generator

## Goal
Generate professional PDF invoices from client and service data, with optional payment link integration and email delivery.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `STRIPE_API_KEY` for payment links (optional)
- `GOOGLE_APPLICATION_CREDENTIALS` for Google Sheets tracking (optional)

## Execution Command

```bash
python3 .claude/skills/invoice-generator/generate_invoice.py \
  --client "Acme Corp" \
  --client_email "billing@acme.com" \
  --items "Monthly Retainer:3000,Lead List (500 contacts):500" \
  --due_days 15 \
  --company "AIAA" \
  --output .tmp/invoice.pdf
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Gather Invoice Details** - Collect client name, email, line items, and due date
4. **Generate Invoice** - Run `.claude/skills/invoice-generator/generate_invoice.py` to create PDF
5. **Send to Client** - Optionally email via `send_invoice_email.py`
6. **Track Payment** - Log invoice status to Google Sheets

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client or business name |
| `--client_email` | No | Email address for delivery |
| `--items` | Yes | Line items as `Item:Price,Item2:Price2` |
| `--due_days` | No | Days until payment due (default: 30) |
| `--invoice_num` | No | Custom invoice number |
| `--notes` | No | Additional notes on invoice |
| `--company` | No | Your company name |
| `--output` | No | Output file path |

## Quality Checklist
- [ ] Client name and contact details correct
- [ ] All line items listed with accurate amounts
- [ ] Invoice number is unique and sequential
- [ ] Due date clearly stated
- [ ] Payment methods/links included
- [ ] Professional formatting and branding
- [ ] Total calculation is accurate

## Related Directives
- `directives/invoice_generator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_client_operations_retention.md`
- `skills/SKILL_BIBLE_client_communication_setup.md`
