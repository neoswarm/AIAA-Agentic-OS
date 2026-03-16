---
id: seo_content_brief_generator
name: SEO Content Brief Generator
version: 1.0.0
category: SEO & Content
type: manual
description: >
  Reverse-engineers the top 5 ranking pages for any keyword and produces a
  consensus-based content brief in under 10 minutes. Extracts mandatory
  topics, entities, heading structures, differentiation opportunities, and
  gap analysis vs. an existing page. Claude-native — no API cost, no
  third-party tool required.
execution_scripts: []
env_vars: []
integrations:
  - claude_code_native
  - google_docs (optional)
  - slack (optional)
skill_bibles:
  - SKILL_D100_seo_analysis.md
related_directives:
  - ultimate_seo_campaign.md
  - seo_audit_automation.md
  - blog_post_writer.md
---

# SEO Content Brief Generator

## What This Workflow Is

A Claude-native process that reverse-engineers the top 5 Google search results
for any keyword and outputs a production-ready content brief — including every
heading, entity, question, mandatory topic, and differentiation opportunity
found across competitors. Optionally compares the brief against your existing
page and prioritizes gaps by likely ranking impact.

Produces better output than £200+/month SEO tools because it processes all
5 competitor pages simultaneously with full context — not sampled data.

---

## What It Does

1. **Collect** — User Googles the target keyword and copies the full content of
   the top 5 ranking pages
2. **Analyse** — Claude analyses all 5 pages simultaneously: headings, entities,
   questions, word counts, structure patterns
3. **Brief** — Outputs a complete, writer-ready content brief with mandatory
   topics, differentiation opportunities, and internal link hooks
4. **Gap Analysis** (optional) — Compares brief against an existing page and
   prioritizes what to add, fix, or expand

---

## Prerequisites

### Required
- Target keyword identified
- Google Search access (to find top 5 pages)
- Access to Claude Code (this session)

### Optional
- Existing page content (for gap analysis step)
- Google Docs credentials (to auto-publish the brief)
- Slack webhook (to notify team when brief is ready)

### No API keys needed
This workflow runs entirely within Claude Code. Zero additional cost on Claude Max.

---

## How to Run

### Standard (Copy-Paste Method)

**Step 1:** Google your target keyword. Open the top 5 organic results in
separate tabs. Exclude ads, featured snippets, and YouTube results.

**Step 2:** On each page, select all (Ctrl+A / Cmd+A) and copy (Ctrl+C / Cmd+C).
Paste all 5 pages into a single message to Claude Code, clearly separated:

```
=== PAGE 1: [URL] ===
[paste full content]

=== PAGE 2: [URL] ===
[paste full content]

... repeat for pages 3, 4, 5
```

**Step 3:** Paste the content and use **Prompt A** below.

**Step 4 (optional):** Paste your existing page and use **Prompt B** for
gap analysis.

---

## Core Prompts

### Prompt A — Generate the Brief

```
Analyse these 5 pages that rank in the top 5 for [KEYWORD].

Create a comprehensive content brief that includes:

1. HEADING STRUCTURE — Every H1, H2, and H3 used across all 5 pages.
   Group similar headings together. Flag which appear in 3+ pages.

2. MANDATORY ENTITIES — Every person, brand, place, concept, tool, or study
   mentioned by at least 3 out of 5 pages. These are non-negotiable to include.

3. QUESTIONS ANSWERED — Every question addressed across the pages
   (explicit FAQ sections + implicit questions answered in body copy).

4. MANDATORY TOPICS — Topics and subtopics covered by 4–5 of the pages.
   These are what Google has decided belong in this content.

5. DIFFERENTIATION OPPORTUNITIES — Topics covered by only 1–2 pages that
   represent a chance to stand out. Flag which are likely high-impact vs. filler.

6. CONTENT STRUCTURE — Average word count, average number of H2s, whether
   pages use FAQs, tables, lists, or other formats predominantly.

7. INTERNAL LINK OPPORTUNITIES — Based on the topics covered, suggest 5–8
   internal links (as [anchor text] → [topic]) a site in this niche should have.

8. SCHEMA MARKUP — Recommend schema types based on the content format and
   topic (FAQ, HowTo, Article, MedicalWebPage, etc.).

Format the output as a structured content brief I can hand to a writer.
Use clear headers. Keep the brief scannable.
```

