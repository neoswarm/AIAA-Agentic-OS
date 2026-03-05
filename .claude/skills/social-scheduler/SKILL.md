---
name: social-scheduler
description: Generate optimal social media posting schedules across platforms. Use when user asks to schedule social media posts, create a posting schedule, plan social content timing, or optimize post times.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Social Media Scheduler

## Goal
Generate an optimized posting schedule across Twitter, LinkedIn, Instagram, Facebook, and TikTok with platform-specific timing for maximum engagement.

## Prerequisites
- No API keys required for schedule generation (local script)

## Execution Command

```bash
python3 .claude/skills/social-scheduler/schedule_social_media.py \
  --platforms "linkedin,twitter,instagram" \
  --posts_per_week 10 \
  --timezone "America/New_York" \
  --output .tmp/posting_schedule.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Gather Requirements** - Determine platforms, posting frequency, and timezone
4. **Generate Schedule** - Run script with optimal posting times per platform
5. **Review Output** - Verify schedule covers all platforms with proper spacing

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--platforms` | Yes | Comma-separated platforms: linkedin, twitter, instagram, facebook, tiktok |
| `--posts_per_week` | Yes | Total posts per week across all platforms |
| `--timezone` | No | Timezone for scheduling (default: America/New_York) |
| `--output` | No | Output file path (default: .tmp/posting_schedule.md) |

## Quality Checklist
- [ ] Schedule covers all requested platforms
- [ ] Posts spaced 3+ hours apart
- [ ] No duplicate posts within 24 hours
- [ ] Platform-specific optimal times used (LinkedIn: Tue-Thu mornings, Twitter: weekday mornings, etc.)
- [ ] Weekend posting follows platform best practices

## Related Directives
- `directives/social_media_scheduler.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_social_media_marketing.md`
- `skills/SKILL_BIBLE_content_calendar_mastery.md`
