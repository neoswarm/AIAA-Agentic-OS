---
name: video-editor
description: Edit talking-head videos by removing silences, enhancing audio, and optionally adding swivel teaser transitions. Use when user asks to edit a video, remove silences from video, clean up video audio, or process a talking-head recording.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Smart Video Editor

## Goal
Automatically edit talking-head videos: remove silences using FFmpeg detection, normalize audio, generate AI metadata (title, description, tags), and optionally upload to YouTube via Auphonic.

## Prerequisites
- FFmpeg installed (`ffmpeg` and `ffprobe` in PATH)
- `ANTHROPIC_API_KEY` in `.env` (for metadata generation)
- Optional: `AUPHONIC_API_KEY` in `.env` (for upload and audio mastering)

## Execution Command

```bash
# Basic edit (silence removal + metadata)
python3 .claude/skills/video-editor/simple_video_edit.py \
  --video .tmp/my_video.mp4 \
  --title "My Video Title"

# Local only (no upload)
python3 .claude/skills/video-editor/simple_video_edit.py \
  --video .tmp/my_video.mp4 \
  --title "Test" \
  --no-upload
```

### Recommended Full Workflow (VAD + Swivel Teaser)

```bash
# Step 1: Remove silences with neural VAD
python3 .claude/skills/video-editor/simple_video_edit.py input.mp4 .tmp/edited.mp4 --enhance-audio

# Step 2: Add swivel teaser at 3 seconds
python3 .claude/skills/pan-3d-transition/pan_3d_transition.py .tmp/edited.mp4 output.mp4 \
  --bg-image .tmp/background.png
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Verify Input** - Confirm video file exists and get duration
3. **Detect Silences** - FFmpeg silencedetect finds silent sections (threshold: -35dB, min: 3s)
4. **Cut Silences** - Remove detected silent sections with buffer padding
5. **Normalize Audio** - Apply loudness normalization
6. **Generate Metadata** - Claude generates title, description, tags, and chapters
7. **Save Outputs** - Edited video + metadata text file to `.tmp/`
8. **Optional Upload** - Upload via Auphonic to YouTube with preset

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--video` | Yes | Input video file path |
| `--title` | Yes | Video title for metadata generation |
| `--no-upload` | No | Skip Auphonic upload, local edit only |

## Quality Checklist
- [ ] Silences removed without cutting speech
- [ ] Audio levels consistent and normalized
- [ ] No artifacts or glitches in edited video
- [ ] Metadata generated (title, description, tags)
- [ ] Output file saved to `.tmp/` with `_edited` suffix
- [ ] Metadata saved as `_metadata.txt` alongside video

## Related Directives
- `directives/smart_video_edit.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_vsl_video_editing.md`
- `skills/SKILL_BIBLE_video_marketing_agency_video_p.md`
