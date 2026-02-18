---
name: lead-scoring
description: Score and qualify leads using AI against ICP criteria. Use when user asks to score leads, qualify prospects, rank a lead list, or prioritize outreach targets.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# AI Lead Scoring & Qualification

## Goal
Use AI to analyze and score leads based on ICP fit, buying signals, and engagement potential. Classifies leads as Hot/Warm/Cool/Cold with reasoning and recommended actions.

## Prerequisites
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `.env`
- `GOOGLE_APPLICATION_CREDENTIALS` for Google Sheets integration (optional)
- Lead list as CSV or JSON file

## Execution Command

```bash
python3 .claude/skills/lead-scoring/score_leads_ai.py \
  --input ".tmp/leads.json" \
  --icp_criteria "criteria.json" \
  --output ".tmp/scored_leads.json" \
  --batch_size 5
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_lead_generation_mastery.md`
4. **Prepare ICP Criteria** - Define or load ICP criteria JSON with weights
5. **Read Lead Data** - Ingest leads from CSV/JSON or Google Sheets
6. **AI Scoring** - Score each lead on ICP fit (0-100), intent signals (0-100), engagement potential (0-100)
7. **Classify Leads** - Hot (80-100), Warm (60-79), Cool (40-59), Cold (0-39)
8. **Output Results** - Save scored leads with classification and reasoning

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--input` / `-i` | Yes | Input leads file (JSON or CSV) |
| `--icp_criteria` / `-c` | No | ICP criteria JSON file with scoring weights |
| `--output` / `-o` | No | Output file (default: `.tmp/scored_leads.json`) |
| `--batch_size` | No | Leads per API call (default: 5) |

## Quality Checklist
- [ ] Every lead has an overall score (0-100)
- [ ] Every lead has a classification (Hot/Warm/Cool/Cold)
- [ ] AI reasoning provided for each score
- [ ] Recommended next action for each lead
- [ ] ICP criteria weights sum to 1.0
- [ ] Edge cases handled (missing data scored on available fields)
- [ ] Output JSON is valid and parseable

## Related Directives
- `directives/ai_lead_scorer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_lead_generation_mastery.md`
- `skills/SKILL_BIBLE_b2b_lead_generation.md`
- `skills/SKILL_BIBLE_lead_list_building.md`
- `skills/SKILL_BIBLE_lead_gen_system_overview.md`
