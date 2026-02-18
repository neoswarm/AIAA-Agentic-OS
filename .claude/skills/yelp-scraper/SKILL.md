---
name: yelp-scraper
description: Scrape and analyze Yelp reviews to find businesses with pain points. Use when user asks to scrape Yelp reviews, find businesses with bad reviews, analyze review sentiment, or identify outreach targets from reviews.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Yelp Review Scraper & Analyzer

## Goal
Search and analyze Yelp reviews for businesses in a specific category and location, identifying pain point patterns and generating outreach-ready intelligence for targeted sales prospecting.

## Prerequisites
- `PERPLEXITY_API_KEY` - For review research and analysis

## Execution Command

```bash
python3 .claude/skills/yelp-scraper/scrape_yelp_reviews.py \
  --business "marketing agency" \
  --location "Los Angeles" \
  --output .tmp/yelp_reviews.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Define Search** - Specify business type/name and location
4. **Run Scraper** - Perplexity-powered search for review themes and sentiment
5. **Analyze Results** - Review pain point patterns for outreach angles

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--business` | Yes | Business name or category to search |
| `--location` | Yes | Geographic location (city, state) |
| `--output` | No | Output file path (default: .tmp/yelp_reviews.json) |

## Quality Checklist
- [ ] Business and location correctly searched
- [ ] Review summary includes positive and negative themes
- [ ] Overall rating captured if available
- [ ] Pain points identified for outreach angles
- [ ] JSON output is valid and timestamped
- [ ] Results saved to .tmp/ directory

## Related Directives
- `directives/yelp_review_scraper.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_lead_generation.md`
- `skills/SKILL_BIBLE_competitive_intelligence.md`
