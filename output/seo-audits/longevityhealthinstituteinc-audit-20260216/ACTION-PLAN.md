# SEO Action Plan
## Longevity Health Institute
**Priority Order:** Critical → High → Medium → Low
**Overall Score: 52/100 → Target: 72/100 in 90 days**

---

## 🔴 CRITICAL — Fix Immediately (This Week)

### 1. Fix Broken LocalBusiness Schema
**Impact:** High | **Effort:** 30 min | **Score Impact:** +8 pts

The LocalBusiness schema exists but ALL fields are empty. Google sees this as incorrect structured data and ignores it (or may penalize for misleading schema).

**Action:** In Squarespace → Pages → Not Linked → Add Code Block OR use SEO settings to inject:
```json
{
  "@context": "https://schema.org",
  "@type": ["LocalBusiness", "MedicalBusiness"],
  "name": "Longevity Health Institute",
  "url": "https://www.longevityhealthinstituteinc.com",
  "telephone": "YOUR-PHONE-NUMBER",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "YOUR STREET ADDRESS",
    "addressLocality": "Rochester Hills",
    "addressRegion": "MI",
    "postalCode": "YOUR-ZIP",
    "addressCountry": "US"
  },
  "geo": { "@type": "GeoCoordinates", "latitude": YOUR_LAT, "longitude": YOUR_LONG },
  "openingHours": ["Mo-Fr 09:00-17:00"],
  "priceRange": "$$$$",
  "image": "YOUR-LOGO-URL",
  "description": "Functional medicine and concierge primary care clinic specializing in hormone balance, IV therapy, weight loss, anti-aging, and root-cause medicine.",
  "sameAs": ["YOUR-FACEBOOK-URL", "YOUR-INSTAGRAM-URL", "YOUR-LINKEDIN-URL"]
}
```

---

### 2. Add H1 to /alternative-cancer-treatment
**Impact:** Medium | **Effort:** 5 min | **Score Impact:** +2 pts

This service page has NO H1 tag. Google can't determine the page's primary topic.

**Action:** In Squarespace page editor, add an H1 heading: "Alternative Cancer Treatment" or "Integrative Alternative Cancer Treatment in [City], MI"

---

### 3. Fix /iv-therapy Meta Description
**Impact:** Medium | **Effort:** 5 min | **Score Impact:** +1 pt

The meta description reads "Let" — it's truncated/broken. Google will auto-generate a snippet instead.

**Action:** In Squarespace SEO settings for that page, write a complete meta description:
> "Recharge your health with customized IV therapy at Longevity Health Institute. Get vitamins, minerals, and nutrients delivered directly into your bloodstream for fast results. Serving [City], MI."

---

## 🟠 HIGH — Fix Within 1 Week

### 4. Shorten Over-Length Title Tags
**Impact:** Medium | **Effort:** 20 min | **Score Impact:** +3 pts

5 pages have titles that get cut off in Google search results.

| Page | Current (chars) | Suggested Fix |
|---|---|---|
| HRT blog | 87c | "How Long Until HRT Works? What to Expect — LHI" |
| Peptide Therapy | 78c | "Peptide Therapy for Wellness & Recovery — LHI" |
| Alternative Cancer | 63c | "Alternative Cancer Treatment — Longevity Health" |
| HRT service | 62c | "Hormone Replacement Therapy — Longevity Health" |
| FAQ | 61c | "FAQs — Longevity Health Institute" |

---

### 5. Add FAQPage Schema to /faq
**Impact:** High | **Effort:** 45 min | **Score Impact:** +5 pts

FAQ schema enables rich result snippets in Google (accordion FAQs shown in search). With AI Visibility of 22, this also feeds ChatGPT/AI Overview directly.

