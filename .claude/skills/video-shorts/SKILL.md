---
name: video-shorts
description: Extract viral short-form clips from video transcripts. Use when user asks to extract shorts, find viral moments, create TikTok clips, identify Reels content, or repurpose long-form video.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Video Shorts Extractor

## Goal
Analyze long-form video transcripts to identify viral-worthy moments and generate structured short-form clip recommendations for YouTube Shorts, TikTok, and Instagram Reels with hooks, text overlays, and platform fit analysis.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` - For AI transcript analysis
- `ffmpeg` - For video processing (if extracting actual clips)

## Execution Command

```bash
python3 .claude/skills/video-shorts/extract_video_shorts.py \
  --transcript transcript.txt \
  --clips 5 \
  --max_length 60 \
  --output .tmp/shorts_clips.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Prepare Transcript** - Ensure transcript file is available (text format)
4. **Run Extraction** - AI analyzes transcript for high-engagement moments
5. **Review Clips** - Verify each clip has standalone value and strong hooks

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--transcript` | Yes | Path to transcript text file |
| `--clips` | No | Number of clips to identify (default: 5) |
| `--max_length` | No | Max clip length in seconds (default: 60) |
| `--output` | No | Output file path (default: .tmp/shorts_clips.md) |

## Quality Checklist
- [ ] Each clip has a compelling hook title
- [ ] Timestamp ranges estimated for each clip
- [ ] Exact quote or moment description included
- [ ] "Why it works" analysis with emotional/curiosity factors
- [ ] Suggested text overlay for each clip
- [ ] Platform fit assessed (TikTok, Reels, Shorts)
- [ ] First 1-2 seconds of each clip hooks the viewer
- [ ] Each clip delivers standalone value

## Related Directives
- `directives/video_shorts_extractor.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_short_form_video.md`
- `skills/SKILL_BIBLE_video_content_repurposing.md`
