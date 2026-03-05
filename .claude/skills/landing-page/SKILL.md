---
name: landing-page
description: Generate high-converting landing pages with AI copy and modern design, optionally deployed to Cloudflare Pages. Use when user asks to create a landing page, build a sales page website, generate a product page, or make a conversion-optimized page.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# AI Landing Page Generator

## Goal
Generate beautiful, high-converting landing pages using AI-written copy and modern HTML/CSS design with responsive layouts, then optionally deploy to Cloudflare Pages.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`
- `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` in `.env` (only if deploying)
- `PERPLEXITY_API_KEY` in `.env` (only if using `--research` flag)

## Execution Command

```bash
python3 .claude/skills/landing-page/generate_landing_page.py \
  --product "AI Course for Marketers" \
  --headline "Master AI Marketing in 30 Days" \
  --price "$497" \
  --target-audience "Marketing professionals and agency owners" \
  --style "modern-gradient" \
  --output-dir .tmp/landing_pages/ai_course
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Load Skill Bible** - Read landing page and funnel copywriting skill bibles
4. **Research (Optional)** - If `--research` flag, use Perplexity for audience/competitor intel
5. **Generate Copy** - AI generates PROPS-formula copy (Problem, Result, Objection, Proof, Simple next step)
6. **Build HTML/CSS** - Generate responsive landing page with selected design style
7. **Local Save** - Save to `.tmp/landing_pages/{project_slug}/`
8. **Deploy (Optional)** - If `--deploy` flag, push to Cloudflare Pages
9. **Output** - Return live URL or local file path

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--product` | Yes | Product or service name |
| `--headline` | No | Main headline (AI generates if not provided) |
| `--subheadline` | No | Supporting subheadline |
| `--price` | No | Price point (e.g., $497) |
| `--target-audience` | No | Target audience description |
| `--website` | No | Company website for research |
| `--style` | No | Design style: modern-gradient, minimal-clean, dark-mode, neo-noir, editorial-luxury, electric-tech, warm-organic, neubrutalism, bold-colors, professional (default: modern-gradient) |
| `--research` | No | Flag to run market research first |
| `--deploy` | No | Flag to auto-deploy to Cloudflare Pages |
| `--project-name` | No | Cloudflare Pages project name |
| `--output-dir` | No | Local output directory |
| `--cta-text` | No | CTA button text |
| `--cta-url` | No | CTA button URL |

## Quality Checklist
- [ ] PROPS structure followed (Problem → Result → Objection → Proof → Simple next step)
- [ ] Headline is clear, under 10 words, benefit-focused
- [ ] Problem section uses 3-layer depth (surface → tried everything → belief)
- [ ] Unique mechanism is named and differentiated
- [ ] Offer stack shows value breakdown with crossed-out prices
- [ ] Guarantee in highlighted box
- [ ] Mobile responsive (375px, 768px, 1024px)
- [ ] CTA buttons are prominent and action-oriented
- [ ] Page loads under 3 seconds (self-contained HTML)
- [ ] Follows agency brand voice

## Related Directives
- `directives/ai_landing_page_generator.md`
- `directives/funnel_copywriter.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_landing_page_ai_mastery.md`
- `skills/SKILL_BIBLE_high_converting_landing_pages_.md`
- `skills/SKILL_BIBLE_landing_page_copywriting.md`
- `skills/SKILL_BIBLE_landing_page_design_tutorial_h.md`
- `skills/SKILL_BIBLE_landing_page_website.md`
- `skills/SKILL_BIBLE_funnel_copywriting_mastery.md`
- `skills/SKILL_BIBLE_frontend_design_mastery.md`
- `skills/SKILL_BIBLE_sales_funnel_structure.md`
