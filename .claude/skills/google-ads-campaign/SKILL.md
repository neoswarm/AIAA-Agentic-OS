---
name: google-ads-campaign
description: Generate complete Google Ads campaigns with keyword research, ad copy, campaign structure, and bidding strategies. Use when user asks to create Google Ads, generate PPC campaigns, build search ads, write Google ad copy, or set up Performance Max campaigns.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Google Ads Campaign Generator

## Goal
Create complete Google Ads campaign systems from keyword research to ad copy generation. Produces search, display, YouTube, and Performance Max campaign structures with all ad assets, negative keyword lists, audience targeting, bidding strategy recommendations, and conversion tracking setup guides.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` — AI content generation
- `PERPLEXITY_API_KEY` in `.env` — Competitive research

## Execution Command

```bash
python3 .claude/skills/google-ads-campaign/generate_meta_ads_campaign.py \
  --client "Acme Corp" \
  --product "Project Management Software" \
  --offer "Free 14-day trial" \
  --target-audience "B2B SaaS decision makers" \
  --monthly-budget 10000
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bibles** - Read `skills/SKILL_BIBLE_paid_advertising_mastery.md` and `skills/SKILL_BIBLE_google_ads_agency_ppc_advertis.md`
4. **Conduct Keyword Research** - Research brand, generic, competitor, long-tail, problem-aware, and solution-aware keywords with volume and competition metrics
5. **Build Ad Group Structure** - Create themed ad groups organized by feature, pain point, and solution
6. **Generate Ad Copy** - Write responsive search ads (15 headlines, 4 descriptions), YouTube ad scripts, sitelinks, callouts, and structured snippets
7. **Create Negative Keyword Lists** - Universal negatives plus industry-specific exclusions
8. **Define Audience Targeting** - Build audience segments and targeting recommendations
9. **Set Bidding Strategy** - Recommend bidding approach based on budget and objectives
10. **Create Conversion Tracking Guide** - Document tracking setup for conversions

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client/brand name |
| `--product` | Yes | Product/service name |
| `--offer` | Yes | What you're promoting |
| `--target-audience` | Yes | Target audience description |
| `--monthly-budget` | No | Monthly ad spend (default: 5000) |
| `--objective` | No | Campaign objective: conversions, leads, traffic, awareness (default: conversions) |
| `--funnel-stage` | No | cold, warm, hot (default: cold) |
| `--variations` | No | Number of ad variations (default: 5) |
| `--generate-images` | No | Generate ad images (flag) |

## Quality Checklist
- [ ] Keywords grouped thematically
- [ ] Headlines under 30 characters each
- [ ] Descriptions under 90 characters each
- [ ] Landing page matches ad message
- [ ] Conversion tracking setup documented
- [ ] Negative keywords added
- [ ] Ad extensions configured
- [ ] Budget allocated correctly across campaigns

## Related Directives
- `directives/ultimate_google_ads_campaign.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_paid_advertising_mastery.md`
- `skills/SKILL_BIBLE_google_ads_agency_ppc_advertis.md`
- `skills/SKILL_BIBLE_ad_copywriting.md`
- `skills/SKILL_BIBLE_lead_generation_mastery.md`
