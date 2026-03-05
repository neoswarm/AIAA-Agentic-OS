---
name: youtube-script-workflow
description: Generate professional YouTube scripts with research, voice analysis, and structured delivery. Use when user asks to write a YouTube script, create a video script, generate YouTube content, or scriptwrite for a creator.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# YouTube Script Workflow

## Goal
Generate comprehensive, high-converting YouTube scripts (3000-6000 words) by researching the topic, analyzing the creator's existing content style, and producing a fully structured script with hooks, body sections, and CTAs.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` — AI generation (Claude/GPT)
- `PERPLEXITY_API_KEY` in `.env` — Topic and creator research
- `GOOGLE_APPLICATION_CREDENTIALS` — Google Docs delivery
- `SLACK_WEBHOOK_URL` in `.env` — Notifications

## Execution Command

```bash
python3 .claude/skills/youtube-script-workflow/generate_youtube_script_workflow.py \
  --creator "Creator Name" \
  --youtube-channel "https://www.youtube.com/@channel" \
  --topic "Video topic or title" \
  --video-type "educational" \
  --target-length "medium"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_youtube_lead_generation.md` and `skills/SKILL_BIBLE_youtube_script_writing.md`
4. **Gather Creator Info** - Collect creator name, channel URL, social profiles, topic, and video type
5. **Analyze Existing Content** - Download and parse transcripts from creator's recent videos for voice/style reference
6. **Research Topic** - Use Perplexity to research latest information, common questions, best practices, statistics, and misconceptions
7. **Research Creator** - Use Perplexity to gather creator background, expertise, and audience
8. **Generate Script** - Write structured script with hook (30-60s), opening (2-3min), body sections, and CTA/close
9. **Create Google Doc** - Upload to Google Docs with metadata header
10. **Send Notification** - Notify via Slack with script details and Google Doc link

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--creator` | Yes | Name of the person the script is for |
| `--youtube-channel` | No | Their YouTube channel URL |
| `--twitter` | No | Twitter/X profile URL |
| `--linkedin` | No | LinkedIn profile URL |
| `--topic` | Yes | The video topic/title |
| `--video-type` | No | "educational", "story", "case-study", "interview" (default: educational) |
| `--target-length` | No | "short" (3000w), "medium" (4500w), "long" (6000w) (default: medium) |
| `--target-audience` | No | Who the video is for |
| `--cta` | No | Call to action for viewers |
| `--key-points` | No | Specific points to cover |
| `--output-dir` | No | Output directory (default: .tmp/youtube_scripts/) |

## Quality Checklist
- [ ] Hook uses single subject, single question principle
- [ ] Each section starts with WHY before HOW
- [ ] Includes at least 3 stories/examples
- [ ] Has specific stats/data from research
- [ ] CTA is clear and actionable
- [ ] Word count within target range (3000-6000)
- [ ] Voice matches creator style (if reference available)
- [ ] Google Doc created successfully
- [ ] Slack notification sent

## Related Directives
- `directives/youtube_scriptwriter_workflow.md`
- `directives/google_doc_creator.md`
- `directives/slack_notifier.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_youtube_lead_generation.md`
- `skills/SKILL_BIBLE_youtube_script_writing.md`
- `skills/SKILL_BIBLE_youtube_script_advanced.md`
- `skills/SKILL_BIBLE_copywriting_fundamentals.md`
