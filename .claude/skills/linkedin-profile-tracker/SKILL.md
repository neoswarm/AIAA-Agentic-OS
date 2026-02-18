---
name: linkedin-profile-tracker
description: Monitor LinkedIn profiles for job changes, promotions, and posts that signal buying intent or outreach triggers. Use when user asks to track LinkedIn profiles, monitor prospect changes, detect job changes, or set up LinkedIn alerts for sales triggers.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# LinkedIn Profile Change Tracker

## Goal
Monitor a list of LinkedIn profiles for changes that indicate buying intent or outreach triggers. Detects job changes, promotions, company changes, hiring announcements, and new posts. Sends priority-classified alerts and generates personalized outreach templates for each trigger event.

## Prerequisites
- `PHANTOMBUSTER_API_KEY` in `.env` — Or Apify/scraping tool for LinkedIn data
- `SLACK_WEBHOOK_URL` in `.env` — Slack alerts

## Execution Command

```bash
python3 .claude/skills/linkedin-profile-tracker/linkedin_profile_tracker.py \
  --profiles profiles.csv \
  --check-frequency daily \
  --output .tmp/linkedin-tracker/changes.json
```

**Note:** Requires PHANTOMBUSTER_API_KEY or APIFY_API_TOKEN in .env. LinkedIn scraper integration pending.

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Configure Monitoring List** - Load LinkedIn profile URLs from CSV/sheet to monitor
4. **Set Check Frequency** - Configure daily or weekly scan schedule
5. **Scan Profiles** - For each profile, check current data against last-known snapshot
6. **Detect High-Priority Changes** - Flag: new job/role change, promotion, company change, hiring announcement
7. **Detect Medium-Priority Changes** - Note: new post/article, profile update, connection milestones, skill endorsements
8. **Detect Company-Level Changes** - Track: funding announced, new product launch, team growth, office expansion
9. **Classify and Prioritize** - Rank changes by outreach opportunity value
10. **Generate Alert** - Format change alerts with name, old/new title, company, LinkedIn URL, and recommended action
11. **Create Outreach Templates** - Generate personalized messages for each trigger type (job change congrats, promotion congrats, post engagement)
12. **Send Notifications** - Push alerts via Slack and/or email
13. **Update CRM** - Add change notes to CRM records

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--profiles` | Yes | CSV file with LinkedIn profile URLs to monitor |
| `--check_frequency` | No | "daily" or "weekly" (default: daily) |
| `--output` | No | Output file for changes (default: .tmp/changes.json) |

## Quality Checklist
- [ ] Profile list loaded with valid LinkedIn URLs
- [ ] Changes detected compared to previous snapshot
- [ ] High-priority changes (job change, promotion) generate immediate alerts
- [ ] Outreach templates personalized to specific change type
- [ ] No false positives from profile rendering differences
- [ ] Notifications sent within 30 seconds of detection
- [ ] CRM records updated with change notes

## Related Directives
- `directives/linkedin_profile_tracker.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_linkedin_outreach.md`
- `skills/SKILL_BIBLE_linkedin_scraping.md`
- `skills/SKILL_BIBLE_lead_generation_mastery.md`
