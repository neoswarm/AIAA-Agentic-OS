---
name: dashboard-deploy
description: Deploy the AIAA Agentic OS dashboard to Railway with authentication. Use when user asks to deploy the dashboard, set up the AIAA dashboard, deploy dashboard to Railway, or create the management dashboard.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# AIAA Dashboard Deployment

## Goal
Deploy the AIAA Agentic OS management dashboard to Railway with password-protected access, workflow management, environment variable tracking, webhook endpoints, and real-time event logs.

## Prerequisites
- Railway CLI installed (`brew install railway`) and authenticated (`railway login`)
- Dashboard source files in `railway_apps/aiaa_dashboard/`

## Execution Command

```bash
python3 .claude/skills/dashboard-deploy/deploy_aiaa_dashboard.py \
  --username admin \
  --password "your_secure_password"
```

### With Existing Railway Project

```bash
python3 .claude/skills/dashboard-deploy/deploy_aiaa_dashboard.py \
  --project-id "your-project-id" \
  --password "your_secure_password"
```

### Interactive Mode

```bash
python3 .claude/skills/dashboard-deploy/deploy_aiaa_dashboard.py --interactive
```

## Process Steps
1. **Prerequisites Check** - Verify Railway CLI is installed and user is authenticated
2. **Project Setup** - Create new Railway project or link to existing one
3. **Environment Config** - Set `DASHBOARD_USERNAME`, hashed password, `FLASK_SECRET_KEY`, and copy API keys from `.env`
4. **Deploy** - Upload dashboard app to Railway and wait for build completion
5. **Generate Domain** - Create public domain URL
6. **Verify** - Confirm deployment is successful and login works

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--username` | No | Login username (default: admin) |
| `--password` | Yes | Login password (will be securely hashed) |
| `--project-id` | No | Existing Railway project ID |
| `--project-name` | No | Name for new project (default: aiaa-dashboard) |
| `--interactive` | No | Interactive setup mode |

## Quality Checklist
- [ ] Railway CLI installed and authenticated
- [ ] Dashboard source files exist in `railway_apps/aiaa_dashboard/`
- [ ] Password is provided and securely hashed
- [ ] Environment variables set successfully
- [ ] Deployment completes without errors
- [ ] Public domain generated and accessible
- [ ] Login works with provided credentials

## Related Directives
- `directives/deploy_aiaa_dashboard.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_cloud_deployment_methods.md`
