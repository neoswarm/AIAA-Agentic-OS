---
name: sales-call-summary
description: Transcribe and summarize sales call recordings with AI. Use when user asks to summarize a sales call, transcribe a call recording, or generate call notes.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Sales Call Summary

## Goal
Transcribe sales call recordings and generate structured AI summaries with key discussion points, objections raised, action items, and deal assessment.

## Prerequisites
- `OPENAI_API_KEY` in `.env` (for Whisper transcription + summarization)
- `ffmpeg` installed for audio processing
- Audio/video recording file (MP3, MP4, WAV)

## Execution Command

```bash
python3 .claude/skills/sales-call-summary/summarize_sales_call.py \
  --transcript .tmp/transcript.txt \
  --prospect "John Smith" \
  --company "Acme Corp" \
  --output .tmp/call_summary.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_sales_training_complete.md`
4. **Transcribe Recording** - If audio file provided, transcribe with Whisper first
5. **Generate Summary** - Run `.claude/skills/sales-call-summary/summarize_sales_call.py` with transcript
6. **Review Output** - Verify key points, objections, and action items captured
7. **Deliver** - Save to `.tmp/` and optionally push to Google Docs

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--transcript` | Yes | Transcript file path or raw text |
| `--prospect` | No | Prospect's name |
| `--company` | No | Prospect's company name |
| `--output` | No | Output file path |

## Quality Checklist
- [ ] Key discussion points captured accurately
- [ ] All objections identified and documented
- [ ] Action items listed with owners and due dates
- [ ] Deal assessment includes interest level and close probability
- [ ] Next steps clearly defined
- [ ] Notable quotes extracted
- [ ] Competitor mentions documented

## Related Directives
- `directives/sales_call_summarizer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_sales_training_complete.md`
- `skills/SKILL_BIBLE_sales_closing_mastery.md`
- `skills/SKILL_BIBLE_sales_concepts_mastery.md`
- `skills/SKILL_BIBLE_agency_sales_system.md`
- `skills/SKILL_BIBLE_sales_call_recovery.md`
