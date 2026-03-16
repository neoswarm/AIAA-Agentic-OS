# Keyword Research (6 Circles Method)

## What This Workflow Is
**Strategic keyword research system** that transforms business context into a prioritized content plan without expensive tools. Uses the proven 6 Circles Method to expand seed keywords, validates pillars against market reality, and maps keywords to a 90-day content calendar.

## What It Does
1. Generates 20-30 seed keywords from business context
2. Expands keywords using 6 Circles Method (100-200 keywords)
3. Clusters keywords into validated content pillars
4. Prioritizes by business value, opportunity, and speed to win
5. Maps to specific content types and publishing calendar
6. Delivers clear "start here" recommendation

## Prerequisites

### Required API Keys
```
OPENROUTER_API_KEY=your_key           # AI analysis and expansion
PERPLEXITY_API_KEY=your_key           # Competitive research (optional)
```

### Required Skill Files
- `skills/keyword-research.md` (this skill)

## How to Run

```bash
# Full keyword research
python3 execution/keyword_research.py \
  --business "AI marketing consulting for startups" \
  --audience "Funded startups, 10-50 employees, no marketing hire" \
  --goal "Leads for consulting engagements" \
  --timeline "mix" \
  --output output/keyword_research.md

# With website and competitors
python3 execution/keyword_research.py \
  --business "Functional medicine practice" \
  --audience "Patients with chronic illness, mold exposure, gut issues" \
  --website "https://healthpractice.com" \
  --competitors "clevelandclinic.org/functional-medicine,ifm.org" \
  --goal "10 new patients per month" \
  --timeline "quick-wins" \
  --output output/fm_keywords.md
```

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| business | string | Yes | What you sell/offer (1-2 sentences) |
| audience | string | Yes | Who you're targeting (be specific) |
| website | url | No | Your website URL |
| competitors | list | No | Competitor URLs (comma-separated) |
| goal | string | Yes | Campaign goal (traffic/leads/sales/authority) |
| timeline | string | No | quick-wins / long-term / mix (default: mix) |
| output | path | Yes | Output markdown file path |

## Process

### Phase 1: Seed Generation (20-30 keywords)
Generates initial keywords covering:
- **Direct terms** — What you actually sell
- **Problem terms** — What pain you solve
- **Outcome terms** — What results you deliver
- **Category terms** — Broader industry terms

### Phase 2: 6 Circles Expansion (100-200 keywords)
Expands each seed through 6 lenses:
1. **Circle 1: What You Sell** — Products, services, solutions
2. **Circle 2: Problems You Solve** — Pain points, challenges
3. **Circle 3: Outcomes You Deliver** — Results, transformations
4. **Circle 4: Your Unique Positioning** — What makes you different
5. **Circle 5: Adjacent Topics** — Related areas audience explores
6. **Circle 6: Entities to Associate With** — People, tools, frameworks

Uses expansion patterns:
- Question patterns (what, how, why, best)
- Modifier patterns (tools, templates, guide, strategy)
- Comparison patterns (vs, alternatives, review)

### Phase 3: Clustering & Pillar Validation
Groups keywords into content pillars (5-10 per business).

**Critical: 4-Test Pillar Validation**
1. **Search Volume Test** — Does cluster have >1,000 monthly searches?
2. **Market vs Product Test** — Is this what MARKET searches, not just what YOU want to talk about?
3. **Competitive Reality Test** — Can you realistically rank on page 1?
4. **Proprietary Advantage Test** — Do you have unique data/expertise?

**Verdict:** Valid Pillar / Demote to Cluster / Remove

### Phase 4: Prioritization Matrix
Scores each cluster by:
- **Business Value** (High/Medium/Low) — Path to revenue
- **Opportunity** (High/Medium/Low) — Content gaps, weak competition
- **Speed to Win** (Fast/Medium/Long) — 3mo / 6mo / 12mo

**Priority Ranking:**
| Business Value | Opportunity | Speed | Priority |
|---------------|-------------|-------|----------|
| High | High | Fast | **DO FIRST** |
| High | High | Medium | **DO SECOND** |
| High | Medium | Fast | **DO THIRD** |
| Medium | High | Fast | **QUICK WIN** |
| High | Low | Any | **LONG PLAY** |
| Low | Any | Any | **BACKLOG** |

### Phase 5: Content Mapping
Assigns each cluster:
- **Content Type** — Pillar Guide (5-8k words), How-To (2-3k), Comparison (2.5-4k), Listicle (2-3k), Use Case (1.5-2.5k), Definition (1.5-2.5k)
- **Search Intent** — Informational / Commercial / Transactional
- **Calendar Placement** — Tier 1 (weeks 1-4), Tier 2 (weeks 5-8), Tier 3 (weeks 9-12), Tier 4 (backlog)

## Outputs

### Executive Summary
```
# Keyword Research: [Business Name]

## Top Opportunities
1. [Keyword/cluster] — [Why it's an opportunity]
2. [Keyword/cluster] — [Why it's an opportunity]
3. [Keyword/cluster] — [Why it's an opportunity]

## Quick Wins (3-month potential)
- [Keyword] — [Why quick]

## Long-Term Plays (6-12 months)
- [Keyword] — [Strategy needed]

## Start Here
[Specific first piece of content to create and why]
```

