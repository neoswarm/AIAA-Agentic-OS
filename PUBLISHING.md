# Publishing Workflows After Setup

When you ask Claude to publish, deploy, or schedule ANY workflow after initial setup, it will follow these rules:

---

## 1. Deploy to the SAME Railway Project as Dashboard

NEVER create a new Railway project. Always deploy workflow services to the same project where the dashboard was installed:

```bash
cd railway_apps/aiaa_dashboard
railway status  # Get the project ID
cd ../new_workflow
railway link -p <DASHBOARD_PROJECT_ID>
railway up
```

## 2. Upload ALL Required API Keys

Every workflow deployment MUST include setting all environment variables from `.env`:

```bash
# Read keys from .env and set in Railway
railway variables set OPENROUTER_API_KEY="<value>"
railway variables set SLACK_WEBHOOK_URL="<value>"
railway variables set PERPLEXITY_API_KEY="<value>"
# Check skill's SKILL.md for required keys
```

## 3. Update Dashboard Active Skills Section

After deploying a scheduled skill, ALWAYS update `railway_apps/aiaa_dashboard/app.py`:
- Find the `workflow_page()` function
- Add the new skill to the `active_workflows` list
- Redeploy the dashboard with `railway up`

---

## Publishing Checklist (Complete ALL Steps Every Time)

- [ ] Deploy to SAME Railway project as dashboard
- [ ] Set ALL required environment variables
- [ ] Add skill to dashboard's Active Workflows UI
- [ ] Redeploy dashboard
- [ ] Verify skill appears in dashboard
