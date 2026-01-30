# AI News Digest Workflow

## What This Workflow Is
Curates the latest AI news articles using Perplexity's real-time search, formats them into a clean digest, saves locally, and delivers via Slack notification.

## What It Does
1. Queries Perplexity API for the latest AI news (today/this week)
2. Extracts 5 articles with title, source, URL, and summary
3. Formats into a readable digest (Markdown + Slack)
4. Saves digest locally to `.tmp/ai_news_digest/`
5. Sends formatted digest to Slack via webhook

## Prerequisites
- `PERPLEXITY_API_KEY` - Perplexity API access for real-time search
- `SLACK_WEBHOOK_URL` - Slack webhook for delivery

## How to Run
```bash
python3 execution/fetch_ai_news_digest.py
python3 execution/fetch_ai_news_digest.py --topic "AI agents"
python3 execution/fetch_ai_news_digest.py --count 10
python3 execution/fetch_ai_news_digest.py --topic "LLMs" --count 5 --no-slack
```

## Inputs
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| --topic | string | No | "artificial intelligence" | News topic to search |
| --count | int | No | 5 | Number of articles to find |
| --no-slack | flag | No | False | Skip Slack delivery |

## Process

### Step 1: Query Perplexity for Latest News
- Use Perplexity `sonar` model with real-time search
- Prompt requests exactly N articles with structured fields
- Low temperature (0.2) for factual accuracy

### Step 2: Parse and Structure Results
- Extract: title, source, URL, one-sentence summary per article
- Validate all fields are present
- Handle partial results gracefully

### Step 3: Save Locally
- Save Markdown digest to `.tmp/ai_news_digest/digest_YYYY-MM-DD.md`
- Include generation timestamp and topic

### Step 4: Send to Slack
- Format using Slack Block Kit (header, divider, article sections)
- Each article: bold title with link, source, summary
- Include footer with timestamp

## Quality Gates
- [ ] At least 1 article returned (degrade gracefully if fewer than requested)
- [ ] Each article has title, source, and summary
- [ ] Local file saved successfully
- [ ] Slack notification sent (or skipped if --no-slack)

## Edge Cases
- Perplexity API down → Save error, exit with status 1
- Fewer articles than requested → Deliver what's available with warning
- Slack webhook missing → Save locally, print warning, still succeed
- Malformed API response → Log raw response, attempt partial parse

## Related Directives
- `directives/newsletter_writer.md` - Can feed digest into newsletter
- `directives/slack_notifier.md` - Uses same Slack delivery pattern

## Outputs
- `.tmp/ai_news_digest/digest_YYYY-MM-DD.md` - Local Markdown file
- Slack message in configured channel

## Self-Annealing Notes

### 2026-01-29: Initial Creation
- **Context**: Created as new DOE workflow (directive + execution script)
- **Patterns Used**: Followed existing `call_perplexity()` from `research_company_offer.py` and Slack Block Kit from `send_slack_notification.py`
- **First Run**: Successfully fetched 5 articles and delivered to Slack
- **URL Parsing Gotcha**: Perplexity returns URLs that break on naive `split(":", 1)` — added fallback to find `http` substring
- **Model**: Uses `sonar` (Perplexity's latest search-enabled model)
- **Graceful Degradation**: If fewer articles found than requested, delivers what's available with warning
- **Future Enhancement**: Could add deduplication across runs, topic rotation, or feed into newsletter_writer directive

### 2026-01-29: Webhook Deployment
- **Deployed**: Custom webhook handler added to dashboard at `/webhook/ai-news`
- **Dashboard URL**: `https://aiaa-dashboard-production-10fa.up.railway.app`
- **Webhook URL**: `POST https://aiaa-dashboard-production-10fa.up.railway.app/webhook/ai-news`
- **Payload**: `{"topic": "AI agents", "count": 5}` (both optional)
- **Handler**: `handle_ai_news_webhook()` in `app.py` — calls Perplexity, parses articles, sends Slack digest
- **Config**: Registered in `webhook_config.json` with `slack_notify: false` (handler sends its own formatted digest)
- **Railway Env Vars Required**: `PERPLEXITY_API_KEY`, `SLACK_WEBHOOK_URL`
- **Deployment Gotcha**: Railway's `railway run` executes locally, not in container. Use deployment-specific URL (check `RAILWAY_PUBLIC_DOMAIN` env var) not bookmarked URLs
