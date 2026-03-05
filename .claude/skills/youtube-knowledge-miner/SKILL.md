---
name: youtube-knowledge-miner
description: Extract best practices from top YouTube channels and generate skill bibles. Use when user asks to mine YouTube knowledge, extract video best practices, create skill bibles from YouTube, or research a niche via YouTube content.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# YouTube Knowledge Miner

## Goal
Automatically discover top YouTube channels in any niche, extract transcripts from their best videos, convert transcripts into structured how-to manuals using AI, filter by quality rating, and synthesize multiple sources into comprehensive skill bibles.

## Prerequisites
- `OPENROUTER_API_KEY` - For Claude manual generation
- YouTube Data API enabled in Google Cloud Console
- Google OAuth configured (`client_secrets.json` + `token_youtube.json`)
- At least one transcript API recommended:
  - `SUPADATA_API_KEY` - Primary transcript API (supadata.ai)
  - `TRANSCRIPTAPI_KEY` - Secondary transcript API (transcriptapi.com)
- `GOOGLE_API_KEY` - Optional, for Gemini Flash (cheaper alternative with `--use-gemini`)

## Execution Command

```bash
python3 .claude/skills/youtube-knowledge-miner/youtube_knowledge_miner.py \
  --niche "meta ads" "facebook advertising" \
  --max-channels 10 \
  --videos-per-channel 5 \
  --min-subscribers 10000 \
  --min-views 10000 \
  --min-skill-rating 8 \
  --output-dir .tmp/knowledge_mine \
  --parallel 5
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Channel Discovery** - Search YouTube Data API for authority channels matching niche keywords
3. **Video Selection** - Get top-performing educational videos per channel (filtered by views, duration)
4. **Transcript Retrieval** - Supadata → TranscriptAPI → youtube-transcript-api (fallback chain)
5. **Manual Generation** - Claude/Gemini converts each transcript into structured how-to guide
6. **Quality Filtering** - AI rates each manual 1-10, filters by minimum rating
7. **Skill Bible Synthesis** - Combine high-quality manuals into comprehensive skill bible

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--niche` | Yes | Keywords to search (can provide multiple) |
| `--max-channels` | No | Maximum channels to analyze (default: 10) |
| `--videos-per-channel` | No | Videos to process per channel (default: 5) |
| `--min-subscribers` | No | Minimum channel subscribers (default: 5000) |
| `--min-views` | No | Minimum video views (default: 5000) |
| `--min-skill-rating` | No | Minimum quality rating 1-10 (default: 7) |
| `--use-gemini` | No | Use Gemini Flash for cheaper processing |
| `--output-dir` | No | Output directory (default: .tmp/knowledge_mine) |
| `--parallel` | No | Parallel video processing threads (default: 1) |

## Quality Checklist
- [ ] Found at least 3 qualifying channels
- [ ] Processed at least 5 videos successfully
- [ ] At least 3 manuals rated 7+ on quality scale
- [ ] Each manual includes: executive summary, key concepts, step-by-step process, best practices, common mistakes
- [ ] Skill bible generated and saved to output directory
- [ ] channels.json, videos.json, and manuals_index.json created

## Related Directives
- `directives/youtube_knowledge_miner.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_youtube_growth.md`
- `skills/SKILL_BIBLE_content_repurposing.md`
