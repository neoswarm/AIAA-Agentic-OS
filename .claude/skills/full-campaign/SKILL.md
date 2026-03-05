---
name: full-campaign
description: Generate a complete end-to-end marketing campaign with research, Meta ads, landing page, CRM setup, and follow-up sequences. Use when user asks to create a full campaign, build a complete marketing campaign, generate campaign assets, or run the campaign pipeline.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Full Campaign Pipeline

## Goal
Generate a complete end-to-end campaign: client research, Meta Ads setup with targeting, 10+ ad copy variations, AI-generated ad images, full landing page, landing page images, CRM pipeline setup, and 5 follow-up email/SMS sequences.

## Prerequisites
- `OPENROUTER_API_KEY` in `.env` (for Claude — copy, pages, sequences)
- `PERPLEXITY_API_KEY` in `.env` (for research, optional but recommended)
- `OPENAI_API_KEY` in `.env` (for DALL-E image generation, optional)

## Execution Command

```bash
python3 .claude/skills/full-campaign/full_campaign_pipeline.py \
  --client "Acme Corp" \
  --website "https://acmecorp.com" \
  --offer "AI Lead Generation" \
  --budget 5000
```

### Full Options

```bash
python3 .claude/skills/full-campaign/full_campaign_pipeline.py \
  --client "Premium Coaching" \
  --website "https://premiumcoaching.com" \
  --offer "Executive Coaching Program" \
  --budget 10000 \
  --output-dir .tmp/campaigns/premium
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Phase 1: Research** - Deep market research (company, audience, competitors, pain points)
4. **Phase 2: Meta Ads Setup** - Campaign structure, ad sets, targeting, budget allocation
5. **Phase 3: Ad Copy** - 10 ad variations across PAS, Story, Direct Response, Social Proof
6. **Phase 4: Ad Images** - 5 image concepts with DALL-E prompts
7. **Phase 5: Landing Page** - Full sales page with all sections
8. **Phase 6: Landing Page Images** - 5 section images with prompts
9. **Phase 7: CRM Setup** - 10+ pipeline stages, lead scoring, automation triggers
10. **Phase 8: Follow-up Sequences** - Welcome, Pre-Call, No-Show, Post-Call, Long-term Nurture

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--client` | Yes | Client/company name |
| `--website` | Yes | Client website URL |
| `--offer` | Yes | Main offer/product name |
| `--budget` | No | Monthly ad budget (default: 5000) |
| `--output-dir` | No | Output directory (default: .tmp/campaigns) |

## Quality Checklist
- [ ] Research includes 5+ pain points and competitor analysis
- [ ] 10 ad copy variations generated across 4 frameworks
- [ ] Landing page has all 7 sections (hero, problem, solution, benefits, social proof, FAQ, CTA)
- [ ] 5 email sequences with complete individual emails
- [ ] CRM pipeline has 10+ stages with automation triggers
- [ ] All 8 output files saved successfully
- [ ] Total cost under $1.00 per campaign

## Related Directives
- `directives/full_campaign_pipeline.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_meta_ads_manager_technical.md`
- `skills/SKILL_BIBLE_agency_funnel_building.md`
- `skills/SKILL_BIBLE_funnel_copywriting_mastery.md`
- `skills/SKILL_BIBLE_email_campaign_mastery.md`
