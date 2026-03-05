---
name: webinar-followup
description: Generate post-webinar follow-up email sequences segmented by attendance. Use when user asks to create webinar follow-ups, write post-webinar emails, build webinar email sequences, or follow up with webinar attendees.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Webinar Follow-Up Sequence Generator

## Goal
Generate segmented post-webinar follow-up email sequences with different messaging for full attendees, partial attendees, and no-shows to maximize conversions.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/webinar-followup/generate_webinar_followup.py \
  --webinar "AI Automation Masterclass" \
  --offer "Done-For-You AI Implementation" \
  --price "$5,000" \
  --deadline "72 hours" \
  --output ".tmp/webinar_followup.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_webinar_mastery.md`
4. **Define Segments** - Full attendees, partial attendees, no-shows, offer clickers
5. **Generate Full Attendee Sequence** - Thank you → recap → case study → scarcity → final call
6. **Generate No-Show Sequence** - Missed you → key insights → replay expiring
7. **Generate Partial Attendee Sequence** - What you missed → key points → offer details
8. **Add Urgency Elements** - Replay expiration, offer deadline, limited spots
9. **Output** - Save all sequences to `.tmp/` as markdown

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--webinar` / `-w` | Yes | Webinar title or topic |
| `--offer` / `-o` | Yes | Offer being presented |
| `--price` / `-p` | Yes | Price point of the offer |
| `--deadline` / `-d` | No | Offer deadline (default: "72 hours") |
| `--output` | No | Output path (default: `.tmp/webinar_followup.md`) |

## Quality Checklist
- [ ] Separate sequences for each attendance segment
- [ ] Full attendee sequence has 4-5 emails over 3 days
- [ ] No-show sequence includes replay link with urgency
- [ ] Partial attendee sequence references what they missed
- [ ] Every email has a clear CTA
- [ ] Replay urgency (time-limited access) included
- [ ] Case study or testimonial included in sequence
- [ ] Scarcity and deadline elements are authentic

## Related Directives
- `directives/webinar_followup.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_webinar_mastery.md`
- `skills/SKILL_BIBLE_webinar_funnel_building.md`
- `skills/SKILL_BIBLE_webinar_funnel_launch.md`
- `skills/SKILL_BIBLE_webinar_live_events.md`
