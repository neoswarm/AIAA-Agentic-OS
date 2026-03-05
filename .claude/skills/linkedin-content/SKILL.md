---
name: linkedin-content
description: Generate LinkedIn posts and DMs with hooks and CTAs. Use when user asks to write a LinkedIn post, create LinkedIn content, or draft LinkedIn DMs.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# LinkedIn Content Generator

## Goal
Generate optimized LinkedIn posts and direct messages with engagement hooks, storytelling, and clear CTAs.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Commands

```bash
# LinkedIn Post
python3 .claude/skills/linkedin-content/generate_linkedin_post.py \
  --topic "How I landed my first client" \
  --type story \
  --tone casual \
  --cta comments \
  --output .tmp/linkedin_post.md

# LinkedIn DM
python3 .claude/skills/linkedin-content/generate_linkedin_dm.py \
  --prospect "John Smith" \
  --company "Acme Corp" \
  --context "They recently raised Series A" \
  --output .tmp/linkedin_dm.md
```

## Post Types
- `story` - Personal narrative with lesson
- `educational` - Teaching/how-to content
- `controversial` - Hot take or opinion
- `listicle` - Numbered tips or insights
- `case_study` - Client result showcase

## Process Steps
1. **Load Context** - Read `context/agency.md`, `context/brand_voice.md`
2. **Select Format** - Choose post type based on topic
3. **Write Hook** - First 2 lines must stop the scroll
4. **Build Content** - Story/lesson with white space formatting
5. **Add CTA** - Drive comments, shares, or link clicks
6. **Optimize** - Keep under 3000 chars, add line breaks
7. **Output** - Save to `.tmp/`

## Input Specifications (Post)
| Arg | Required | Description |
|-----|----------|-------------|
| `--topic` | Yes | Post topic |
| `--type` | No | Post type (default: educational) |
| `--tone` | No | casual/professional/bold |
| `--cta` | No | CTA type: comments/link/dm |
| `--output` | No | Output path |

## Quality Checklist
- [ ] Hook grabs attention in first 2 lines
- [ ] 150-3000 characters
- [ ] Proper line spacing for readability
- [ ] Clear CTA at the end
- [ ] No spam or overly promotional language
- [ ] Matches brand voice

## Related Directives
- `directives/linkedin_post_generator.md`
- `directives/linkedin_dm_automation.md`
- `directives/ultimate_linkedin_outreach.md`
