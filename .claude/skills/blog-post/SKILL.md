---
name: blog-post
description: Generate SEO-optimized blog posts with keyword targeting. Use when user asks to write a blog post, create an article, or generate long-form content.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Blog Post Writer

## Goal
Generate SEO-optimized, long-form blog posts with keyword targeting, proper structure, and compelling content.

## Prerequisites
- `OPENROUTER_API_KEY` or `OPENAI_API_KEY` in `.env`

## Execution Command

```bash
python3 .claude/skills/blog-post/generate_blog_post.py \
  --topic "How to Scale Cold Email Outreach" \
  --keyword "cold email outreach" \
  --length "1500" \
  --output .tmp/blog_post.md
```

## Process Steps
1. **Load Context** - Read `context/agency.md` and `context/brand_voice.md`
2. **Load Client Context** - If client work, read `clients/{client}/*.md`
3. **Keyword Research** - Identify primary + secondary keywords
4. **Outline** - Generate H1/H2/H3 structure
5. **Draft** - Write 1200+ word article with SEO optimization
6. **Optimize** - Add meta description, keyword density 1-3%
7. **Quality Check** - Verify structure, length, and SEO elements
8. **Deliver** - Save to `.tmp/`, optionally upload to Google Docs

## Input Specifications
| Arg | Required | Description |
|-----|----------|-------------|
| `--topic` | Yes | Blog post topic |
| `--keyword` | No | Target SEO keyword |
| `--length` | No | Word count target (default: 1500) |
| `--tone` | No | Writing tone (professional/casual/educational) |
| `--output` | No | Output path (default: `.tmp/blog_post.md`) |

## Quality Checklist
- [ ] 1200+ words minimum
- [ ] H1 title with primary keyword
- [ ] 3+ H2 subheadings
- [ ] Introduction and conclusion sections
- [ ] Keyword density 1-3%
- [ ] Meta description included
- [ ] Internal/external links suggested
- [ ] Follows agency brand voice

## Related Directives
- `directives/blog_post_writer.md`

## Related Skill Bibles
- `skills/SKILL_BIBLE_seo_content_strategy.md`
