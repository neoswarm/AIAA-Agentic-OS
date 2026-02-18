---
name: jump-cut-editor
description: Remove silences from talking-head videos using neural voice activity detection (Silero VAD). Use when user asks to remove silences, jump cut a video, edit out pauses, or trim dead air from video.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Jump Cut Editor (VAD-based)

## Goal
Automatically remove silences from talking-head videos using Silero VAD neural voice activity detection. Optionally enhance audio and apply color grading.

## Prerequisites
- FFmpeg installed (`ffmpeg` and `ffprobe` in PATH)
- Python packages: `torch`, `torchaudio` (for Silero VAD)
- Optional: `.cube` LUT file for color grading

## Execution Command

```bash
python3 .claude/skills/jump-cut-editor/jump_cut_vad.py input.mp4 output.mp4 \
  --enhance-audio \
  --detect-restarts
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Verify Input** - Confirm input video exists and is a supported format
3. **Extract Audio** - Script extracts WAV audio from video
4. **Run Silero VAD** - Neural voice activity detection identifies speech segments
5. **Detect Restarts** - Optionally detect "cut cut" restart phrases and remove mistake segments
6. **Concatenate Speech** - Stitch speech segments together with padding
7. **Enhance Audio** - Apply EQ, compression, and loudness normalization (-16 LUFS)
8. **Apply Color Grading** - Optional LUT-based color correction
9. **Review Output** - Check final video for quality

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `input` | Yes | Input video file path |
| `output` | Yes | Output video file path |
| `--min-silence` | No | Minimum silence gap to cut in seconds (default: 0.5) |
| `--min-speech` | No | Minimum speech duration to keep in seconds (default: 0.25) |
| `--padding` | No | Padding around speech in milliseconds (default: 100) |
| `--merge-gap` | No | Merge segments closer than this in seconds (default: 0.3) |
| `--enhance-audio` | No | Apply audio enhancement chain (EQ, compression, loudnorm) |
| `--detect-restarts` | No | Detect "cut cut" and remove mistake segments |
| `--apply-lut` | No | Path to .cube LUT file for color grading |
| `--no-keep-start` | No | Allow cutting silence at the beginning |

## Quality Checklist
- [ ] Output video plays without artifacts
- [ ] Speech segments preserved with natural transitions
- [ ] No abrupt cuts mid-word
- [ ] Audio levels consistent (-16 LUFS if enhanced)
- [ ] Color grading applied correctly (if LUT specified)

## Related Directives
- `directives/jump_cut_vad.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_vsl_video_editing.md`
