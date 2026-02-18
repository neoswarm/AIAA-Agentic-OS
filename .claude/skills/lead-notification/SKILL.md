---
name: lead-notification
description: Send instant Slack and email notifications when new leads are captured from forms, calendar bookings, or email replies. Use when user asks to set up lead alerts, configure lead notifications, notify on new leads, or send lead capture alerts.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Lead Notification

## Goal
Send instant Slack and email notifications when a new lead is captured from form submissions, calendar bookings, or positive email replies. Ensures fast follow-up with enriched lead data, logging to tracking sheets, and optional follow-up triggers.

## Prerequisites
- `SLACK_WEBHOOK_URL` in `.env` — Slack notifications
- `SENDGRID_API_KEY` in `.env` — Email alerts (optional)
- `GOOGLE_APPLICATION_CREDENTIALS` — Google Sheets for lead logging

## Execution Command

```bash
python3 .claude/skills/lead-notification/send_slack_notification.py \
  --workflow "lead-notification" \
  --status "success" \
  --company "Acme Corp" \
  --deliverables '[{"name": "New Lead: John Smith", "url": ""}]' \
  --metadata '{"lead_name": "John Smith", "lead_email": "john@acme.com", "source": "website_form"}'
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Parse Lead Data** - Extract contact info (name, email, phone), company name, lead source, and form responses
4. **Validate Lead** - Check email format, verify not duplicate, basic spam filtering
5. **Enrich Lead (Optional)** - If company domain available, lookup company size, industry, and recent news
6. **Send Slack Alert** - Post notification with lead name, company, email, source, details, and timestamp
7. **Send Email Alert** - Email sales team with subject "🔥 New Lead: {name} from {company}"
8. **Log to Tracking Sheet** - Append lead to Google Sheets tracker with name, email, company, source, date, and status "New"
9. **Trigger Follow-up** - If source is "calendar", send confirmation email and add to CRM pipeline. If source is "email_reply", route to inbox owner and update campaign status.

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--workflow` | Yes | Workflow name identifier (e.g., "lead-notification") |
| `--status` | Yes | Status: "success", "failed", "partial" |
| `--company` | No | Company name for the lead |
| `--deliverables` | No | Deliverables JSON array of {name, url} |
| `--metadata` | No | Metadata JSON with lead_name, lead_email, source, details |

## Quality Checklist
- [ ] Notification sent within 30 seconds of lead capture
- [ ] Slack alert includes all lead details (name, email, company, source)
- [ ] Lead logged to tracking sheet with "New" status
- [ ] Duplicate leads detected and merged
- [ ] Spam submissions filtered out
- [ ] Follow-up triggered based on source type
- [ ] Response time target: first human response <5 minutes (business hours)

## Related Directives
- `directives/lead_notification.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_lead_generation_mastery.md`
- `skills/SKILL_BIBLE_slack_communication_systems.md`
- `skills/SKILL_BIBLE_crm_pipeline_management.md`
