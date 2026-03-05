---
name: content-calendar
description: Generate multi-platform content calendars with topics, hooks, and posting schedules. Use when user asks to create a content calendar, plan content strategy, or schedule social media posts.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Content Calendar Generator

## Goal
Generate a structured content calendar with topics, hooks, and posting schedules across multiple platforms (LinkedIn, Twitter, Instagram, YouTube).

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `GOOGLE_APPLICATION_CREDENTIALS` for Google Sheets export (optional)

## Execution Command

```bash
python3 .claude/skills/content-calendar/generate_content_calendar.py \
  --client "Acme Corp" \
  --industry "SaaS" \
  --platforms "linkedin,twitter" \
  --content-pillars "thought leadership,case studies,tips" \
  --posts-per-week 5 \
  --days 30 \
  --brand-voice "professional yet approachable"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_content_calendar_creation.md`
4. **Define Content Strategy** - Identify unique angle, past performance, goals
5. **Generate Topic Ideas** - AI brainstorms topics per content pillar (educational, story-based, contrarian, engagement)
6. **Create Platform Hooks** - Generate platform-specific hooks and copy outlines
7. **Build Calendar** - Assign dates based on optimal posting times and content variety
8. **Export** - Save to `.tmp/` as markdown or Google Sheets

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client or brand name |
| `--industry` | Yes | Industry or niche |
| `--platforms` | No | Comma-separated platforms (default: `linkedin,twitter`) |
| `--content-pillars` | No | Comma-separated content themes |
| `--posts-per-week` | No | Posts per week (default: 5) |
| `--days` | No | Calendar length: 30, 60, or 90 days (default: 30) |
| `--brand-voice` | No | Brand voice description (default: `professional yet approachable`) |

## Quality Checklist
- [ ] Content mix follows 40% educational, 25% story, 20% engagement, 15% promotional
- [ ] Each post has a scroll-stopping hook
- [ ] No same content pillar posted back-to-back
- [ ] Platform-specific formatting (character limits, hashtags)
- [ ] Calendar covers full requested timeframe
- [ ] CTA included in promotional posts
- [ ] Follows client brand voice

## Related Directives
- `directives/generate_content_calendar.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_content_calendar_creation.md`
- `skills/SKILL_BIBLE_content_strategy_growth.md`
- `skills/SKILL_BIBLE_content_marketing.md`
- `skills/SKILL_BIBLE_ai_content_generation.md`
