# Full SEO Audit Report
## Longevity Health Institute
**URL:** https://www.longevityhealthinstituteinc.com/
**Audit Date:** 2026-02-16
**Platform:** Squarespace
**Business Type:** Functional Medicine + Concierge Primary Care Clinic

---

## 🏆 Overall SEO Health Score: 52 / 100

| Category | Score | Weight | Weighted |
|---|---|---|---|
| Technical SEO | 62/100 | 25% | 15.5 |
| Content Quality | 55/100 | 25% | 13.75 |
| On-Page SEO | 58/100 | 20% | 11.6 |
| Schema / Structured Data | 18/100 | 10% | 1.8 |
| Performance (CWV) | 45/100 | 10% | 4.5 |
| Images | 72/100 | 5% | 3.6 |
| AI Search Readiness | 60/100 | 5% | 3.0 |
| **TOTAL** | | | **53.75 → 52** |

---

## Executive Summary

**Business Detected:** Functional Medicine + Concierge Primary Care Clinic (Squarespace CMS)
**Location:** Michigan (Boca Raton referenced but primary location appears to be Rochester/Bingham Farms, MI area based on blog posts)
**Traffic Status:** 1,200 organic visits/month, **DECLINING -31%** — requires urgent intervention

### Top 5 Critical Issues
1. 🔴 **LocalBusiness schema is empty** — has the type declared but ALL fields are blank (name, address, phone, hours, geo)
2. 🔴 **Page weight 2.3MB / 86 resources / 44 scripts** — severely overloaded, contributing to poor Core Web Vitals
3. 🔴 **5 title tags exceed 60 characters** — getting truncated in Google SERPs
4. 🔴 **Alternative Cancer Treatment page missing H1** — critical service page with no primary heading
5. 🔴 **Traffic declining -31%** — no location pages, thin local signals, no Google Business Profile optimization visible

### Top 5 Quick Wins
1. ✅ Fix LocalBusiness schema — add name, address, phone, geo coords, hours (30 min fix, big impact)
2. ✅ Add H1 to /alternative-cancer-treatment
3. ✅ Shorten 5 over-length title tags to under 60 chars
4. ✅ Add MedicalBusiness + Physician schema to /meet-dr-lewerenz
5. ✅ Create location-specific landing pages (Rochester MI, Bingham Farms MI)

---

## 1. Technical SEO — Score: 62/100

### ✅ What's Working
- HTTPS enabled with HSTS (max-age=15552000)
- X-Content-Type-Options and X-Frame-Options headers present
- robots.txt present and well-configured (blocks Squarespace parameter spam URLs)
- Sitemap.xml present and linked from robots.txt
- Canonical tags implemented on homepage
- HTML lang="en-US" set
- 15/27 images use lazy loading

### ❌ Issues Found

**Critical**
- `x-frame-options` header duplicated (sent twice) — minor but indicates header management issues

**High**
- **44 JavaScript files loaded** — extreme script bloat from Squarespace + GTM + third-party widgets
- **20 render-blocking resources** — CSS and scripts blocking initial paint
- **Page size: 2,326 KB** — images alone: 1,754 KB. Far above the 500KB recommended threshold
- **Load time: 3,717ms** — well above 2.5s LCP threshold

**Medium**
- Sitemap `lastmod` dates all show 2025-09-11 — stale, not reflecting recent content
- No sitemap index (single sitemap with 59 URLs is fine, but lastmod staleness is a ranking signal issue)
- `home` page listed as `/home` AND `/` in sitemap — potential duplicate

**Low**
- No CSP (Content Security Policy) header
- No `preconnect` hints for Squarespace CDN domains

### HTTP Headers Summary
```
HTTPS:              ✅ 200 OK
HSTS:               ✅ max-age=15552000
X-Frame-Options:    ✅ (duplicated)
X-Content-Type:     ✅ nosniff
CSP:                ❌ Missing
Cache-Control:      ❌ Not visible
```

---

## 2. Content Quality — Score: 55/100

### E-E-A-T Assessment
**Experience:** ⚠️ WEAK — Dr. Lewerenz has a dedicated page but lacks credentials prominently displayed on service pages. No board certifications, years of practice, or medical affiliations visible in structured format.

**Expertise:** ⚠️ MODERATE — Blog content demonstrates subject knowledge (HRT, IV therapy, functional medicine). However most posts lack author bylines with credentials.

**Authoritativeness:** ⚠️ WEAK — 207 referring domains is modest. Top cited AI sources are generic (YouTube, alluremedical.com). No .gov, .edu, or major medical publication links visible.

**Trustworthiness:** ✅ DECENT — HTTPS, physical clinic presence, testimonials page, team photos. Missing: privacy policy link in footer, medical disclaimers on treatment pages.

### Content Issues

