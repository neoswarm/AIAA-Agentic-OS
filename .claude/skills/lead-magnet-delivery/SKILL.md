---
name: lead-magnet-delivery
description: Automate lead magnet delivery, email list tagging, and nurture sequence triggering on opt-in. Use when user asks to deliver a lead magnet, automate lead capture, set up opt-in delivery, trigger nurture emails, or configure lead magnet fulfillment.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Lead Magnet Delivery Automation

## Goal
Automate the end-to-end delivery of lead magnets when someone opts in. Captures leads from form submissions, immediately delivers the resource via email, adds contacts to email list with tags, triggers nurture sequences, and tracks conversion sources.

## Prerequisites
- `CONVERTKIT_API_KEY` in `.env` — Or MAILCHIMP/SENDGRID API key
- `GOOGLE_APPLICATION_CREDENTIALS` — Google Drive for file hosting

## Execution Command

```bash
python3 .claude/skills/lead-magnet-delivery/lead_magnet_delivery.py \
  --email "lead@example.com" \
  --name "John Smith" \
  --lead-magnet "VSL Template Pack" \
  --download-url "https://example.com/download" \
  --source "linkedin_ad"
```

**Note:** Requires CONVERTKIT_API_KEY or SENDGRID_API_KEY in .env. Email service integration pending.

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Capture Lead** - Receive form submission with email, name, lead magnet name, and source
4. **Validate Lead Data** - Check email format, verify not duplicate, basic spam filtering
5. **Tag Contact** - Apply tags: `lead_magnet:{name}`, `source:{channel}`, `date:{signup_date}`
6. **Send Delivery Email** - Immediately email the lead magnet download link with quick-start tips
7. **Redirect to Thank-You Page** - Show confirmation with download link and next-step CTA (book a call, join community)
8. **Trigger Nurture Sequence** - Start 6-email sequence: implementation tips (Day 1), case study (Day 3), related resource (Day 5), soft pitch (Day 7), value + harder pitch (Day 10), final offer (Day 14)
9. **Track Conversion Source** - Log lead source for attribution reporting
10. **Optional: Double Opt-in** - If enabled, send confirmation email before delivering resource

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--email` | Yes | Lead's email address |
| `--lead_magnet` | Yes | Lead magnet identifier/name |
| `--source` | No | Conversion source (e.g., "linkedin_ad", "blog_post") |
| `--name` | No | Lead's name |

## Quality Checklist
- [ ] Delivery email sent within 30 seconds of opt-in
- [ ] Download link works and is accessible
- [ ] Contact added to email list with correct tags
- [ ] Nurture sequence triggered and scheduled
- [ ] Source tracking captures attribution data
- [ ] No duplicate contacts created
- [ ] Spam submissions filtered out

## Related Directives
- `directives/lead_magnet_delivery.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_lead_generation_mastery.md`
- `skills/SKILL_BIBLE_email_sequence_writing.md`
- `skills/SKILL_BIBLE_email_deliverability.md`
- `skills/SKILL_BIBLE_lead_magnet_ad_funnels.md`
