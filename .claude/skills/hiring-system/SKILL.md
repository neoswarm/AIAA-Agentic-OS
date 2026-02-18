---
name: hiring-system
description: Generate complete hiring materials including job descriptions, interview scripts, scorecards, and onboarding plans. Use when user asks to create a job description, build interview questions, design a hiring process, create onboarding materials, or set up a hiring system.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Agency Hiring System

## Goal
Create a complete hiring and team building system for agencies scaling their teams. Produces job descriptions, multi-stage interview scripts, evaluation scorecards, offer templates, onboarding checklists, and 30/60/90 day training plans.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` — AI content generation

## Execution Command

```bash
python3 .claude/skills/hiring-system/assign_team_tasks.py \
  --tasks '[{"title": "Meta Ads Specialist", "level": "Mid", "department": "Paid Media"}]' \
  --team '[{"name": "Hiring Manager", "role": "Team Lead"}]' \
  --output ".tmp/hiring/assignments.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bibles** - Read `skills/SKILL_BIBLE_team_hiring_management.md` and `skills/SKILL_BIBLE_agency_hiring_system.md`
4. **Define Role** - Specify role title, level, department, salary range, and responsibilities
5. **Generate Job Description** - Create JD with about-company, role overview, responsibilities, requirements, nice-to-haves, benefits, and how-to-apply
6. **Create Interview Scripts** - Design 4-stage process: screening call (15min), technical interview (45min), culture fit (30min), final interview (30min)
7. **Build Evaluation Scorecard** - Rate candidates 1-5 on technical skills, communication, problem-solving, culture fit, and growth potential
8. **Generate Offer Template** - Position, start date, compensation, benefits, reporting structure, and terms
9. **Create Onboarding Plan** - Week 1 day-by-day schedule, weeks 2-4 gradual ramp, and 30/60/90 day milestones
10. **Deliver Materials** - Save all documents to `.tmp/hiring/` directory

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--tasks` | Yes | Tasks JSON with role details (title, level, department) |
| `--team` | Yes | Team members JSON (hiring manager, interviewers) |
| `--output` | No | Output file path (default: .tmp/assignments.md) |

## Quality Checklist
- [ ] Job description is clear and compelling
- [ ] Interview process has 4 defined stages
- [ ] Scorecard criteria defined with 1-5 scale
- [ ] Red flags and green flags documented
- [ ] Offer template includes all key elements
- [ ] Onboarding has day-by-day Week 1 plan
- [ ] 30/60/90 day milestones are measurable
- [ ] Role-specific interview questions included

## Related Directives
- `directives/ultimate_hiring_system.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_team_hiring_management.md`
- `skills/SKILL_BIBLE_hiring_team_building.md`
- `skills/SKILL_BIBLE_agency_hiring_system.md`
