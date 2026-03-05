---
name: campaign-launcher
description: Create and launch cold email campaigns in Instantly with AI-generated copy and A/B variants. Use when user asks to launch a campaign, create Instantly campaigns, set up cold email sends, or start outbound campaigns.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Campaign Launcher (Instantly)

## Goal
Create 3 email campaigns in Instantly based on client description and offers. Each campaign targets a different offer with 2-3 email steps and A/B split test variants on the first step.

## Prerequisites
- `INSTANTLY_API_KEY` in `.env` (for campaign creation)
- `ANTHROPIC_API_KEY` in `.env` (for email copy generation)

## Execution Command

```bash
python3 .claude/skills/campaign-launcher/instantly_create_campaigns.py \
  --client_name "Acme Corp" \
  --client_description "AI automation agency helping B2B companies" \
  --offers "Lead Generation|Email Automation|CRM Setup" \
  --target_audience "SaaS founders and marketing directors" \
  --social_proof "Generated 500+ meetings for 50 clients"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Campaign Examples** - Script reads examples from `.tmp/instantly_campaign_examples/campaigns.md`
4. **Generate Email Copy** - Claude generates 3 campaigns with personalized sequences
5. **Create Campaigns in Instantly** - API calls to create campaigns with steps and variants
6. **Configure Settings** - Set sending schedules, tracking, and daily limits
7. **Verify Campaigns** - Confirm campaigns created successfully in Instantly

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client_name` | Yes | Client or sender company name |
| `--client_description` | Yes | Description of the business and services |
| `--offers` | Yes | Pipe-separated list of offers (one per campaign) |
| `--target_audience` | Yes | Who the campaigns target |
| `--social_proof` | Yes | Credentials and results to reference in emails |

## Quality Checklist
- [ ] 3 separate campaigns created (one per offer)
- [ ] Each campaign has 2-3 email steps
- [ ] First step has 2 A/B variants
- [ ] Email copy is personalized and follows cold email best practices
- [ ] Subject lines are compelling and under 60 characters
- [ ] Campaigns configured with proper sending settings
- [ ] No spam trigger words in copy

## Related Directives
- `directives/launch_cold_email_campaign.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_cold_email_mastery.md`
- `skills/SKILL_BIBLE_cold_email_infrastructure.md`
- `skills/SKILL_BIBLE_email_deliverability.md`
