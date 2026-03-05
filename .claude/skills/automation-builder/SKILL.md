---
name: automation-builder
description: Design and deploy AI automations, n8n/Make workflows, and webhook integrations with node configs and documentation. Use when user asks to build an automation, create a workflow, deploy a webhook, design an n8n workflow, or set up a Make automation.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# AI Automation Builder

## Goal
Design, document, and deploy AI automation workflows. Analyzes business processes, generates workflow architecture, creates node-by-node configurations, produces testing protocols, and generates client-facing and technical documentation for n8n, Make, or Zapier platforms.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` — AI design and content generation
- Railway dashboard deployed (for webhook registration)

## Execution Command

```bash
python3 .claude/skills/automation-builder/deploy_webhook_workflow.py \
  --slug "lead-intake" \
  --name "Lead Intake Automation" \
  --description "Enrich leads and add to CRM on form submission" \
  --source "Typeform" \
  --forward-url "https://your-processing-url.com" \
  --slack-notify
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bibles** - Read `skills/SKILL_BIBLE_n8n_workflow_automation.md` and `skills/SKILL_BIBLE_ai_automation_agency.md`
4. **Analyze Process** - Document current manual process, time/effort, error rate, and volume
5. **Design Architecture** - Map trigger events, integrations, decision points, and output requirements
6. **Generate Node Configuration** - Define each node's type, settings, input/output mapping, and credentials
7. **Create Testing Protocol** - Unit test nodes, integration test full workflow, edge case and load testing
8. **Generate Documentation** - Client guide (what it does, how to monitor) and technical docs (deployment, maintenance)
9. **Deploy Webhook** - Register webhook on AIAA Dashboard with slug, source, and forwarding URL
10. **Send Notification** - Notify via Slack with webhook URL and configuration details

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--slug` | Yes | Webhook slug (e.g., "lead-intake", "stripe-payments") |
| `--name` | Yes | Display name for the webhook |
| `--description` | No | What the webhook does |
| `--source` | No | External service name (e.g., "Stripe", "Typeform") |
| `--forward-url` | No | URL to forward webhook payloads to |
| `--slack-notify` | No | Enable Slack notifications (flag) |
| `--no-slack` | No | Disable Slack notifications (flag) |
| `--list` | No | List registered webhooks from live dashboard (flag) |
| `--unregister` | No | Unregister a webhook by slug (flag) |
| `--dry-run` | No | Show what would be sent without doing it (flag) |
| `--dashboard-url` | No | Dashboard URL override |

## Quality Checklist
- [ ] All nodes tested individually
- [ ] Full workflow tested end-to-end
- [ ] Error handling covers all failure points
- [ ] Credentials securely stored
- [ ] Rate limits considered
- [ ] Logging enabled
- [ ] Client documentation complete
- [ ] Technical documentation complete
- [ ] Webhook registered on dashboard

## Related Directives
- `directives/ultimate_ai_automation_builder.md`
- `directives/deploy_webhook_workflow.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_n8n_workflow_automation.md`
- `skills/SKILL_BIBLE_n8n_workflow_building.md`
- `skills/SKILL_BIBLE_ai_automation_agency.md`
- `skills/SKILL_BIBLE_n8n_error_handling.md`
