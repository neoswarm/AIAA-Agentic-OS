---
name: ghl-prospecting
description: Automate prospect research and import enriched leads into GoHighLevel CRM via Surfe API. Use when user asks to prospect into GHL, enrich leads for CRM, automate prospecting, import contacts to GoHighLevel, or build a prospect list with email enrichment.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# GHL Prospecting Automation

## Goal
Automate prospect research and import enriched leads into GoHighLevel CRM. Receives ICP criteria, searches for matching companies, finds decision-makers, enriches contacts with email addresses via Surfe API, and imports them into GHL CRM for outreach.

## Prerequisites
- `SURFE_API_KEY` in `.env` — Email enrichment via Surfe
- `GHL_API_KEY` in `.env` — GoHighLevel CRM API access

## Execution Command

```bash
python3 .claude/skills/ghl-prospecting/ghl_prospecting.py \
  --industry "marketing agencies" \
  --max-employees 500 \
  --country US \
  --output .tmp/prospecting/enriched_leads.json
```

**Note:** Requires SURFE_API_KEY and GHL_API_KEY in .env. Company search API integration pending.

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Define ICP Criteria** - Specify industry, max employee count, country code (Alpha-2), and any other firmographic filters
4. **Search ICP Companies** - Use company search APIs to find matching businesses in the target niche
5. **Search People in Companies** - Find decision-makers (owners, VPs, directors) at each matching company
6. **Prepare Enrichment Payload** - Format contact data as JSON for Surfe bulk enrichment API
7. **Submit to Surfe API** - Send bulk enrichment request to Surfe for email addresses
8. **Poll Enrichment Status** - Check enrichment completion status (wait 3 seconds between polls)
9. **Extract Enriched Contacts** - Parse Surfe API response for people with validated email addresses
10. **Import to GHL CRM** - Create or update contacts in GoHighLevel with enriched data
11. **Send Confirmation Email** - Notify via Gmail that the prospect list is ready
12. **Deliver Results** - Save enriched prospect list to `.tmp/prospecting/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--industry` | Yes | Target industry for ICP |
| `--max_employees` | No | Maximum employee count filter |
| `--country` | No | Country code Alpha-2 (e.g., "US") |
| `--name` | No | Requester name |
| `--email` | No | Requester email for notifications |

## Quality Checklist
- [ ] ICP criteria clearly defined
- [ ] Minimum 10 matching companies found
- [ ] Email enrichment completed for all contacts
- [ ] Contacts imported to GHL with proper tags
- [ ] No duplicate contacts created
- [ ] Confirmation notification sent
- [ ] Results saved locally

## Related Directives
- `directives/automated_prospecting_ghl_crm.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_lead_generation_mastery.md`
- `skills/SKILL_BIBLE_crm_pipeline_management.md`
- `skills/SKILL_BIBLE_n8n_gohighlevel.md`
