---
name: cold-email-personalizer
description: AI-powered hyper-personalized email first lines and openers. Use when user asks to personalize cold emails, generate first lines, create icebreakers, or research prospects for email personalization.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Cold Email Personalizer

## Goal
Generate hyper-personalized first lines and email openers for each prospect using AI research on their company, LinkedIn, news, and job posts.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `PERPLEXITY_API_KEY` in `.env` (for prospect research)

## Execution Command

```bash
python3 .claude/skills/cold-email-personalizer/personalize_emails_ai.py \
  --input "leads.json" \
  --service "B2B lead generation" \
  --value_prop "Book 30+ meetings per month" \
  --output ".tmp/personalized_leads.json"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Prepare Lead Data** - Ensure lead list has name, title, company, website columns
4. **Research Prospects** - AI researches each prospect via Perplexity (company, news, LinkedIn)
5. **Generate First Lines** - Creates personalized openers per prospect using patterns (achievement, content reference, company observation, industry insight)
6. **Quality Control** - Validates each line is specific, accurate, relevant, and concise (<25 words)
7. **Save Output** - Writes personalized data to JSON with first lines, pain points, and confidence scores

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--input` | Yes | Input lead file (JSON or CSV) |
| `--service` | Yes | What service you're selling |
| `--value_prop` | Yes | Key benefit/value proposition |
| `--output` | No | Output file path (default: `.tmp/personalized_leads.json`) |

## Quality Checklist
- [ ] Each first line is specific (not generic)
- [ ] First lines are under 25 words
- [ ] Pain points identified for each prospect
- [ ] Confidence scores assigned
- [ ] Output JSON contains personalized_first_line, pain_point, research_notes

## Related Directives
- `directives/ai_cold_email_personalizer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_cold_email_mastery.md`
- `skills/SKILL_BIBLE_hormozi_email_marketing_complete.md`
- `skills/SKILL_BIBLE_hormozi_lead_generation.md`