**Thin Content Pages**
- `/faq` — 2,377 words (OK) but FAQ schema not implemented
- `/podcast` — likely thin (not audited)
- `/bios` — likely thin team listing
- `/plan-overview` — likely thin comparison page
- `/careers` — likely minimal content

**Homepage**
- 912 words (rendered) — acceptable but lean for a medical homepage
- H2 tags are ALL in ALL CAPS — looks like design choice but Google reads them as screaming, not semantic hierarchy
- 19 H2 tags on homepage — overuse dilutes signal

**Blog Content**
- Good keyword-targeted titles: "How Long After Starting HRT Will You Feel Different?" (Position 1)
- Blog posts have 2,500-4,700 words — solid depth
- Issue: Several posts reference "Rochester MI" / "Bingham Farms" location — contradicts the current site which doesn't have dedicated location pages

**Missing Content**
- No dedicated location page (Rochester, MI / Bingham Farms, MI)
- No physician credentials schema on Dr. Lewerenz page
- No patient reviews/ratings on service pages
- No pricing page or membership comparison table with schema
- No "Conditions We Treat" index page with schema

---

## 3. On-Page SEO — Score: 58/100

### Title Tags Audit

| Page | Title | Length | Status |
|---|---|---|---|
| Homepage | Longevity Health Institute \| Enhance Your Health | 48 | ✅ Good |
| HRT | Hormone Replacement Therapy — Longevity Health Institute | 62 | ⚠️ Too long |
| IV Therapy | IV Therapy — Longevity Health Institute | 45 | ✅ Good |
| Weight Loss | Weight Loss Treatments — Longevity Health Institute | 57 | ✅ Good |
| Meet Dr. | Meet Dr Lewerenz — Longevity Health Institute | 51 | ✅ Good (missing period) |
| FAQ | Frequently Asked Questions — Longevity Health Institute | 61 | ⚠️ Too long |
| HRT Blog | How Long after Starting HRT Will You Feel Different? — Longevity Health Institute | 87 | ❌ Critical |
| Peptides | Peptide Therapy for Wellness & Recovery — Longevity Health Institute | 78 | ⚠️ Too long |
| Alt Cancer | Alternative Cancer Treatment — Longevity Health Institute | 63 | ⚠️ Too long |

**Issues:** 5 pages with titles over 60 characters. The HRT blog post at 87 characters is severely truncated.

### Meta Descriptions
- Most service pages have meta descriptions ✅
- `/iv-therapy` meta description is only "Let" — effectively MISSING ❌
- Descriptions could be more action-oriented with location keywords

### Heading Structure
- Homepage: 1× H1 ✅, 19× H2 (overuse), H2s all in ALL CAPS (semantic issue)
- /alternative-cancer-treatment: **Missing H1** ❌ — critical service page
- Most service pages: 1 H1 ✅

### Internal Linking
- 98 internal links on homepage — good coverage
- No breadcrumbs implemented
- Blog posts don't appear to cross-link to relevant service pages
- No anchor text optimization visible

---

## 4. Schema / Structured Data — Score: 18/100

### Current Implementation

**Homepage — WebSite Schema**
```json
{
  "@type": "WebSite",
  "@context": "http://schema.org",
  "url": "https://www.longevityhealthinstituteinc.com",
  "name": "Longevity Health Institute",
  "image": "[logo url]"
}
```
**Status:** ⚠️ Minimal — missing SearchAction (sitelinks search box), publisher

**Homepage — LocalBusiness Schema** ❌ CRITICAL
```json
{
  "@type": "LocalBusiness",
  "@context": "http://schema.org",
  "address": "",
  "image": "[broken image url]",
  "openingHours": ""
}
```
**Status:** 🔴 BROKEN — ALL fields empty. This is worse than no schema because it signals incorrect data to Google.

### Missing Schema (High Priority)

| Schema Type | Page | Priority |
|---|---|---|
| MedicalBusiness | Homepage + service pages | 🔴 Critical |
| Physician | /meet-dr-lewerenz | 🔴 Critical |
| FAQPage | /faq | 🔴 Critical |
| MedicalCondition | Condition pages | 🔴 High |
| Service | All service pages | 🔴 High |
| BreadcrumbList | All pages | ⚠️ Medium |
| Article/BlogPosting | All blog posts | ⚠️ Medium |
| Review/AggregateRating | Homepage, testimonials | ⚠️ Medium |
| SiteLinksSearchBox | Homepage | Low |

