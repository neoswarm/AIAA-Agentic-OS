---
name: linkedin-outreach
description: Generate LinkedIn DMs, connection requests, and outreach sequences. Use when user asks to write LinkedIn messages, create LinkedIn outreach, generate connection requests, or build a LinkedIn DM campaign.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# LinkedIn Outreach Campaign

## Goal
Generate personalized LinkedIn connection requests, follow-up DM sequences, and engagement strategies for B2B prospecting.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `PERPLEXITY_API_KEY` for prospect research (optional)

## Execution Command

```bash
python3 .claude/skills/linkedin-outreach/generate_linkedin_dm.py \
  --name "John Smith" \
  --title "VP of Marketing" \
  --company "Acme Corp" \
  --offer "AI-powered lead generation" \
  --context "They recently raised Series A" \
  --output ".tmp/linkedin_dm.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_linkedin_outreach.md`
4. **Research Prospect** - Gather context on the prospect and their company
5. **Generate Connection Request** - Short, personalized connection message (300 char limit)
6. **Create Follow-Up Sequence** - 3-4 DMs spaced across 14 days
7. **Personalize** - Customize messaging based on prospect's role, company, and context
8. **Output** - Save all messages to `.tmp/` as markdown

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--name` / `-n` | Yes | Prospect's full name |
| `--title` / `-t` | No | Prospect's job title |
| `--company` / `-c` | No | Prospect's company name |
| `--offer` / `-o` | Yes | What you're offering |
| `--context` | No | Additional context (recent news, mutual connections, etc.) |
| `--output` | No | Output path (default: `.tmp/linkedin_dm.md`) |

## Quality Checklist
- [ ] Connection request under 300 characters
- [ ] No pitching in the connection request
- [ ] Follow-up sequence has 3-4 messages
- [ ] Each message provides value before asking
- [ ] Personalized to prospect's specific situation
- [ ] Final message is a graceful break-up
- [ ] Follows LinkedIn best practices (no spam language)
- [ ] Clear CTA in follow-up messages

## Related Directives
- `directives/ultimate_linkedin_outreach.md`
- `directives/linkedin_dm_automation.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_linkedin_outreach.md`
- `skills/SKILL_BIBLE_linkedin_post_writing.md`
- `skills/SKILL_BIBLE_cold_dm_email_conversion.md`
