---
name: press-release
description: Generate professional AP-style press releases for company announcements. Use when user asks to write a press release, create a PR announcement, draft a media release, or generate a news announcement.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Press Release Generator

## Goal
Generate professional press releases in AP style format for product launches, funding announcements, partnerships, awards, and executive hires, including headline, body, quotes, and company boilerplate.

## Prerequisites
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/press-release/generate_press_release.py \
  --company "Acme Corp" \
  --announcement "Launches AI-powered lead generation platform" \
  --details "The platform uses machine learning to identify and qualify B2B leads" \
  --quote_person "Jane Smith" \
  --quote_title "CEO" \
  --contact "press@acmecorp.com" \
  --output .tmp/press_release.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Determine Announcement Type** - Identify: product launch, funding, partnership, award, or hire
4. **Generate Headline** - Create action-oriented, newsworthy headline
5. **Write Body** - Run `.claude/skills/press-release/generate_press_release.py` with company and announcement details
6. **Craft Quotes** - Generate executive quotes that add perspective and vision
7. **Add Boilerplate** - Include company about section and media contact
8. **Output** - Save to `.tmp/press_release.md`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--company` | Yes | Company name |
| `--announcement` | Yes | Main announcement or news |
| `--details` | No | Supporting details and context |
| `--quote_person` | No | Name of person for executive quote |
| `--quote_title` | No | Title of quote person (default: CEO) |
| `--contact` | No | Media contact information |
| `--output` | No | Output path (default: `.tmp/press_release.md`) |

## Quality Checklist
- [ ] Follows AP style press release format
- [ ] Headline is action-oriented and newsworthy
- [ ] Subheadline provides key benefit or detail
- [ ] Lead paragraph answers who, what, when, where, why
- [ ] Executive quote adds perspective (not generic praise)
- [ ] Company boilerplate included
- [ ] Media contact information present
- [ ] Professional, objective tone throughout
- [ ] Follows agency brand voice

## Related Directives
- `directives/press_release_generator.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_persuasion_speaking.md`
- `skills/SKILL_BIBLE_content_strategy_growth.md`