**Action:** Extract all Q&A pairs from /faq page and add:
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is functional medicine?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Functional medicine treats the root causes of illness rather than just symptoms..."
      }
    }
    // ... all FAQ items
  ]
}
```

---

### 6. Add Physician Schema to /meet-dr-lewerenz
**Impact:** High | **Effort:** 20 min | **Score Impact:** +4 pts

Dr. Lewerenz has no structured data. For a YMYL (medical) site, physician schema is critical for E-E-A-T and AI citability.

```json
{
  "@context": "https://schema.org",
  "@type": "Physician",
  "name": "Dr. James Lewerenz",
  "url": "https://www.longevityhealthinstituteinc.com/meet-dr-lewerenz",
  "medicalSpecialty": ["FamilyMedicine", "FunctionalMedicine"],
  "worksFor": { "@type": "MedicalBusiness", "name": "Longevity Health Institute" },
  "description": "Board-certified physician specializing in functional and concierge medicine..."
}
```

---

### 7. Create Google Business Profile & Optimize
**Impact:** Very High | **Effort:** 1-2 hours | **Score Impact:** +6 pts (local pack visibility)

The -31% traffic decline is largely a local SEO problem. A fully optimized GBP is the #1 lever for local healthcare clinics.

**Actions:**
- Claim/verify Google Business Profile at your physical address
- Add all services as GBP services
- Upload 10+ photos (clinic interior, staff, treatments)
- Set exact hours
- Enable appointment booking link
- Post weekly GBP updates

---

### 8. Add Service Schema to All Service Pages
**Impact:** High | **Effort:** 2 hours | **Score Impact:** +4 pts

None of the 9 service pages have Service schema. This is a major missed opportunity for rich results.

**Pages to update:** HRT, IV Therapy, Weight Loss, Peptide Therapy, Alternative Cancer, Functional Medicine, Gut Health, Anti-Aging, Concierge Medicine

---

## 🟡 MEDIUM — Fix Within 1 Month

### 9. Create Location-Specific Landing Pages
**Impact:** Very High | **Effort:** 4-6 hours | **Score Impact:** +7 pts (local traffic)

Blog posts already reference "Rochester MI" and "Bingham Farms" but there are no dedicated location pages. These are high-conversion, low-competition keywords.

**Create pages for:**
- `/functional-medicine-rochester-mi`
- `/functional-medicine-bingham-farms-mi`
- `/hormone-therapy-rochester-hills-mi`
- `/iv-therapy-rochester-mi`

Each page should: 600+ words, include LocalBusiness schema with that location, embed Google Map, list services available at that location.

---

### 10. Add BlogPosting Schema to All Blog Posts
**Impact:** Medium | **Effort:** 1 hour (template) | **Score Impact:** +2 pts

Blog posts currently only have minimal schema. Add Article/BlogPosting with author, datePublished, dateModified.

---

### 11. Fix Heading Hierarchy — Remove ALL CAPS H2s
**Impact:** Medium (UX + semantic clarity) | **Effort:** 1 hour

All H2 tags on homepage are in ALL CAPS ("OUR SERVICES", "FUNCTIONAL MEDICINE", etc.). This should be a CSS styling choice, not actual uppercase text in the heading. Screen readers and Google parse it as emphasis, which is semantically incorrect.

**Fix:** In Squarespace, use normal case text in headings and apply `text-transform: uppercase` via CSS if the design requires it.

---

### 12. Optimize Images for Performance
**Impact:** High (Core Web Vitals) | **Effort:** 2 hours

Total image weight is 1,754 KB — the biggest performance bottleneck.

**Actions:**
- In Squarespace Image Editor: reduce quality to 80%, check "Serve in WebP where supported"
- Hero image: resize to max 1200px wide
- All images: ensure lazy loading except hero/LCP image
- Target: reduce image weight to under 500 KB

---

### 13. Add Medical Disclaimers to Treatment Pages
**Impact:** Medium (E-E-A-T / YMYL) | **Effort:** 30 min

YMYL (Your Money or Your Life) medical pages require disclaimer text for Google's quality raters.

**Add to all treatment pages:** "The information on this page is for educational purposes only and does not constitute medical advice. Always consult with a qualified healthcare provider."

---

### 14. Fix Sitemap lastmod Dates
**Impact:** Low-Medium | **Effort:** Automatic after Squarespace content edit

All sitemap `lastmod` values show 2025-09-11 — stale. Squarespace auto-updates these when you save pages.

**Fix:** Open each key page in Squarespace editor and re-save to trigger sitemap refresh.

---

## 🟢 LOW — Backlog (Nice to Have)

### 15. Add llms.txt File
Help AI crawlers understand your site structure:
```
# Longevity Health Institute
> Functional medicine and concierge primary care clinic

/meet-dr-lewerenz — Physician profile and credentials
/faq — Frequently asked questions about functional medicine
/hormone-replacement-therapy — HRT services
/iv-therapy — IV therapy services
```

### 16. Add SiteLinksSearchBox Schema
Enables search box in Google branded results.

### 17. Add BreadcrumbList to All Pages
Improves SERP display and internal link signals.

### 18. Add AggregateRating Schema to Homepage
Pull from Google/verified review source to show star ratings in SERPs.

### 19. Audit & Clean GTM Container
48 scripts are loading — some are likely unused tracking pixels. Audit GTM and remove unused tags to improve load time.

### 20. Add preconnect Resource Hints
```html
<link rel="preconnect" href="https://images.squarespace-cdn.com">
<link rel="preconnect" href="https://fonts.googleapis.com">
```

---

## 90-Day Score Projection

| Timeline | Actions | Expected Score |
|---|---|---|
| Week 1 | Items 1-3 (Critical fixes) | 55/100 |
| Week 2-3 | Items 4-8 (Schema + GBP) | 62/100 |
| Month 2 | Items 9-13 (Location pages + performance) | 68/100 |
| Month 3 | Items 14-20 (Polish) | 72+/100 |

**Traffic recovery estimate:** +40-60% organic traffic within 90 days if location pages + GBP + schema fixes are all implemented.

---

## Top Priority for Stopping the -31% Traffic Decline

The traffic decline is primarily from:
1. **No local SEO signals** — no GBP optimization, no location pages
2. **Competing sites have stronger schema** — Google prefers structured data for local medical searches
3. **Blog content not linked to service pages** — authority isn't flowing from high-ranking blog posts to conversion pages

Fix items 1, 7, and 9 first. That combination will have the most impact on reversing the decline.
