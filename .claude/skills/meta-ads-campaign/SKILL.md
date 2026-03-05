---
name: meta-ads-campaign
description: Generate complete Meta/Facebook/Instagram ad campaigns with copy, targeting, and creative briefs. Use when user asks to create Facebook ads, Meta ads, Instagram ads, or paid social campaigns.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Meta Ads Campaign Generator

## Goal
Generate complete Meta/Facebook/Instagram ad campaigns including ad copy variations, audience targeting strategies, creative briefs, campaign structure, and optimization playbooks.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` (for AI copy generation)
- `PERPLEXITY_API_KEY` for competitor research (optional)
- `FAL_KEY` for AI image generation (optional)

## Execution Command

```bash
python3 .claude/skills/meta-ads-campaign/generate_meta_ads_campaign.py \
  --client "Acme SaaS" \
  --product "Project Management Tool" \
  --offer "14-day free trial" \
  --target-audience "Small business owners, 25-45" \
  --monthly-budget 5000 \
  --objective "conversions" \
  --funnel-stage "cold" \
  --variations 5
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bibles** - Read `skills/SKILL_BIBLE_facebook_ads.md` and `skills/SKILL_BIBLE_paid_advertising_mastery.md`
4. **Research Competitors** - Analyze competitor ads via Facebook Ad Library insights
5. **Define Audiences** - Build targeting for cold, warm, and hot audiences
6. **Generate Ad Copy** - Create primary text, headlines, and descriptions with A/B variants
7. **Create Creative Briefs** - Image, video, and carousel concepts
8. **Build Campaign Structure** - Campaigns → Ad Sets → Ads hierarchy
9. **Write Optimization Playbook** - Day-by-day and week-by-week optimization guide
10. **Output** - Save all assets to `.tmp/meta_ads_campaigns/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client or brand name |
| `--product` | Yes | Product or service name |
| `--offer` | Yes | What you're promoting (free trial, discount, etc.) |
| `--target-audience` | Yes | Target audience description |
| `--monthly-budget` | No | Monthly ad spend budget |
| `--objective` | No | `awareness`, `traffic`, `conversions`, or `leads` |
| `--funnel-stage` | No | `cold`, `warm`, or `hot` |
| `--variations` | No | Number of ad copy variations |
| `--generate-images` | No | Generate AI ad creatives with fal.ai |

## Quality Checklist
- [ ] 5+ ad copy variations with different hooks
- [ ] Headlines under 40 characters
- [ ] Primary text under 125 characters for mobile
- [ ] Audience targeting defined for each funnel stage
- [ ] Creative briefs include specs (1080x1080, 1080x1920)
- [ ] Campaign structure follows best practices
- [ ] Budget allocation across ad sets is reasonable
- [ ] CTAs are clear and action-oriented
- [ ] Optimization playbook included

## Related Directives
- `directives/ultimate_meta_ads_campaign.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_facebook_ads.md`
- `skills/SKILL_BIBLE_meta_ads_tutorial_facebook_adv.md`
- `skills/SKILL_BIBLE_meta_ads_manager_tutorial_face.md`
- `skills/SKILL_BIBLE_meta_ads_manager_technical.md`
- `skills/SKILL_BIBLE_paid_advertising_mastery.md`
- `skills/SKILL_BIBLE_facebook_ad_copywriting_direct.md`
