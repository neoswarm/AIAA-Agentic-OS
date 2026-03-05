---
name: content-translator
description: Translate content to multiple languages preserving tone and cultural context. Use when user asks to translate content, localize marketing materials, create multi-language versions, or translate emails and posts.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Content Translator

## Goal
Translate content into multiple languages using AI, preserving tone, idioms, formatting, and cultural context for marketing materials, emails, social posts, and documentation.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/content-translator/translate_content.py \
  --content "Your content here" \
  --languages "spanish,french,german" \
  --output ".tmp/translations.json"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md` for brand guidelines
3. **Prepare Content** - Accept content directly via `--content` or from file via `--file`
4. **Translate** - AI translates to each target language preserving formatting and tone
5. **Localize** - Adapt idioms and cultural references appropriately
6. **Save Output** - Write translations JSON with original and all translated versions

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--content` | Yes* | Content to translate (*or use `--file`) |
| `--file` | No | File containing content to translate |
| `--languages` | Yes | Comma-separated target languages (e.g., "spanish,french,german") |
| `--output` | No | Output file path (default: `.tmp/translations.json`) |

## Supported Languages
spanish, french, german, italian, portuguese, dutch, russian, japanese, chinese, korean, arabic, hindi

## Quality Checklist
- [ ] Grammar validated in each target language
- [ ] Formatting preserved (headers, bullets, links)
- [ ] Idioms localized appropriately (not literally translated)
- [ ] Proper nouns kept unchanged (unless standard translation exists)
- [ ] Brand voice consistency maintained across languages
- [ ] All requested languages included in output

## Related Directives
- `directives/content_translator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_content_localization.md`
