---
name: fb-ad-library
description: Scrape and analyze Facebook Ad Library competitor ads with AI-powered creative, copy, and strategy analysis. Use when user asks to analyze competitor ads, research Facebook ad library, study ad creatives, or audit competitor ad strategies.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Facebook Ad Library Analysis Automation

## Goal
Scrape Facebook Ad Library for competitor ads by keyword, download media assets (images and videos), and use AI (Gemini vision) to analyze each ad's creative approach, copy strategy, and persuasion techniques. Outputs structured summaries to a Google Sheet for competitive intelligence.

## Prerequisites
- `GEMINI_API_KEY` in `.env` — Video/image analysis via Gemini
- `GOOGLE_APPLICATION_CREDENTIALS` — Google Sheets and Drive access
- Ad Library scraper access (Apify or custom)

## Execution Command

```bash
python3 .claude/skills/fb-ad-library/fb_ad_library_analyzer.py \
  --keyword "saas marketing" \
  --output .tmp/fb-ads/analysis.json
```

**Note:** Requires Facebook Ad Library scraper (Apify or similar). Uses placeholder data until integrated.

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bibles** - Read `skills/SKILL_BIBLE_meta_ads_manager_technical.md` for ad analysis framework
4. **Submit Search Keyword** - Enter the Facebook Ad Library search keyword to target (e.g., "skincare brand", "SaaS tool")
5. **Run Ad Library Scraper** - Scrape matching ads from Facebook Ad Library with metadata
6. **Filter Results** - Filter for ads with significant engagement (likes threshold)
7. **Classify Ad Types** - Separate results into image ads, video ads, and text-only ads
8. **Process Image Ads** - Download images, analyze with Gemini vision for creative elements, copy hooks, and persuasion techniques
9. **Process Video Ads** - Download videos, upload to Gemini, analyze for script structure, visual storytelling, and CTA placement
10. **Process Text Ads** - Analyze copy-only ads for messaging frameworks and value propositions
11. **Generate Summaries** - Create structured analysis for each ad type with scoring
12. **Output to Google Sheet** - Write all analysis results to a Google Sheet organized by ad type

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--keyword` | Yes | Facebook Ad Library search keyword |
| `--output_sheet` | No | Google Sheet URL for output |

## Quality Checklist
- [ ] Search keyword returns 10+ relevant ads
- [ ] Image ads analyzed for visual creative elements
- [ ] Video ads analyzed for script structure and storytelling
- [ ] Copy hooks and CTAs identified for each ad
- [ ] Persuasion techniques categorized
- [ ] Results organized by ad type in Google Sheet
- [ ] Actionable takeaways summarized

## Related Directives
- `directives/facebook_ad_library_analysis_automation.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_meta_ads_manager_technical.md`
- `skills/SKILL_BIBLE_hormozi_ad_analysis.md`
- `skills/SKILL_BIBLE_facebook_ad_copywriting_direct.md`
- `skills/SKILL_BIBLE_ad_creative_hooks.md`
