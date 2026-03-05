---
name: vsl-funnel
description: Create complete VSL funnels with research, script, sales page, and email sequence. Use when user asks to build a VSL funnel, create a video sales letter, or generate funnel copy.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# VSL Funnel Creator

## Goal
Orchestrate the complete VSL funnel creation pipeline: research → VSL script → sales page → email sequence → delivery.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env`
- `PERPLEXITY_API_KEY` for market research
- `GOOGLE_APPLICATION_CREDENTIALS` for Google Doc delivery
- `SLACK_WEBHOOK_URL` for notifications (optional)

## Execution Command

```bash
# Complete pipeline (recommended)
python3 .claude/skills/vsl-funnel/generate_complete_vsl_funnel.py \
  --company "Acme Corp" \
  --website "https://acmecorp.com" \
  --offer "B2B Lead Generation"

# Individual steps
python3 .claude/skills/company-research/research_company_offer.py --company "Acme Corp" --website "https://acmecorp.com"
python3 .claude/skills/vsl-script/generate_vsl_script.py --research-file ".tmp/research.json"
python3 .claude/skills/sales-page/generate_sales_page.py --vsl-file ".tmp/vsl_script.md"
python3 .claude/skills/email-sequence/generate_email_sequence.py --research-file ".tmp/research.json"
```

## Process Steps
1. **Load Context** - Read `context/agency.md`, `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Market Research** - Deep research via Perplexity on company, offer, competitors
4. **VSL Script** - Generate 3000+ word VSL script with hook, problem, solution, offer, CTA
5. **Sales Page** - Generate long-form sales page copy (2000+ words)
6. **Email Sequence** - 7-email nurture sequence (300+ words each)
7. **Google Doc Delivery** - Upload all deliverables to Google Docs
8. **Slack Notification** - Send completion notification with doc links

## Outputs
- `.tmp/vsl_funnel_<company>/01_research.md`
- `.tmp/vsl_funnel_<company>/02_vsl_script.md`
- `.tmp/vsl_funnel_<company>/03_sales_page.md`
- `.tmp/vsl_funnel_<company>/04_email_sequence.md`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--company` | Yes | Company name |
| `--website` | Yes | Company website URL |
| `--offer` | Yes | Main offer/product |
| `--industry` | No | Industry vertical |
| `--price_point` | No | Product price point |
| `--vsl_length` | No | short/medium/long (default: medium) |

## Quality Checklist
- [ ] Research has 5+ sources and competitor analysis
- [ ] VSL script is 3000+ words with Hook, Problem, Solution, Offer, CTA
- [ ] Sales page is 2000+ words with proper sections
- [ ] Email sequence has 7 emails, 300+ words each
- [ ] All deliverables uploaded to Google Docs
- [ ] Slack notification sent with links

## Related Skill Bibles
- `skills/SKILL_BIBLE_vsl_writing_production.md`
- `skills/SKILL_BIBLE_vsl_script_mastery_fazio.md`
- `skills/SKILL_BIBLE_funnel_copywriting_mastery.md`
