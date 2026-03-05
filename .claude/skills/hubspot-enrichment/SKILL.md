---
name: hubspot-enrichment
description: Enrich HubSpot contacts with job titles, company info, and verified contact details from external sources. Use when user asks to enrich HubSpot contacts, add data to CRM contacts, update HubSpot leads, or enrich email contacts.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# HubSpot Lead Enrichment

## Goal
Enrich HubSpot contacts with additional data from AnyMailFinder, Apollo, Clearbit, or People Data Labs — including job titles, company size, industry, verified emails, and phone numbers — then update HubSpot with the enriched data.

## Prerequisites
- `ANYMAILFINDER_API_KEY` in `.env` (primary enrichment)
- Google OAuth credentials (`credentials.json` + `token.json`) for sheet-based workflows

## Execution Command

```bash
python3 .claude/skills/hubspot-enrichment/enrich_emails.py \
  --sheet-url "https://docs.google.com/spreadsheets/d/..." \
  --domain "targetcompany.com"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Export Contacts** - Get contacts from HubSpot list or Google Sheet
4. **Enrich Data** - Query AnyMailFinder/Apollo for each contact: title, company size, industry, verified email, phone
5. **Apply Rules** - Only enrich empty fields, don't overwrite manual entries, flag low-confidence data
6. **Update Source** - Push enriched data back to HubSpot or Google Sheet
7. **Generate Report** - Create quality report with enrichment success rates

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--sheet-url` | No | Google Sheet URL with contacts to enrich |
| `--domain` | No | Domain to search for contacts |

## Quality Checklist
- [ ] Enrichment only fills empty fields (doesn't overwrite manual entries)
- [ ] Low-confidence data is flagged for review
- [ ] All changes logged for audit trail
- [ ] Quality report generated with success/failure rates
- [ ] Cost per contact under $0.10

## Related Directives
- `directives/hubspot_enrichment.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_crm_pipeline_management.md`
- `skills/SKILL_BIBLE_lead_list_building.md`
- `skills/SKILL_BIBLE_b2b_lead_generation.md`
