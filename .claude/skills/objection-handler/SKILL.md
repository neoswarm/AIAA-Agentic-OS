---
name: objection-handler
description: Generate AI-powered sales objection handling responses. Use when user asks to handle a sales objection, overcome prospect pushback, or create objection response scripts.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Objection Handler

## Goal
Provide AI-powered objection handling responses and scripts for sales conversations, with multiple approaches and follow-up questions tailored to context.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/objection-handler/handle_objections.py \
  --objection "It's too expensive" \
  --product "AI Lead Generation Service" \
  --price "3000" \
  --context "Discovery call, prospect is a marketing agency owner" \
  --output .tmp/objection_response.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_objection_handling_mastery.md`
4. **Classify Objection** - Identify objection category (price, timing, competitor, authority, trust)
5. **Generate Responses** - Run `.claude/skills/objection-handler/handle_objections.py` for multiple approaches
6. **Review Scripts** - Verify responses are consultative and value-focused
7. **Output** - Save response scripts to `.tmp/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--objection` | Yes | The objection text from the prospect |
| `--product` | Yes | Product or service being sold |
| `--price` | No | Price point for context |
| `--context` | No | Additional deal context (stage, prospect info) |
| `--output` | No | Output file path |

## Quality Checklist
- [ ] Objection correctly categorized
- [ ] Multiple response approaches provided (ROI reframe, value stack, etc.)
- [ ] Responses are consultative, not aggressive
- [ ] Follow-up questions included to keep conversation going
- [ ] Tone matches brand voice
- [ ] Scripts are natural and conversational

## Related Directives
- `directives/objection_handler.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_objection_handling_mastery.md`
- `skills/SKILL_BIBLE_objection_handling_advanced.md`
- `skills/SKILL_BIBLE_sales_training_complete.md`
- `skills/SKILL_BIBLE_sales_closing_mastery.md`
