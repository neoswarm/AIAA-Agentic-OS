---
name: seo-audit
description: Run comprehensive SEO audits with technical analysis and actionable recommendations. Use when user asks to audit a website's SEO, check technical SEO, or analyze on-page optimization.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# SEO Audit Generator

## Goal
Crawl a website and generate a comprehensive SEO audit report with prioritized fixes, covering technical SEO, on-page optimization, content analysis, and Core Web Vitals.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `PAGESPEED_API_KEY` for Core Web Vitals (optional)

## Execution Command

```bash
python3 .claude/skills/seo-audit/generate_seo_audit.py \
  --url "https://example.com" \
  --output ".tmp/seo_audit.md"
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read `skills/SKILL_BIBLE_seo_agency_local_seo_seo_strat.md`
4. **Crawl Website** - Fetch pages up to specified depth
5. **Technical Analysis** - Check site speed, mobile-friendliness, HTTPS, sitemaps, robots.txt, broken links, redirects, canonical tags, schema markup
6. **On-Page Analysis** - Audit title tags, meta descriptions, H1-H6 structure, image alt text, internal linking, content length
7. **Generate Report** - Prioritized findings with fix instructions (Critical → Warning → Info)
8. **Output** - Save report to `.tmp/`

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--url` | Yes | Website URL to audit |
| `--output` | No | Output file path (default: `.tmp/seo_audit.md`) |

## Quality Checklist
- [ ] All major technical SEO factors checked
- [ ] Issues prioritized by severity (Critical/Warning/Info)
- [ ] Each issue includes specific fix instructions
- [ ] Core Web Vitals scores included (if API available)
- [ ] On-page elements audited per page
- [ ] Actionable recommendations with estimated impact
- [ ] Executive summary included

## Related Directives
- `directives/seo_audit_automation.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_seo_agency_local_seo_seo_strat.md`
- `skills/SKILL_BIBLE_marketing_strategy_advanced.md`
- `skills/SKILL_BIBLE_content_strategy_growth.md`