### Pillar Overview
For each pillar:
- Validation results (4 tests)
- Priority level
- Content pieces breakdown
- Target timeline

### 90-Day Content Calendar
Month-by-month breakdown:
- Week-by-week content pieces
- Target keyword clusters
- Content types
- Publishing order

## Success Metrics

**Deliverable Quality:**
- ✅ Clear "start here" recommendation (not just a list)
- ✅ Prioritized by opportunity (not random)
- ✅ Realistic timelines (acknowledges competition)
- ✅ Strategic alignment (connects to business goals)
- ✅ Specific angles (content types and approaches, not just keywords)

**Business Outcomes:**
- 5-10 validated content pillars
- 100-200 keyword opportunities identified
- 90-day actionable content calendar
- Clear competitive positioning
- Proprietary advantage documentation

## Common Mistakes to Avoid

❌ **Product-Centric Keywords** — "Our methodology", "Why we're different"
✅ **Market-Centric Keywords** — What people actually search for

❌ **Pillar Without Volume** — "Claude marketing" (0 searches)
✅ **Validated Pillar** — "AI marketing" (validated volume)

❌ **No Competitive Analysis** — Ignoring DR 80+ domination
✅ **Realistic Assessment** — Finding winnable adjacent terms

❌ **Generic Prioritization** — "This seems important"
✅ **Matrix-Based Priority** — Value × Opportunity × Speed

❌ **Just a Keyword List** — 500 keywords with no action plan
✅ **Strategic Plan** — Clustered, prioritized, mapped to calendar

## Free Tools to Supplement

Validation and data sources:
- **Google Trends** (trends.google.com) — Trend direction, seasonality
- **Google Search** — SERP analysis, autocomplete, People Also Ask
- **AnswerThePublic** (free tier) — Question-based keywords
- **AlsoAsked** (free tier) — PAA relationship mapping
- **Reddit/Quora** — Real user language and questions

## Integration with Other Workflows

**Before keyword-research:**
- `research_company_offer.py` — Understand target market
- `research_prospect_deep.py` — Audience pain points

**After keyword-research:**
- `generate_blog_post.py` — Execute content creation
- `generate_content_calendar.py` — Schedule publishing
- `create_google_doc.py` — Document deliverable
- `generate_seo_audit.py` — Technical optimization

## Example Output Structure

```
# Keyword Research: Functional Medicine Practice

## Executive Summary
Top 3 opportunities identified with clear competitive gaps...

## Phase 1: Seed Keywords (28 generated)
- Direct: functional medicine doctor, integrative medicine...
- Problem: chronic illness, mold exposure, gut issues...
- Outcome: root cause treatment, symptom resolution...
- Category: holistic health, alternative medicine...

## Phase 2: Expanded Keywords (187 total)

### Circle 1: What You Sell
- Functional medicine doctor near me
- Integrative health practitioner
- Root cause medicine specialist

### Circle 2: Problems You Solve
- Mold illness treatment
- SIBO doctor
- Chronic fatigue specialist

[... continues through all 6 circles ...]

## Phase 3: Content Pillars (6 validated)

### Pillar 1: Mold Illness Recovery
**Validation Results:**
- Search Volume: PASS — 4,200/mo cluster volume
- Market-Centric: PASS — "Mold illness" vs "Our mold protocol"
- Competitive: PASS — Weak content from DR 20-40 sites
- Proprietary: YES — Custom mold calculator, 15 years patient experience

**VERDICT:** VALID PILLAR — DO FIRST

**Content Clusters:**
- Mold exposure symptoms (880/mo, 35% difficulty)
- CIRS treatment protocol (160/mo, 28% difficulty)
- Mycotoxin testing (240/mo, 32% difficulty)

[... continues for all pillars ...]

## Phase 4: Priority Matrix

| Pillar | Business Value | Opportunity | Speed | Priority |
|--------|---------------|-------------|-------|----------|
| Mold Illness | High | High | Fast | DO FIRST |
| Gut Health | High | High | Medium | DO SECOND |
| Hormone Balance | High | Medium | Fast | DO THIRD |

## Phase 5: 90-Day Content Calendar

### Month 1: Foundation
- Week 1-2: "Complete Guide to Mold Illness Recovery" (Pillar, 6k words)
- Week 3: "25 Mold Exposure Symptoms You're Missing" (Listicle, 2.5k)
- Week 4: "How to Test for Mold Illness: Complete Protocol" (How-To, 3k)

### Month 2: Expansion
[... continues ...]

## Start Here
Create "Complete Guide to Mold Illness Recovery" first because:
1. Highest search volume cluster (4,200/mo)
2. Weak existing content (opportunity)
3. Your unique expertise (mold calculator, patient experience)
4. Fast ranking potential (3 months)
5. Commercial intent (leads to consultations)
```

## Notes

This skill produces **strategic direction**, not:
- Live search volume data (supplement with free tools)
- Automated SERP scraping (manual review required)
- Actual content writing (separate workflow)
- Technical SEO implementation (separate audit)

The output is an actionable plan. Execution happens through other workflows.

---

*Follows skill: skills/keyword-research.md*
*Uses: 6 Circles Method, 4-Test Pillar Validation, Priority Matrix*
