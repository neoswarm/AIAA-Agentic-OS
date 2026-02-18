---
name: rss-content
description: Convert RSS feed articles into social media content for LinkedIn, Twitter, and other platforms. Use when user asks to convert RSS to content, repurpose articles, turn news into social posts, or create content from RSS feeds.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# RSS to Content Pipeline

## Goal
Monitor RSS feeds for industry news, then automatically generate social media content and commentary for LinkedIn, Twitter, and other platforms using AI.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env` (for content generation)

## Execution Command

```bash
python3 .claude/skills/rss-content/convert_rss_to_content.py \
  --feed "https://example.com/rss" \
  --platforms "linkedin,twitter" \
  --items 3 \
  --output .tmp/rss_content.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Fetch RSS Feed** - Script fetches and parses latest items from the feed URL
4. **Select Items** - Pick top N most relevant articles
5. **Generate Content** - AI creates platform-specific social posts for each article
6. **Format Output** - Organize content by article and platform
7. **Review Content** - Verify brand voice alignment and accuracy
8. **Save or Schedule** - Output drafts for posting

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--feed` | Yes | RSS feed URL |
| `--platforms` | No | Comma-separated platforms (default: "linkedin,twitter") |
| `--items` | No | Number of feed items to convert (default: 3) |
| `--output` | No | Output path (default: `.tmp/rss_content.md`) |

## Quality Checklist
- [ ] RSS feed fetched successfully with valid articles
- [ ] Content generated for each specified platform
- [ ] Posts follow platform-specific best practices (char limits, hashtags, hooks)
- [ ] Brand voice consistent across all posts
- [ ] Each post adds unique commentary (not just article summary)
- [ ] Links to original articles included

## Related Directives
- `directives/rss_to_content_pipeline.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_video_marketing_agency_video_p.md`
