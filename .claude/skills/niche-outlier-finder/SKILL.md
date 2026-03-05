---
name: niche-outlier-finder
description: Find high-performing YouTube videos from adjacent business niches with transferable content patterns. Use when user asks to find cross-niche outliers, discover YouTube content ideas, scrape business YouTube videos, or find viral video patterns.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Cross-Niche YouTube Outlier Finder

## Goal
Identify high-performing videos from adjacent business niches to extract transferable content patterns, hooks, and structures. Generates title variants adapted to your channel niche and outputs to Google Sheets.

## Prerequisites
- `ANTHROPIC_API_KEY` in `.env` (for Claude summaries and title variants)
- `APIFY_API_TOKEN` in `.env` (optional, for fallback transcript fetching)
- Google OAuth credentials (`credentials.json` + `token.json`)

## Execution Command

```bash
python3 .claude/skills/niche-outlier-finder/scrape_cross_niche_outliers.py
```

### With Options

```bash
python3 .claude/skills/niche-outlier-finder/scrape_cross_niche_outliers.py \
  --days 90 \
  --min_score 1.1 \
  --limit 20 \
  --skip_transcripts
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Video Discovery** - Search cross-niche keywords and monitor business channels (50 videos/keyword, 15 videos/channel)
3. **Outlier Scoring** - Calculate outlier scores with recency boost; threshold 1.1x (10% above channel average)
4. **Cross-Niche Scoring** - Apply modifiers: -20% technical terms, +30% money hooks, +20% time hooks, +20% curiosity gaps
5. **Transcript & Summary** - 2-tier transcript fetch (youtube-transcript-api → Apify fallback), Claude summarization
6. **Title Variants** - Generate 3 title variants per outlier adapted to your niche
7. **Output to Sheet** - Create Google Sheet with 19 columns sorted by publish date

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--days` | No | Days to look back (default: 90) |
| `--min_score` | No | Minimum outlier score (default: 1.1) |
| `--limit` | No | Max outliers to process |
| `--keywords_only` | No | Skip channel monitoring (faster) |
| `--channels_only` | No | Skip keyword searches |
| `--skip_transcripts` | No | Skip transcript fetching (10x faster) |

## Quality Checklist
- [ ] ~20 outliers found per run
- [ ] Cross-niche scores calculated for transferability
- [ ] 3 title variants generated per outlier
- [ ] Results sorted by publish date (most recent first)
- [ ] Google Sheet created with all 19 columns

## Related Directives
- `directives/cross_niche_outliers.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_youtube_growth.md`
- `skills/SKILL_BIBLE_youtube_script_writing.md`
- `skills/SKILL_BIBLE_youtube_channel_automation.md`