---

### Prompt B — Gap Analysis vs. Existing Page

```
Here is my existing page on [KEYWORD]:

[PASTE YOUR EXISTING PAGE CONTENT]

Compare it against the content brief you just created. Produce:

1. CRITICAL GAPS — Topics, entities, or headings present in 4–5 competitor
   pages that I'm completely missing. Prioritize these first.

2. PARTIAL GAPS — Areas where I touch on something but go less deep than
   competitors. Suggest specific additions.

3. MY ADVANTAGES — What does my page cover that competitors don't?
   Assess whether these are genuine differentiation signals or just noise.

4. PRIORITY ACTION LIST — Rank the 10 most impactful changes I can make,
   ordered by estimated ranking impact (High / Medium / Low).

5. QUICK WINS — Changes I can make in under 30 minutes (meta title, H2
   restructure, missing entity mentions, FAQ additions).
```

---

### Prompt C — Health Practice Variant (Functional Medicine / Naturopathic)

Use this variant when briefing content for healthbiz.io or any health practice client:

```
Analyse these 5 pages that rank in the top 5 for [KEYWORD].

In addition to the standard brief analysis, also include:

- E-E-A-T SIGNALS — What credentials, author bios, clinical references, or
  trust signals do competitors use? Which are mentioned by 3+ pages?

- PATIENT INTENT LANGUAGE — List the exact phrases and questions patients
  use when searching this topic. What stage of awareness does each page target?

- LOCAL SEO ELEMENTS — Do any pages incorporate city/region targeting,
  Google Maps references, or practice-specific schema? Flag patterns.

- AI OVERVIEW CANDIDATES — Which sections or questions from these pages are
  most likely being pulled into Google AI Overviews? Structure these as
  direct-answer passages in the brief.

- REGULATORY/COMPLIANCE WATCH — Flag any health claims made by competitors
  that could be risky. Note where competitors add disclaimers.

Then produce the full content brief in the standard format.
```

---

## Process — Step by Step

### 1. Identify Target Keyword
- Use Semrush (via MCP) or existing keyword research from SEO-STRATEGY.md
- Confirm search intent: informational, commercial, navigational, transactional
- Note: KD, search volume, and primary intent before starting

### 2. Collect Competitor Content
- Search keyword in incognito mode (eliminates personalization)
- Take top 5 **organic** results only — skip:
  - Google Ads (marked "Sponsored")
  - Featured snippets (already captured in organic results)
  - YouTube results
  - Reddit/Quora (unless explicitly targeting these formats)
- For each page: Ctrl+A → Ctrl+C → paste into staging doc

### 3. Run the Analysis (Prompt A)
- Paste all 5 pages + Prompt A into this Claude Code session
- Review the output — flag anything that seems wrong or needs clarification
- Save output as `.tmp/briefs/[keyword-slug]-brief.md`

### 4. Gap Analysis (Prompt B — if existing page exists)
- Paste existing page + Prompt B
- Focus on "Critical Gaps" and "Quick Wins" first
- Save gap analysis as `.tmp/briefs/[keyword-slug]-gap-analysis.md`

### 5. Brief Refinement
- Add any additional context Claude may not have from page content alone:
  - Internal linking targets (pages that exist on the site)
  - Tone/voice requirements from `context/brand_voice.md`
  - Client-specific rules from `clients/{client}/rules.md`
- Finalize the writer brief

