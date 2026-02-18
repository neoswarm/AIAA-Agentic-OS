---
name: reddit-ad-script
description: Generate ad scripts from Reddit voice-of-customer insights. Use when user asks to create ads from Reddit, scrape Reddit for ad copy, generate ad scripts from pain points, or build VOC-based ads.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Reddit to Ad Scripts Generator

## Goal
Scrape Reddit threads for customer pain points and real language, then generate high-converting ad scripts using voice-of-customer insights and the Villain-Hero framework.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` in `.env` (optional, for direct Reddit API)

## Execution Command

```bash
python3 .claude/skills/reddit-ad-script/generate_reddit_ad.py \
  --topic "cold email deliverability problems" \
  --product "AI email warmup tool" \
  --subreddit "coldemail" \
  --output ".tmp/reddit_ads.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_ad_creative_hooks.md`
4. **Research Reddit** - Search relevant subreddits for pain points, frustrations, and real language
5. **Extract VOC Insights** - Identify frequency signals, severity markers, and failed solution attempts
6. **Analyze Opportunity** - Score business opportunity potential from extracted insights
7. **Generate Ad Scripts** - Create 3 ad scripts using Villain-Hero and PAS frameworks
8. **Output** - Save ad scripts with VOC evidence to `.tmp/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--topic` / `-t` | Yes | Topic or problem to research on Reddit |
| `--product` / `-p` | Yes | Your product or service being advertised |
| `--subreddit` / `-s` | No | Specific subreddit to research |
| `--output` / `-o` | No | Output path (default: `.tmp/reddit_ads.md`) |

## Quality Checklist
- [ ] At least 3 ad script variations generated
- [ ] Each script uses real voice-of-customer language
- [ ] Pain points backed by actual Reddit quotes
- [ ] Scripts follow Villain-Hero or PAS framework
- [ ] Hook captures attention in first 3 seconds
- [ ] Clear CTA with urgency in each script
- [ ] Scripts are platform-ready (proper timing/length)
- [ ] Sentiment analysis included

## Related Directives
- `directives/reddit_to_ad_scripts.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_ad_creative_hooks.md`
- `skills/SKILL_BIBLE_paid_advertising_mastery.md`
- `skills/SKILL_BIBLE_cold_ads_mastery.md`
- `skills/SKILL_BIBLE_meta_ads_manager_technical.md`
