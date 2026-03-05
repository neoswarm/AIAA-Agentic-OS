---
name: crm-automator
description: Automate CRM deal stage updates with AI-recommended next actions and tasks. Use when user asks to update a CRM deal, automate deal stage actions, generate deal next steps, or manage pipeline stages.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# CRM Deal Stage Automator

## Goal
Generate AI-powered deal stage assessments, recommended next actions, task lists, and email/call scripts based on current deal status and recent activity.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/crm-automator/automate_crm_deal.py \
  --deal "Acme Corp - Enterprise Plan" \
  --current_stage "demo_completed" \
  --notes "Great demo, asked about pricing" \
  --value 25000 \
  --output .tmp/deal_update.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Identify Deal Details** - Gather deal name, current stage, notes, and value
4. **Run Automator** - Execute `automate_crm_deal.py` to generate assessment and next actions
5. **Review Output** - Verify deal assessment, tasks, and scripts are actionable
6. **Deliver** - Save to `.tmp/` and optionally create Google Doc

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--deal` / `-d` | Yes | Deal name (e.g., "Acme Corp - Enterprise Plan") |
| `--current_stage` / `-s` | Yes | Current stage: lead, qualified, demo_scheduled, demo_completed, proposal_sent, negotiation, closed_won, closed_lost |
| `--notes` / `-n` | No | Recent notes or activity on the deal |
| `--value` / `-v` | No | Deal value in dollars (default: 0) |
| `--output` / `-o` | No | Output file path (default: .tmp/deal_update.md) |

## Quality Checklist
- [ ] Deal assessment includes momentum rating (hot/warm/cold)
- [ ] Win probability estimate provided
- [ ] At least 3 concrete tasks with due dates
- [ ] Email/call script included for next touchpoint
- [ ] Stage advancement criteria clearly defined

## Related Directives
- `directives/crm_deal_automator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_crm_pipeline_management.md`
- `skills/SKILL_BIBLE_sales_closing_mastery.md`
- `skills/SKILL_BIBLE_high_ticket_sales_process.md`
