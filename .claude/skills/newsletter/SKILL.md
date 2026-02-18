---
name: newsletter
description: Generate engaging email newsletters with curated content. Use when user asks to write a newsletter, create an email digest, or build a weekly update.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Newsletter Writer

## Goal
Generate engaging email newsletters with curated content, insights, and clear CTAs for subscriber engagement.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/newsletter/generate_newsletter.py \
  --topic "Weekly Marketing Tips" \
  --style "educational" \
  --length "short" \
  --output .tmp/newsletter.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md`, `context/brand_voice.md`
2. **Theme Selection** - Define newsletter theme and key topics
3. **Intro Hook** - Write compelling opening that hooks readers
4. **Main Content** - 2-3 value-packed sections
5. **Quick Tips** - Actionable takeaways
6. **Resource Links** - Curated links and recommendations
7. **CTA** - Clear call to action (reply, share, click)
8. **Subject Line** - 5 subject line options with A/B variants

## Newsletter Styles
| Style | Description |
|-------|-------------|
| `educational` | Teaching tips and frameworks |
| `curated` | Curated links and resources |
| `story` | Personal narrative with lessons |
| `news` | Industry news roundup |
| `mixed` | Combination of all styles |

## Length Options
| Length | Sections | Word Count |
|--------|----------|------------|
| `short` | 2-3 | 500-800 |
| `medium` | 3-4 | 800-1200 |
| `long` | 4-6 | 1200-2000 |

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--topic` | Yes | Newsletter theme/topic |
| `--style` | No | Newsletter style (default: educational) |
| `--length` | No | short/medium/long (default: short) |
| `--output` | No | Output path |

## Quality Checklist
- [ ] 800+ words for standard newsletter
- [ ] Compelling subject line options
- [ ] Hook in first paragraph
- [ ] 2+ actionable takeaways
- [ ] Clear CTA
- [ ] Easy to scan with headers/bullets
- [ ] Follows brand voice
- [ ] No spam triggers

## Related Directives
- `directives/newsletter_writer.md`
- `directives/ultimate_local_newsletter.md`
