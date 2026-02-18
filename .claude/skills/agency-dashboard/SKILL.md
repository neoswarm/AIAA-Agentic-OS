---
name: agency-dashboard
description: Deploy and manage the AIAA agency operations dashboard on Railway with KPI tracking, team metrics, and client health scores. Use when user asks to deploy the dashboard, set up agency dashboard, manage agency KPIs, or configure the Railway dashboard.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Agency Dashboard

## Goal
Deploy the complete AIAA agency operations dashboard to Railway. Manages KPI tracking, team performance, client health, revenue metrics, automated reporting, and alert systems for agency management.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` — AI analysis
- `GOOGLE_APPLICATION_CREDENTIALS` — Google Sheets integration
- Railway CLI installed and authenticated (`railway login`)

## Execution Command

```bash
python3 .claude/skills/agency-dashboard/deploy_aiaa_dashboard.py \
  --username "admin" \
  --password "your_secure_password" \
  --project-name "aiaa-dashboard"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Check Railway Auth** - Verify Railway CLI is authenticated and project exists
4. **Configure Dashboard** - Set admin credentials, environment variables, and project settings
5. **Deploy to Railway** - Push dashboard application to Railway infrastructure
6. **Set Environment Variables** - Configure all required API keys from `.env`
7. **Verify Deployment** - Health check the deployed dashboard endpoints
8. **Configure KPIs** - Set up financial, client, delivery, and team KPI definitions
9. **Send Notification** - Notify via Slack with dashboard URL and access details

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--username` | No | Dashboard login username (default: admin) |
| `--password` | No | Dashboard login password (will be hashed) |
| `--project-id` | No | Existing Railway project ID to use |
| `--project-name` | No | Name for new Railway project (default: aiaa-dashboard) |
| `--interactive` | No | Prompt for missing values (flag) |
| `--skip-env` | No | Skip setting environment variables from .env (flag) |
| `--dry-run` | No | Show what would be done without doing it (flag) |

## Quality Checklist
- [ ] Railway CLI authenticated
- [ ] Dashboard deployed successfully
- [ ] Health check passes at `/health`
- [ ] Admin login works
- [ ] Environment variables configured
- [ ] KPI definitions complete with formulas
- [ ] Alert thresholds configured
- [ ] Slack notification sent with dashboard URL

## Related Directives
- `directives/ultimate_agency_dashboard.md`
- `directives/deploy_to_railway.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_agency_scaling_systems.md`
- `skills/SKILL_BIBLE_crm_pipeline_management.md`
- `skills/SKILL_BIBLE_agency_operations_scaling_agen.md`
