---
name: x-youtube-content
description: Search X for trending posts and generate YouTube video ideas. Use when user asks to find trending topics on X, generate YouTube ideas from Twitter, create video concepts from social trends, or run the X-to-YouTube pipeline.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# X Keyword Search to YouTube Content Generator

## Goal
Search X (Twitter) for high-performing posts using Grok-4-fast via OpenRouter, analyze engagement patterns, and generate YouTube video ideas with full outlines optimized for the @thelucassynnott channel. Delivers output to Google Doc and notifies via Slack.

## Prerequisites
- `OPENROUTER_API_KEY` - For Grok-4-fast X search and content generation
- `SLACK_WEBHOOK_URL` - For notifications
- Google OAuth configured (`client_secrets.json` + `token.pickle`)

## Execution Command

```bash
python3 .claude/skills/x-youtube-content/x_keyword_youtube_content.py \
  --keywords "AI agents" "Claude Code" "automation workflows" \
  --min_engagement 100 \
  --num_videos 5
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Skill Bibles** - Read `skills/SKILL_BIBLE_youtube_script_writing.md` and `skills/SKILL_BIBLE_youtube_growth.md`
3. **Search X** - Use Grok-4-fast to find high-engagement posts matching keywords
4. **Aggregate & Analyze** - Combine results, rank by engagement, identify themes
5. **Generate Video Ideas** - Transform trending topics into 5 YouTube concepts
6. **Create Outlines** - Full outline per video (title, thumbnail, hook, body, CTA)
7. **Deliver** - Create Google Doc and send Slack notification

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--keywords` | No | Keywords to search on X (default: AI agents, AI automation, Claude Code, etc.) |
| `--min_engagement` | No | Minimum likes+retweets threshold (default: 50) |
| `--num_videos` | No | Number of video ideas to generate (default: 5) |
| `--time_range` | No | How far back to search: 24h, 7d, 30d (default: 24h) |

## Quality Checklist
- [ ] Minimum 10 high-performing posts found on X
- [ ] All video ideas have complete outlines
- [ ] Each outline includes hook (5-part framework), body, and CTA
- [ ] Titles under 60 characters with curiosity gap
- [ ] Thumbnail concepts described for each idea
- [ ] Google Doc created successfully
- [ ] Slack notification sent with document link

## Related Directives
- `directives/x_keyword_youtube_content.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_youtube_script_writing.md`
- `skills/SKILL_BIBLE_youtube_growth.md`
