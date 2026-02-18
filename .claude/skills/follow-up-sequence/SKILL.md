---
name: follow-up-sequence
description: Generate multi-touch follow-up email sequences after demos, proposals, or cold outreach. Use when user asks to create follow-up emails, build a follow-up sequence, write post-demo emails, or automate follow-ups.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Follow-Up Sequence Generator

## Goal
Generate personalized multi-touch follow-up email sequences for post-demo, post-proposal, no-response, and re-engagement scenarios.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/follow-up-sequence/generate_followup_sequence.py \
  --context "Demo with VP Marketing at SaaS company about lead gen services" \
  --goal "book_call" \
  --emails 4 \
  --tone "professional" \
  --output ".tmp/followup_sequence.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_follow_up_systems.md`
4. **Identify Sequence Type** - Post-demo, post-proposal, cold no-response, or re-engage
5. **Set Timing** - Determine spacing between touches (Day 0, 2, 5, 8, 12)
6. **Generate Emails** - Create personalized follow-up emails with unique angles per touch
7. **Add Personalization** - Include prospect name, company, relevant case studies
8. **Output** - Save sequence to `.tmp/` as markdown

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--context` / `-c` | Yes | Context of the initial interaction |
| `--goal` / `-g` | No | Sequence goal: `book_call`, `get_reply`, `close_deal`, `reconnect` (default: `book_call`) |
| `--emails` / `-e` | No | Number of follow-up emails (default: 4) |
| `--tone` / `-t` | No | Tone: `professional`, `casual`, `friendly` (default: `professional`) |
| `--output` / `-o` | No | Output path (default: `.tmp/followup_sequence.md`) |

## Quality Checklist
- [ ] Each email has a unique angle (no repetitive messaging)
- [ ] Clear CTA in every email
- [ ] Timing between emails is appropriate (not too aggressive)
- [ ] Final email is a graceful break-up
- [ ] Each email is under 75 words (per Sturtevant method)
- [ ] Subject lines are varied across the sequence
- [ ] Value provided before asking
- [ ] No desperate or pushy language

## Related Directives
- `directives/follow_up_sequence.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_follow_up_systems.md`
- `skills/SKILL_BIBLE_no_show_followup.md`
- `skills/SKILL_BIBLE_email_sequence_writing.md`
- `skills/SKILL_BIBLE_cold_email_mastery.md`
