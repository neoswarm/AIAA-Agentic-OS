---
name: ai-news-digest
description: Curate latest AI news into a formatted digest with Slack delivery. Use when user asks for AI news, tech news digest, daily news summary, or latest AI developments.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# AI News Digest

## Goal
Curate the latest AI news articles using Perplexity real-time search, format into a clean digest, save locally, and deliver via Slack notification.

## Prerequisites
- `PERPLEXITY_API_KEY` in `.env`
- `SLACK_WEBHOOK_URL` in `.env` (optional, for Slack delivery)

## Execution Command

```bash
python3 .claude/skills/ai-news-digest/fetch_ai_news_digest.py \
  --topic "artificial intelligence" \
  --count 5
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Query Perplexity** - Search for latest news on the specified topic using Sonar model
3. **Parse Articles** - Extract title, source, URL, and one-sentence summary per article
4. **Save Locally** - Write Markdown digest to `.tmp/ai_news_digest/digest_YYYY-MM-DD.md`
5. **Deliver to Slack** - Format using Slack Block Kit and send via webhook (unless `--no-slack`)

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--topic` | No | News topic to search (default: "artificial intelligence") |
| `--count` | No | Number of articles to find (default: 5) |
| `--no-slack` | No | Skip Slack delivery (flag) |

## Quality Checklist
- [ ] At least 1 article returned (degrade gracefully if fewer than requested)
- [ ] Each article has title, source, and summary
- [ ] Local Markdown file saved successfully
- [ ] Slack notification sent (or skipped if `--no-slack`)
- [ ] Articles are from the past 7 days

## Related Directives
- `directives/ai_news_digest.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_content_curation.md`
