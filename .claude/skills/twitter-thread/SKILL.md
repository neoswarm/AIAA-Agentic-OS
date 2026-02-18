---
name: twitter-thread
description: Generate viral Twitter/X threads with compelling hooks and structured tweets. Use when user asks to write a Twitter thread, create an X post thread, generate tweet storms, or build a thread for Twitter.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Twitter/X Thread Writer

## Goal
Generate Twitter/X threads optimized for virality with scroll-stopping hooks, structured 280-char tweets, numbered points, and engagement-driving CTAs.

## Prerequisites
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/twitter-thread/generate_twitter_thread.py \
  --topic "How to write cold emails that get replies" \
  --style educational \
  --length 10 \
  --output .tmp/twitter_thread.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read Twitter-specific skill bibles for thread strategy
4. **Select Hook Formula** - Choose curiosity, results, contrarian, story, or breakdown hook
5. **Generate Thread** - Run `.claude/skills/twitter-thread/generate_twitter_thread.py` with topic and style
6. **Validate Tweets** - Ensure each tweet is under 280 characters
7. **Check Structure** - Verify hook tweet, numbered body, and CTA finale
8. **Output** - Save to `.tmp/twitter_thread.md`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--topic` | Yes | Thread subject |
| `--style` | No | Thread style: story, educational, listicle, contrarian (default: educational) |
| `--length` | No | Number of tweets in the thread (default: 10) |
| `--output` | No | Output path (default: `.tmp/twitter_thread.md`) |

## Quality Checklist
- [ ] Hook tweet creates curiosity and includes 🧵 indicator
- [ ] Each tweet is under 280 characters
- [ ] Points are numbered (1/, 2/, etc.) for readability
- [ ] Line breaks used for visual clarity
- [ ] Final tweet has recap bullets and clear CTA
- [ ] Thread matches requested style (educational, story, etc.)
- [ ] Follows agency brand voice

## Related Directives
- `directives/twitter_thread_writer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_twitter_thread_writing.md`
- `skills/SKILL_BIBLE_twitter_growth_outreach.md`
- `skills/SKILL_BIBLE_twitter_algorithm.md`
- `skills/SKILL_BIBLE_twitter_growth_masterclass.md`
- `skills/SKILL_BIBLE_content_strategy_growth.md`
