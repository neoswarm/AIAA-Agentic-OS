---
name: demo-scheduler
description: Generate demo confirmation emails and prep materials for sales demos. Use when user asks to prepare for a demo, schedule a demo, create demo prep materials, or generate demo confirmation emails.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Demo Scheduler & Prep Generator

## Goal
Generate comprehensive demo preparation materials including confirmation emails, pre-demo research checklists, demo agendas, discovery questions, and objection handling scripts.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/demo-scheduler/schedule_demo.py \
  --prospect "John Smith" \
  --company "Acme Corp" \
  --datetime "2024-01-15 2:00 PM" \
  --product "Marketing Platform" \
  --output .tmp/demo_prep.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Gather Demo Details** - Collect prospect name, company, date/time, product, and any notes
4. **Run Generator** - Execute `.claude/skills/demo-scheduler/schedule_demo.py` to create all prep materials
5. **Review Output** - Verify confirmation email, agenda, and discovery questions
6. **Deliver** - Save to `.tmp/` and optionally create Google Doc

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--prospect` / `-p` | Yes | Prospect name |
| `--company` / `-c` | Yes | Prospect's company |
| `--datetime` / `-d` | Yes | Demo date and time (e.g., "2024-01-15 2:00 PM") |
| `--product` | Yes | Product being demoed |
| `--notes` / `-n` | No | Additional context or notes |
| `--output` / `-o` | No | Output file path (default: .tmp/demo_prep.md) |

## Quality Checklist
- [ ] Confirmation email includes date/time, agenda, and meeting link placeholder
- [ ] Pre-demo research checklist included
- [ ] Demo agenda covers 30-45 minute structure
- [ ] At least 5 discovery questions tailored to prospect
- [ ] Objection handling section included

## Related Directives
- `directives/demo_scheduler.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_sales_closing_mastery.md`
- `skills/SKILL_BIBLE_high_ticket_sales_process.md`
- `skills/SKILL_BIBLE_sales_call_recovery.md`
