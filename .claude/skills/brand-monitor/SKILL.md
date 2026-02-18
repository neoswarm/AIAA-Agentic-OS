---
name: brand-monitor
description: Monitor brand mentions across web, social media, and news. Use when user asks to track brand mentions, monitor reputation, check brand sentiment, or scan for brand references online.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Brand Mention Monitor

## Goal
Track brand mentions across web, social media, news, and forums to manage reputation, identify engagement opportunities, and alert on negative sentiment.

## Prerequisites
- `PERPLEXITY_API_KEY` in `.env` (for web search)

## Execution Command

```bash
python3 .claude/skills/brand-monitor/monitor_brand_mentions.py \
  --brand "Company Name" \
  --competitors "Competitor1,Competitor2" \
  --output ".tmp/brand_mentions.json"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Search News** - Query Perplexity for recent news articles and blog mentions
4. **Search Social** - Query for social media discussions about the brand
5. **Search Reviews** - Query for reviews and feedback
6. **Categorize Results** - Classify mentions as positive, negative, or neutral
7. **Save Report** - Output JSON with timestamped results

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--brand` | Yes | Brand name to monitor |
| `--competitors` | No | Comma-separated competitor brand names |
| `--output` | No | Output file path (default: `.tmp/brand_mentions.json`) |

## Quality Checklist
- [ ] Multiple search angles covered (news, social, reviews)
- [ ] Results timestamped
- [ ] Sentiment categorized for each mention
- [ ] Competitor mentions tracked (if provided)
- [ ] Actionable insights highlighted

## Related Directives
- `directives/brand_mention_monitor.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_brand_monitoring.md`
