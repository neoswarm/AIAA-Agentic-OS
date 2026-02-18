---
name: video-transcription
description: Transcribe video and audio files with AI-powered summaries. Use when user asks to transcribe a video, summarize a recording, extract key points from audio, or generate meeting notes from a file.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Video Transcription + Summary

## Goal
Transcribe video or audio files using OpenAI Whisper and generate structured AI summaries with key points, timestamps, quotes, and action items.

## Prerequisites
- `OPENAI_API_KEY` in `.env` (for Whisper transcription + summarization)
- `ffmpeg` installed (`brew install ffmpeg`)
- Audio or video file (MP3, MP4, WAV, M4A)

## Execution Command

```bash
# Transcribe only
python3 .claude/skills/video-transcription/transcribe_video.py \
  --file recording.mp3 \
  --output .tmp/transcript.txt

# Transcribe + summarize
python3 .claude/skills/video-transcription/transcribe_video.py \
  --file recording.mp4 \
  --summarize \
  --output .tmp/summary.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Prepare Audio** - Extract audio from video if needed (ffmpeg)
4. **Transcribe** - Run the transcription script with Whisper
5. **Generate Summary** - Use `--summarize` flag for AI-powered summary
6. **Review Output** - Verify transcript accuracy and summary completeness
7. **Deliver** - Save to `.tmp/` and optionally push to Google Docs

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--file` | Yes | Audio or video file path (MP3, MP4, WAV, M4A) |
| `--summarize` | No | Also generate AI-powered summary with key points |
| `--output` | No | Output file path |

## Quality Checklist
- [ ] Transcript is accurate and readable
- [ ] Speaker identification attempted (if multiple speakers)
- [ ] Summary captures all key discussion points
- [ ] Timestamps included for major sections
- [ ] Action items extracted and listed
- [ ] Notable quotes highlighted
- [ ] TL;DR summary provided at top

## Related Directives
- `directives/video_transcription_summary.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_vsl_video_editing.md`
- `skills/SKILL_BIBLE_video_marketing_agency_video_p.md`
