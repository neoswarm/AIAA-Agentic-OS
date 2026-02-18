---
name: cold-email-mass
description: Mass personalize cold emails with AI-researched icebreakers from a lead CSV. Use when user asks to mass personalize cold emails, generate icebreakers for a lead list, or personalize email campaigns at scale.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Cold Email Mass Personalizer

## Goal
Take a cold email script and lead list CSV, research each prospect using AI, and generate personalized icebreakers that achieve high open rates — output to Google Sheets or local file.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `PERPLEXITY_API_KEY` in `.env` (for prospect research)

## Execution Command

```bash
python3 .claude/skills/cold-email-mass/cold_email_pipeline.py \
  --industry "SaaS" \
  --location "united states" \
  --limit 50 \
  --skip_instantly
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Prepare Lead List** - Ensure CSV has First Name, Last Name, Company, and email columns
4. **Research Prospects** - AI agent researches each prospect (LinkedIn posts, news, achievements)
5. **Generate Icebreakers** - Master copywriter AI creates 8-22 word opening lines per prospect
6. **Quality Filter** - Separate high-confidence (from posts) and medium-confidence (from headline) leads
7. **Format Output** - Create final email with icebreaker + email body per lead
8. **Save Results** - Output personalized leads to `.tmp/leads/` as JSON and CSV

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--industry` | Yes | Target industry for lead discovery |
| `--location` | Yes | Target location (state/country format) |
| `--limit` | No | Number of leads to process (default: 50) |
| `--skip_instantly` | No | Skip Instantly upload, save locally only (flag) |
| `--campaign_name` | No | Campaign name if uploading to Instantly |

## Quality Checklist
- [ ] Each icebreaker is 8-22 words maximum
- [ ] Icebreakers are 100% about the prospect, 0% about you
- [ ] Tone is observational and conversational
- [ ] Public achievements used first as personalization source
- [ ] High-confidence vs medium-confidence leads separated
- [ ] No generic or salesy opening lines

## Related Directives
- `directives/cold_email_mass_personalizer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_cold_email_mastery.md`
- `skills/SKILL_BIBLE_hormozi_email_marketing_complete.md`
- `skills/SKILL_BIBLE_hormozi_lead_generation.md`
