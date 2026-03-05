---
name: faq-chatbot
description: Generate FAQ responses and chatbot knowledge base content. Use when user asks to create FAQ answers, build chatbot responses, generate support content, or write FAQ documentation.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# FAQ Chatbot Response Generator

## Goal
Generate structured FAQ responses for AI-powered chatbots in Slack or Telegram, with confidence-based handling and human escalation logic.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/faq-chatbot/generate_faq_responses.py \
  --questions "What services do you offer?,How does pricing work?,What's the onboarding process?" \
  --business "AI Automation Agency - we build AI systems for B2B companies" \
  --context "Target audience is SaaS founders and marketing directors" \
  --tone "friendly" \
  --output ".tmp/faq_responses.json"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Gather Questions** - Parse comma-separated questions or load from file
4. **Research Answers** - Use business context and loaded knowledge to draft answers
5. **Generate Responses** - Create clear, helpful responses with source citations
6. **Add Confidence Levels** - Tag each response with confidence (high/medium/low)
7. **Include Escalation Logic** - Add human handoff triggers for low-confidence answers
8. **Output** - Save structured FAQ responses as JSON

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--questions` / `-q` | Yes | Comma-separated questions or path to questions file |
| `--business` / `-b` | Yes | Business name and description |
| `--context` / `-c` | No | Additional context about the business |
| `--tone` / `-t` | No | Response tone: `friendly`, `professional`, `casual` (default: `friendly`) |
| `--output` / `-o` | No | Output path (default: `.tmp/faq_responses.json`) |

## Quality Checklist
- [ ] Every question has a complete, accurate answer
- [ ] Responses match the specified tone
- [ ] Answers are concise but thorough
- [ ] Source citations included where applicable
- [ ] Confidence levels assigned to each response
- [ ] Escalation triggers defined for uncertain answers
- [ ] Output JSON is valid and well-structured
- [ ] No hallucinated or made-up information

## Related Directives
- `directives/faq_chatbot.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_ai_automation_agency.md`
