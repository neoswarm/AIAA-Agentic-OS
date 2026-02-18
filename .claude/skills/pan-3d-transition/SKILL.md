---
name: pan-3d-transition
description: Create fast-forward 3D pan transition effects for video intros and scene transitions. Use when user asks to add a 3D transition, create a swivel effect, make a preview teaser, or add a pan transition to video.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# 3D Pan Transition Effect

## Goal
Create fast-forward "preview" style transitions with subtle 3D rotation (rotateY, rotateX, scale) using Remotion. Used for intros, scene transitions, or "coming up" previews.

## Prerequisites
- FFmpeg installed (`ffmpeg` and `ffprobe` in PATH)
- Node.js and Remotion (for video effects rendering)

## Execution Command

```bash
python3 .claude/skills/pan-3d-transition/pan_3d_transition.py input.mp4 output.mp4 \
  --output-duration 1.0 \
  --speed 7 \
  --bg-image .tmp/background.png
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Verify Input** - Confirm input video exists and check resolution/FPS
3. **Extract Frames** - Script extracts frames at native FPS
4. **Apply 3D Transforms** - Remotion applies rotateY, rotateX, scale transforms
5. **Fast-Forward Playback** - Video plays at specified speed (default 7x)
6. **Render Output** - Final video rendered at source resolution/FPS
7. **Review Output** - Check transition smoothness and visual quality

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `input` | Yes | Input video file path |
| `output` | Yes | Output video file path |
| `--start` | No | Start time in source video in seconds (default: 0) |
| `--source-duration` | No | Duration of source to use (default: auto) |
| `--output-duration` | No | Final output duration in seconds (default: 1.0) |
| `--swivel-start` | No | Starting Y-axis rotation in degrees (default: 3.5) |
| `--swivel-end` | No | Ending Y-axis rotation in degrees (default: -3.5) |
| `--tilt-start` | No | Starting X-axis rotation in degrees (default: 1.7) |
| `--tilt-end` | No | Ending X-axis rotation in degrees (default: 1.7) |
| `--perspective` | No | 3D perspective depth (default: 1000) |
| `--speed` | No | Playback speed multiplier (default: 7) |
| `--easing` | No | Animation easing: linear, easeOut, easeInOut, spring (default: linear) |
| `--bg-color` | No | Background color hex (default: #2d3436) |
| `--bg-image` | No | Background image path (overrides --bg-color) |

## Quality Checklist
- [ ] Transition plays smoothly without frame drops
- [ ] 3D rotation effect is subtle and professional
- [ ] Background fills visible edges cleanly
- [ ] Output duration matches specification
- [ ] Resolution matches source video

## Related Directives
- `directives/pan_3d_transition.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_vsl_video_editing.md`
