---
name: railway-deploy
description: Deploy any AIAA workflow to Railway as a cron job, webhook, or web service. Use when user asks to deploy a workflow to Railway, publish a cron job, add a webhook, schedule a workflow, or deploy a service to Railway.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Railway Workflow Deployer

## Goal
Deploy any AIAA directive/workflow to Railway as a standalone service — cron job (scheduled), webhook (event-triggered), or web service (always-on). Automatically discovers the dashboard project, scaffolds files, syncs shared variables, and registers the workflow.

## Prerequisites
- Railway CLI installed (`brew install railway`) and authenticated (`railway login`)
- AIAA Dashboard deployed to Railway (`python3 .claude/skills/dashboard-deploy/deploy_aiaa_dashboard.py`)
- Local `.env` file with required API keys

## Execution Command

```bash
# Cron workflow
python3 .claude/skills/railway-deploy/deploy_to_railway.py \
  --directive "x_keyword_youtube_content" \
  --type cron \
  --schedule "0 */3 * * *" \
  --auto

# Webhook workflow
python3 .claude/skills/railway-deploy/deploy_to_railway.py \
  --directive "calendly_meeting_prep" \
  --type webhook \
  --slug "calendly" \
  --slack-notify \
  --auto

# Web service
python3 .claude/skills/railway-deploy/deploy_to_railway.py \
  --directive "ai_news_digest" \
  --type web \
  --auto

# Auto-detect type
python3 .claude/skills/railway-deploy/deploy_to_railway.py \
  --directive "workflow_name" \
  --auto
```

### Utility Commands

```bash
# List all deployable directives
python3 .claude/skills/railway-deploy/deploy_to_railway.py --list

# Check requirements before deploying
python3 .claude/skills/railway-deploy/deploy_to_railway.py --directive "workflow_name" --info

# Preview without deploying
python3 .claude/skills/railway-deploy/deploy_to_railway.py --directive "workflow_name" --dry-run
```

## Process Steps
1. **Load Context** - Read `context/agency.md` for deployment context
2. **Determine Type** - Auto-detect or specify: cron, webhook, or web
3. **Parse Directive** - Extract scripts, integrations, and env var requirements
4. **Discover Project** - Find Railway project from `workflow_config.json` or CLI config
5. **Scaffold Service** - Create standalone service in `railway_apps/<name>/` with all required files
6. **Deploy** - Push to Railway via CLI
7. **Sync Variables** - Sync API keys as project-level shared variables
8. **Register** - Register workflow in `workflow_config.json` for dashboard display
9. **Verify** - Confirm deployment, cron schedule (if cron), or webhook registration (if webhook)

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--directive` | Yes | Directive name without .md extension |
| `--type` | No | `cron`, `webhook`, or `web` (auto-detected if omitted) |
| `--schedule` | Cron only | Cron expression (e.g., `0 */3 * * *`) |
| `--slug` | Webhook only | URL slug for webhook endpoint |
| `--forward-url` | No | URL to forward webhook payloads to |
| `--slack-notify` | No | Enable Slack notifications (webhook) |
| `--auto` | No | Fully automated, no prompts |
| `--dry-run` | No | Show plan without executing |
| `--list` | No | List all deployable directives |
| `--info` | No | Show deployment requirements |

## Quality Checklist
- [ ] Railway CLI accessible and authenticated
- [ ] Project discovered from workflow_config.json or Railway CLI
- [ ] All required env vars present in .env
- [ ] Deployment status is SUCCESS
- [ ] Cron schedule confirmed via GraphQL API (cron type)
- [ ] Webhook registered and returning 200 (webhook type)
- [ ] Workflow visible in dashboard Active Workflows page

## Related Directives
- `directives/deploy_to_railway.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_cloud_deployment_methods.md`
