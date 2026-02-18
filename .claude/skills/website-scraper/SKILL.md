---
name: website-scraper
description: Scrape contact information from company websites. Use when user asks to find website contacts, extract emails from a site, scrape company contact info, or get website email addresses.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Website Contact Scraper

## Goal
Extract contact information from company websites including emails, phone numbers, social media profiles, and contact page URLs by scraping main pages, contact pages, about pages, and footers.

## Prerequisites
- No API keys required for basic scraping

## Execution Command

```bash
python3 .claude/skills/website-scraper/scrape_website_contacts.py \
  --url "https://example.com" \
  --output .tmp/contacts.json
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Prepare URL** - Ensure target URL is properly formatted with https://
4. **Run Scraper** - Script checks main page, contact page, about page, and footer
5. **Review Results** - Verify extracted emails, phones, and social profiles

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--url` | Yes | Website URL to scrape (auto-prepends https:// if missing) |
| `--output` | No | Output file path (default: .tmp/contacts.json) |

## Quality Checklist
- [ ] Emails extracted and validated (no image file extensions)
- [ ] Phone numbers found and formatted
- [ ] Social media profiles identified (LinkedIn, Twitter, Facebook)
- [ ] Contact page URLs discovered
- [ ] Output JSON is valid and well-structured
- [ ] Scrape timestamp recorded

## Related Directives
- `directives/website_contact_scraper.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_lead_generation.md`
- `skills/SKILL_BIBLE_web_scraping.md`