### 6. Delivery (Optional)
```bash
# Save to Google Doc
python3 execution/create_google_doc.py \
  --file ".tmp/briefs/[keyword-slug]-brief.md" \
  --title "Content Brief: [Keyword]"

# Notify team
python3 execution/send_slack_notification.py \
  --message "Content brief ready: [Keyword] — [Google Doc link]" \
  --channel "#seo"
```

---

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `target_keyword` | Yes | The exact keyword to brief for |
| `top_5_pages` | Yes | Full text content of top 5 ranking pages |
| `existing_page` | No | Your current page content (for gap analysis) |
| `client_name` | No | Load client rules/preferences if client work |
| `page_url` | No | URL of existing page (for reference in output) |
| `word_count_target` | No | Override suggested word count if needed |

---

## Outputs

```
.tmp/briefs/
├── [keyword-slug]-brief.md          # Full content brief (writer-ready)
├── [keyword-slug]-gap-analysis.md   # Gap analysis vs. existing page
└── [keyword-slug]-metadata.json     # Keyword + competitor metadata
```

### Brief Format (What Claude Produces)

```markdown
# Content Brief: [Keyword]
**Target Keyword:** [keyword]
**Search Intent:** [Informational / Commercial / Transactional]
**Recommended Word Count:** [avg ± 20%]
**Priority Schema:** [Schema types]

## Mandatory Headings (3-5/5 competitors use these)
...

## Mandatory Entities
...

## Questions to Answer
...

## Mandatory Topics (4-5/5 pages)
...

## Differentiation Opportunities (1-2/5 pages — high impact)
...

## Differentiation Opportunities (1-2/5 pages — low priority)
...

## Recommended Content Structure
...

## Internal Link Opportunities
...

## Schema Markup Plan
...

## Writer Notes
...
```

---

## Quality Gates

**Before running the brief:**
- [ ] Confirmed keyword intent (not mixed)
- [ ] Collected exactly 5 organic results (not ads, not YouTube)
- [ ] Pages collected in incognito mode
- [ ] Existing page URL noted (if gap analysis needed)

**After brief is generated:**
- [ ] Mandatory topics list makes sense for the keyword
- [ ] Entity list includes no obvious false positives
- [ ] Word count recommendation is realistic for the topic
- [ ] Internal link suggestions map to real pages that exist
- [ ] Health practice content: E-E-A-T signals noted, compliance flags reviewed

---

## Edge Cases

| Situation | Solution |
|-----------|----------|
| Top 5 results are thin / low quality | Note this — it means the bar is low. Brief can be shorter than usual |
| All 5 pages are the same domain | Expand to top 5 *unique domains* in the results |
| Page behind paywall | Skip it, use next organic result instead |
| Keyword returns news/current events | Add date context to prompts; note content has short shelf life |
| Foreign language results appear | Use incognito + set Google to correct region/language first |
| Existing page is very long (10K+ words) | Paste summary/outline only for gap analysis |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Brief generation time | < 10 minutes (excluding collection) |
| Mandatory topics coverage | 90%+ of competitor mandatory topics in brief |
| Writer time saved vs. manual brief | 3–4 hours → under 30 min |
| Gap analysis precision | Every "Critical Gap" produces an actionable edit |

---

## Related Skill Bibles

- `skills/SKILL_D100_seo_analysis.md` — Full SEO analysis methodology
- `skills/SKILL_BIBLE_vsl_writing_production.md` — If brief is for a video/VSL page
- `skills/SKILL_BIBLE_funnel_copywriting_mastery.md` — If brief targets a conversion page

---

## Self-Annealing Notes

_Update this section after each use:_

- **2026-03-01:** Initial directive created. Health practice variant (Prompt C) added
  based on healthbiz.io use case. Functional medicine content has low KD terms
  that move fast — use the standard brief but add E-E-A-T section always.
- Edge case: Reddit/Quora often appears in top 5 for functional medicine terms.
  Skip them unless the goal is matching forum-style Q&A content.
