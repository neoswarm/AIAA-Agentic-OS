---
name: slack-notifier
description: Send formatted Slack notifications with workflow status, deliverable links, and execution metadata. Use when user asks to send a Slack notification, notify the team, post to Slack, or alert on completion.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Slack Notifier

## Goal
Send formatted Slack notifications with workflow completion status (✅/❌/⚠️), links to deliverables, and execution metadata. Handles errors gracefully without breaking parent workflows.

## Prerequisites
- `SLACK_WEBHOOK_URL` in `.env` (for sending messages)

## Execution Command

```bash
python3 .claude/skills/slack-notifier/send_slack_notification.py \
  --workflow "VSL Funnel Complete" \
  --status success \
  --company "Acme Corp" \
  --deliverables '[{"name": "VSL Script", "url": "https://docs.google.com/..."}, {"name": "Sales Page", "url": "https://docs.google.com/..."}]' \
  --metadata '{"duration": "4m 32s", "word_count": 3500}'
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Prepare Message** - Format workflow name, status emoji, and company
3. **Add Deliverables** - List all output links with labels
4. **Add Metadata** - Include execution details (duration, errors, etc.)
5. **Send Notification** - POST to Slack webhook URL
6. **Handle Failures** - Log but don't throw on send failure

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--workflow` | Yes | Name of the completed workflow |
| `--status` | Yes | Execution status: "success", "failed", or "partial" |
| `--company` | No | Client company name |
| `--deliverables` | No | JSON array of `{name, url}` deliverable objects |
| `--metadata` | No | JSON object of execution metadata |

## Quality Checklist
- [ ] Correct status emoji displayed (✅ success, ❌ failed, ⚠️ partial)
- [ ] All deliverable links included and clickable
- [ ] Metadata formatted cleanly
- [ ] Message sent to correct channel
- [ ] Failure to send does not crash parent workflow

## Related Directives
- `directives/slack_notifier.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_slack_communication_systems.md`
