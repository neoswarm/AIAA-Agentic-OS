---
name: client-onboarding
description: Generate client onboarding materials and setup new client profiles. Use when user asks to onboard a client, set up a new client, or create onboarding docs.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Client Onboarding

## Goal
Generate comprehensive onboarding materials for new clients and set up their profile in the system.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/client-onboarding/onboard_client.py \
  --client "Acme Corp" \
  --service "Marketing Automation" \
  --start_date "2024-01-15" \
  --contact "John Smith" \
  --output .tmp/onboarding/
```

## Process Steps
1. **Create Client Folder** - Set up `clients/{client_name}/` directory
2. **Build Profile** - Create `profile.md` with business info, goals, ICP
3. **Define Rules** - Create `rules.md` with brand guidelines, do's/don'ts
4. **Set Preferences** - Create `preferences.md` with tone, formatting
5. **Generate Welcome Pack** - Onboarding doc with timeline, deliverables
6. **Kickoff Agenda** - Create meeting agenda for kickoff call
7. **Milestone Timeline** - Week-by-week delivery schedule
8. **Deliver** - Save all docs to `.tmp/onboarding/` and/or Google Docs

## Client Profile Structure
```
clients/{client_name}/
├── profile.md      # Business info, industry, goals, ICP
├── rules.md        # Content rules, brand voice, compliance
├── preferences.md  # Style, tone, formatting preferences
└── history.md      # Past work, outcomes, learnings
```

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client/company name |
| `--service` | Yes | Service being delivered |
| `--start_date` | No | Project start date |
| `--contact` | No | Primary contact name |
| `--output` | No | Output directory |

## Quality Checklist
- [ ] Client folder created in `clients/`
- [ ] profile.md has business info and goals
- [ ] rules.md has brand guidelines
- [ ] Welcome pack generated
- [ ] Kickoff agenda prepared
- [ ] Timeline with milestones set

## Related Directives
- `directives/ultimate_client_onboarding.md`
- `directives/stripe_client_onboarding.md`
