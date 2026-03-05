---
name: thumbnail-recreator
description: Recreate YouTube thumbnails with face-swapped images using AI and pose matching. Use when user asks to recreate a thumbnail, face-swap a thumbnail, generate YouTube thumbnails, or remake a video thumbnail.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Thumbnail Recreator

## Goal
Recreate YouTube thumbnails with a specific person's face swapped in using Nano Banana Pro (Gemini image model). Analyzes face direction in source, finds best-matching reference photo by pose, and generates 3 variations.

## Prerequisites
- `NANO_BANANA_API_KEY` in `.env` (for image generation via Gemini)
- Python packages: `opencv-python`, `mediapipe`, `Pillow`, `google-genai`
- Reference photos in `.tmp/reference_photos/` (analyzed with face direction metadata)

## Execution Command

```bash
# From YouTube URL
python3 .claude/skills/thumbnail-recreator/recreate_thumbnails.py \
  --youtube "https://youtube.com/watch?v=VIDEO_ID"

# From local image
python3 .claude/skills/thumbnail-recreator/recreate_thumbnails.py \
  --source "path/to/thumbnail.jpg"

# Edit pass on generated thumbnail
python3 .claude/skills/thumbnail-recreator/recreate_thumbnails.py \
  --edit "path/to/generated.png" \
  --prompt "Change graph to show upward trend"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Get Source Thumbnail** - Download from YouTube URL or use local image
3. **Analyze Face Direction** - MediaPipe detects yaw/pitch angles in source
4. **Find Best Reference** - Match source pose to closest reference photo
5. **Generate Variations** - Nano Banana Pro generates 3 thumbnail variations
6. **Save Output** - Images saved to `.tmp/thumbnails/`
7. **Optional Edit Pass** - Refine generated thumbnails with text prompts

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--youtube` | Yes* | YouTube video URL (*or --source) |
| `--source` | Yes* | Local thumbnail image path (*or --youtube) |
| `--edit` | No | Path to generated thumbnail for edit refinement |
| `--prompt` | No | Edit instructions (used with --edit) |

## Quality Checklist
- [ ] Face direction matches source thumbnail pose
- [ ] 3 variations generated with distinct styles
- [ ] Face swap looks natural and consistent
- [ ] Text/overlays preserved from source where relevant
- [ ] Output resolution matches YouTube thumbnail spec (1280x720)

## Related Directives
- `directives/recreate_thumbnails.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_video_marketing_agency_video_p.md`