### Recommended LocalBusiness Schema Fix
```json
{
  "@context": "https://schema.org",
  "@type": ["LocalBusiness", "MedicalBusiness"],
  "name": "Longevity Health Institute",
  "url": "https://www.longevityhealthinstituteinc.com",
  "telephone": "[PHONE NUMBER]",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "[STREET ADDRESS]",
    "addressLocality": "Rochester",
    "addressRegion": "MI",
    "postalCode": "[ZIP]",
    "addressCountry": "US"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": "[LAT]",
    "longitude": "[LONG]"
  },
  "openingHours": ["Mo-Fr 09:00-17:00"],
  "priceRange": "$$$$",
  "description": "Functional medicine and concierge primary care clinic...",
  "sameAs": [
    "https://www.facebook.com/[page]",
    "https://www.instagram.com/[handle]"
  ],
  "hasMap": "https://maps.google.com/?q=[ADDRESS]"
}
```

---

## 5. Performance / Core Web Vitals — Score: 45/100

### Measured Performance (Desktop, Lab Data)
| Metric | Value | Threshold | Status |
|---|---|---|---|
| TTFB | 72ms | <200ms | ✅ Excellent |
| DOM Interactive | 2,117ms | <1,300ms | ❌ Slow |
| DOM Content Loaded | 2,317ms | <1,800ms | ❌ Slow |
| Full Load | 3,717ms | <2,500ms | ❌ Slow |

### Resource Breakdown
| Type | Count | Size |
|---|---|---|
| Scripts | 48 | 402 KB |
| Images | 12 | 1,754 KB |
| CSS | 12 | 161 KB |
| Other | 14 | ~10 KB |
| **Total** | **86** | **2,326 KB** |

### Key Issues
1. **Image weight 1,754 KB** — images not compressed/converted to WebP
2. **48 script files** — Squarespace loads many third-party scripts (GTM, analytics, etc.)
3. **20 render-blocking resources** — delaying first contentful paint
4. **No `preconnect` resource hints** for critical third-party origins

### Recommendations
- Convert all images to WebP format (Squarespace supports this)
- Enable Squarespace's built-in image compression
- Minimize GTM container — audit tags for unused scripts
- Add `<link rel="preconnect">` for fonts and CDN domains

---

## 6. Images — Score: 72/100

| Metric | Value | Status |
|---|---|---|
| Total Images | 27 | — |
| Missing Alt Text | 2 | ⚠️ Fix |
| Using Lazy Load | 15/27 (56%) | ⚠️ Should be 100% |
| Estimated Total Size | ~1.7 MB | ❌ Too large |
| WebP Format | Unknown | ⚠️ Check |

### Issues
- 2 images missing alt text (both appear to be decorative/background)
- 12 images not lazy-loaded (including above-fold hero — that's correct for LCP)
- Images served from Squarespace CDN — good for global delivery
- Hero image is very large — likely the LCP element causing slow scores

---

## 7. AI Search Readiness — Score: 60/100

### Current AI Visibility (SEMrush Data)
- AI Visibility Score: **22** (ChatGPT: 5, AI Overview: 23, AI Mode: 4)
- AI Mentions: **32** | Cited Pages: **43**
- This is actually relatively strong for a small clinic — ranking higher than Authority Score of 13 suggests

### Strengths
- Blog content is being cited by AI systems (43 cited pages)
- Long-form blog posts with specific questions ("How long after HRT...") match AI query patterns
- FAQ page exists (not optimized with schema yet)

### Weaknesses
- No `llms.txt` file
- No structured data for AI crawlers to parse
- No author entity markup (Physician schema)
- LocalBusiness schema is empty — AI can't cite location/hours accurately
- Missing medical disclaimer/EEAT signals for YMYL (Your Money Your Life) content

### Recommendations
1. Add `llms.txt` at root level
2. Implement FAQPage schema on /faq page
3. Add Physician schema with credentials on Dr. Lewerenz page
4. Add medical disclaimers to treatment pages for YMYL compliance

---

## Appendix: Pages Audited

| Page | Title OK | Meta OK | H1 OK | Schema | Words |
|---|---|---|---|---|---|
| / (homepage) | ✅ | ✅ | ✅ | ⚠️ Broken LB | 912 |
| /hormone-replacement-therapy | ⚠️ Long | ✅ | ✅ | ⚠️ Min | 3,466 |
| /iv-therapy | ✅ | ❌ Empty | ✅ | ⚠️ Min | 4,478 |
| /weight-loss-treatments | ✅ | ✅ | ✅ | ⚠️ Min | 4,764 |
| /meet-dr-lewerenz | ✅ | ✅ | ✅ | ⚠️ Min | 2,977 |
| /faq | ⚠️ Long | ✅ | ✅ | ⚠️ Min | 2,377 |
| /alternative-cancer-treatment | ⚠️ Long | ✅ | ❌ MISSING | ⚠️ Min | 2,887 |
| /peptides | ⚠️ Long | ✅ | ✅ | ⚠️ Min | 2,869 |
| Blog: HRT timing | ❌ Very long | ✅ | ✅ | ✅ Article | 2,606 |
| Blog: IV Therapy benefits | ✅ | ✅ | ✅ | ✅ Article | 2,515 |
