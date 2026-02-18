---
name: cold-email-campaign
description: Generate personalized cold email sequences with A/B variants. Use when user asks to write cold emails, create outreach sequences, or build email campaigns for prospects.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Cold Email Campaign Generator

## Goal
Generate personalized cold email sequences with A/B variants using AI research and proven copywriting frameworks.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `PERPLEXITY_API_KEY` for prospect research
- Lead list CSV (optional - can generate without)

## Execution Command

```bash
# Generate cold emails from a lead list
python3 .claude/skills/cold-email-campaign/write_cold_emails.py \
  --leads leads.csv \
  --sender_name "John Smith" \
  --product "AI Cold Email Tool" \
  --value_prop "Book 30+ meetings per month" \
  --output .tmp/email_sequences.json

# Full pipeline with research + personalization
python3 .claude/skills/cold-email-campaign/cold_email_pipeline.py \
  --sender "John Smith" \
  --company "Acme Corp" \
  --offer "Lead generation service" \
  --target "Marketing agencies"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client-specific, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_cold_email_mastery.md`
4. **Research Prospects** - Use Perplexity to research each lead
5. **Generate First Lines** - Personalized openers based on research
6. **Create Sequences** - Multi-email sequences (3-5 emails each)
7. **A/B Variants** - Generate variant subject lines and hooks
8. **Output** - Save to `.tmp/` as JSON or markdown

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--leads` | No | CSV file with prospect data |
| `--sender_name` | Yes | Sender's name |
| `--product` | Yes | Product or service name |
| `--value_prop` | Yes | Core value proposition |
| `--output` | No | Output path (default: `.tmp/email_sequences.json`) |

## Quality Checklist
- [ ] Each email has a compelling subject line
- [ ] Personalized first line for each prospect
- [ ] Clear CTA in every email
- [ ] 3-5 email sequence per prospect
- [ ] A/B variants for subject lines
- [ ] Min 300 words per email
- [ ] No spam trigger words
- [ ] Follows agency brand voice

## Related Directives
- `directives/cold_email_scriptwriter.md`
- `directives/ultimate_cold_email_campaign.md`
- `directives/ai_cold_email_personalizer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_cold_email_mastery.md`
- `skills/SKILL_BIBLE_cold_dm_email_conversion.md`
- `skills/SKILL_BIBLE_email_deliverability.md`
