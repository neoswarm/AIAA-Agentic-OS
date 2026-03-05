---
name: stripe-onboarding
description: Automate client onboarding triggered by Stripe payment. Use when user asks to onboard a new client, set up client after payment, run Stripe onboarding, create VIP channel, or send welcome email.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Stripe Client Onboarding

## Goal
Automate the full client onboarding flow after Stripe payment: create Slack VIP channel, send branded welcome email, research client via Perplexity, search Fathom for past calls, generate internal report, create Google Doc, and post summary to Slack.

## Prerequisites
- `SLACK_BOT_TOKEN` - Slack bot token with channels:manage, chat:write scopes
- `SLACK_OWNER_USER_ID` - Owner's Slack user ID
- `SLACK_CONTENT_CHANNEL_ID` - #content-approval channel ID
- `GMAIL_SENDER` - Gmail sender address
- `GOOGLE_DRIVE_FOLDER_ID` - Drive folder for reports
- `FATHOM_API_KEY` - Fathom call search API key
- `PERPLEXITY_API_KEY` - For client company research
- `OPENROUTER_API_KEY` - For AI report generation
- Google OAuth configured (`client_secrets.json` + tokens)

## Execution Command

```bash
python3 .claude/skills/stripe-onboarding/stripe_client_onboarding.py \
  --client_name "Client Name" \
  --client_email "client@company.com" \
  --company_website "company.com"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If existing client, read `clients/{client}/*.md`
3. **Run Onboarding Script** - Execute with client name, email, and website
4. **Verify Outputs** - Check Slack channel created, email sent, Google Doc generated
5. **Create Client Profile** - Set up `clients/{client_name}/` directory with profile.md

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client_name` | Yes | Client's full name |
| `--client_email` | Yes | Client's email address |
| `--company_website` | No | Client's company domain (defaults to email domain) |

## Quality Checklist
- [ ] Slack VIP channel created and owner invited
- [ ] Branded welcome email sent to client
- [ ] Fathom searched for past call transcripts
- [ ] Perplexity research completed on company
- [ ] Internal AI report generated
- [ ] Google Doc created with full research
- [ ] Slack notification posted to #content-approval
- [ ] JSON results saved to `.tmp/`

## Related Directives
- `directives/stripe_client_onboarding.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_client_onboarding.md`
- `skills/SKILL_BIBLE_agency_operations.md`
