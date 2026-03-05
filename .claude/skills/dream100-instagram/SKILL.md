---
name: dream100-instagram
description: Generate personalized Instagram DM openers for Dream 100 prospects using AI vision analysis. Use when user asks to create Dream 100 DMs, personalize Instagram outreach, generate DM openers, or automate Instagram prospecting.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Dream 100 Instagram Personalized DM Automation

## Goal
Fetch Instagram accounts from a Dream 100 prospect list, analyze their latest post using AI vision, and generate personalized DM openers with compliment-first strategy. Outputs ready-to-send messages added to a Google Sheet for manual or automated sending.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` — AI vision and text generation
- `GOOGLE_APPLICATION_CREDENTIALS` — Google Sheets access
- Instagram API access or scraping tool

## Execution Command

```bash
python3 .claude/skills/dream100-instagram/dream100_instagram.py \
  --prospects prospects.json \
  --booking-link "https://calendly.com/example" \
  --output .tmp/dream100/dm_results.json
```

**Note:** Requires Instagram scraping integration (Apify or similar). Uses placeholder data until integrated.

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bibles** - Read `skills/SKILL_BIBLE_hormozi_lead_generation.md` for Dream 100 strategy
4. **Pull Dream 100 List** - Fetch Instagram account handles from Google Sheet (full name, username, biography)
5. **Fetch Account Data** - For each account, retrieve profile info and latest posts via Instagram API
6. **Download Latest Post Image** - Get the image from the most recent post for each account
7. **Analyze Post with AI Vision** - Use vision model to describe the image content and context
8. **Generate Personalized DM** - Create a 3-sentence DM using compliment-first opener referencing the post image, caption, and bio
9. **Include Booking Link** - Append calendar booking link with soft CTA
10. **Write to Google Sheet** - Add generated DM to the prospect sheet for review and sending
11. **Loop for All Accounts** - Process all Dream 100 accounts in the list

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--sheet_url` | Yes | Google Sheet URL with Dream 100 list |
| `--booking_link` | No | Calendar booking link for CTA |

## Quality Checklist
- [ ] DMs are 3 sentences or fewer
- [ ] Each DM references specific post content (not generic)
- [ ] Compliment feels authentic, not salesy
- [ ] Booking link included with soft CTA
- [ ] No copy-paste detectable patterns across DMs
- [ ] All Dream 100 accounts processed
- [ ] Results written to Google Sheet

## Related Directives
- `directives/dream_100_instagram_personalized_dm_automation.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_hormozi_lead_generation.md`
- `skills/SKILL_BIBLE_hormozi_free_customer_acquisition.md`
- `skills/SKILL_BIBLE_hormozi_content_strategy.md`
