---
name: zoom-content-repurposer
description: Repurpose Zoom call recordings into multi-platform content including YouTube scripts, LinkedIn posts, Twitter threads, newsletters, and Facebook posts. Use when user asks to repurpose a Zoom call, turn a recording into content, create multi-platform posts from a call, or generate content from a transcript.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Zoom Call Multi-Content Repurposer

## Goal
Process Zoom call recordings or transcripts to generate multiple content pieces for every major platform. Produces YouTube video scripts, LinkedIn posts, Twitter/X threads, email newsletters, and Facebook posts — each optimized for its platform. Saves to Google Docs, queues for scheduling, and sends Slack notifications.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` — AI content generation
- `OPENAI_API_KEY` in `.env` — Transcription (if audio)
- `GOOGLE_APPLICATION_CREDENTIALS` — Google Docs and Drive
- `SLACK_WEBHOOK_URL` in `.env` — Notifications

## Execution Command

```bash
python3 .claude/skills/zoom-content-repurposer/zoom_content_repurposer.py \
  --transcript transcript.txt \
  --platforms "linkedin,twitter,youtube,newsletter,facebook" \
  --output-dir .tmp/zoom-repurpose
```

Generates multi-platform content from Zoom call transcripts.

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Receive Transcript** - Accept Zoom recording transcript (plaintext or file path)
4. **Generate YouTube Script** - Create high-converting video script with hook (proof, promise, plan, persona), teaching segments, and CTA close
5. **Title YouTube Script** - Generate a 3-7 word document title
6. **Generate LinkedIn Post** - Create platform-optimized post with strong hook, clear structure, engaging conclusion in Lucas Synnott's voice
7. **Title LinkedIn Post** - Generate a 3-7 word document title
8. **Generate Email Newsletter** - Write emotionally resonant, personal newsletter in Lucas's writing style with insights from the call
9. **Title Newsletter** - Generate a 3-7 word document title
10. **Generate Twitter/X Post** - Create concise, high-performing tweet from key insights
11. **Generate Facebook Post** - Create engagement-optimized Facebook post
12. **Save to Google Docs** - Create individual Google Docs for each content piece
13. **Queue for Scheduling** - Add each post to the content scheduling queue in Google Sheets
14. **Publish via Blotato** - Optionally publish to Instagram, Facebook, LinkedIn, TikTok, YouTube, Threads, Twitter, and Bluesky
15. **Send Slack Notifications** - Notify for each content piece created with Google Doc links

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--transcript` | Yes | Path to Zoom transcript file or plaintext |
| `--platforms` | No | Comma-separated platforms: linkedin, twitter, blog, youtube, newsletter, facebook |

## Quality Checklist
- [ ] YouTube script has hook, teaching segments, and CTA
- [ ] LinkedIn post uses strong hook and clear structure
- [ ] Newsletter feels personal, not over-polished
- [ ] Twitter post is concise and impactful
- [ ] All content matches Lucas Synnott's brand voice
- [ ] No formatting characters (#, *, **) in social posts
- [ ] Each piece saved to Google Doc with proper title
- [ ] Content queued for scheduling
- [ ] Slack notifications sent for each piece

## Related Directives
- `directives/zoom_call_multi_content_copywriter_scheduler.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_content_strategy_growth.md`
- `skills/SKILL_BIBLE_content_marketing.md`
- `skills/SKILL_BIBLE_linkedin_post_writing.md`
- `skills/SKILL_BIBLE_youtube_script_writing.md`
- `skills/SKILL_BIBLE_email_newsletter.md`
