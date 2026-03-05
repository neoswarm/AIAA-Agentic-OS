---
name: podcast-repurposer
description: Repurpose podcast or video content into social media posts, threads, blog articles, and summaries. Use when user asks to repurpose a podcast, turn a video into social content, or create content from a transcript.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Podcast Repurposer

## Goal
Transform podcast or video transcripts into multiple platform-specific content pieces including LinkedIn posts, Twitter threads, blog summaries, and key takeaways.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- Transcript file (text or markdown)

## Execution Command

```bash
python3 .claude/skills/podcast-repurposer/repurpose_podcast.py \
  --transcript ".tmp/transcript.txt" \
  --title "How We Scaled to $1M ARR" \
  --formats "linkedin,twitter,summary" \
  --output ".tmp/repurposed/"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_podcast_to_shorts_automation.md`
4. **Ingest Transcript** - Load and parse the transcript file
5. **Identify Highlights** - Extract best quotes, key insights, and compelling moments
6. **Generate LinkedIn Posts** - Long-form posts from main talking points (2-3 posts)
7. **Generate Twitter Threads** - Key insights as 8-12 tweet threads
8. **Generate Summary** - Blog-style episode summary with show notes
9. **Output** - Save all content pieces to output directory

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--transcript` | Yes | Path to transcript file |
| `--title` | No | Content title for context |
| `--formats` | No | Comma-separated output formats (default: `linkedin,twitter,summary`) |
| `--output` | No | Output directory (default: `.tmp/repurposed/`) |

## Quality Checklist
- [ ] Each platform's content follows native formatting rules
- [ ] LinkedIn posts are 150-3000 characters with story hooks
- [ ] Twitter threads are 8-12 tweets with strong opener
- [ ] Key quotes preserved accurately from transcript
- [ ] Summary captures all major talking points
- [ ] CTAs included where appropriate
- [ ] Content is original reframing, not copy-paste from transcript
- [ ] Hashtags included for discoverability

## Related Directives
- `directives/podcast_repurposer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_podcast_to_shorts_automation.md`
- `skills/SKILL_BIBLE_content_strategy_growth.md`
- `skills/SKILL_BIBLE_content_marketing.md`
- `skills/SKILL_BIBLE_social_media_marketing_agency_.md`
