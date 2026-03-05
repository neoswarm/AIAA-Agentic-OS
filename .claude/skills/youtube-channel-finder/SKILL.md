---
name: youtube-channel-finder
description: Find and analyze YouTube channels by keyword with engagement filtering. Use when user asks to find YouTube channels, discover influencers, build a Dream 100 list, research YouTube competitors, or find content creators.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# YouTube Channel Finder

## Goal
Search YouTube for channels matching keywords, scrape detailed channel data (subscribers, views, video count), filter by engagement metrics, and export structured results for influencer outreach, competitor research, or Dream 100 prospecting.

## Prerequisites
- YouTube Data API enabled in Google Cloud Console
- Google OAuth configured (`client_secrets.json` + `token_youtube.json`)
- `SERPAPI_API_KEY` - SerpAPI fallback for YouTube search (optional)

## Execution Command

```bash
python3 .claude/skills/youtube-channel-finder/scrape_youtube_channels.py \
  --keywords "email marketing agency" "cold email outreach" \
  --min-subscribers 10000 \
  --max-subscribers 500000 \
  --min-videos 20 \
  --sort-by subscribers \
  --max-results 100 \
  --output-format both
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Search Channels** - Query YouTube Data API with keywords and filters
4. **Extract Data** - Scrape subscriber count, views, video count, descriptions
5. **Filter & Rank** - Apply min/max filters and sort by chosen metric
6. **Export Results** - Save to JSON and/or CSV in .tmp/ directory

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--keywords` | Yes | Search terms to find channels (can provide multiple) |
| `--max-results` | No | Maximum channels to return (default: 50) |
| `--min-subscribers` | No | Minimum subscriber count filter |
| `--max-subscribers` | No | Maximum subscriber count filter |
| `--min-videos` | No | Minimum video count filter |
| `--min-views` | No | Minimum total view count filter |
| `--sort-by` | No | Sort by: subscribers, views, videos, relevance (default: relevance) |
| `--language` | No | Filter by language code (e.g., en, es) |
| `--country` | No | Filter by country code (e.g., US, UK) |
| `--output-format` | No | Output format: json, csv, both (default: json) |
| `--output-prefix` | No | Custom prefix for output filename |

## Quality Checklist
- [ ] At least 1 keyword provided
- [ ] YouTube API credentials valid
- [ ] Results returned and filtered correctly
- [ ] No duplicate channels in results
- [ ] Output files created successfully (JSON and/or CSV)
- [ ] Channel data includes: name, handle, URL, subscribers, views, video count, description

## Related Directives
- `directives/youtube_channel_finder.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_youtube_lead_generation.md`
- `skills/SKILL_BIBLE_dream_100_strategy.md`
