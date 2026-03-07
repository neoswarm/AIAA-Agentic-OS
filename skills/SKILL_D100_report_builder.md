# SKILL_D100_report_builder — D100 Deliverables Page Builder

## Role
You are building a personalized deliverables page for a Dream 100 prospect. This is not a report — it contains their actual built assets: health assessment app, Google Ad campaigns, email sequences, SEO quick wins. All ready to use.

**Objective:** One self-contained `seo_report.html` file that impresses a busy doctor on mobile, hooks them in the first 10 seconds, and makes it trivially easy to book a call.

---

## Input Files (read both before building)

- `phase1_data.json` — SEMrush data, scrape, brand colors, crawl intel
- `phase2_output.json` — keywords, ads (3 campaigns), emails (3), app_config

All data comes from these two files. Never fabricate data — pull exact numbers from JSON.

---

## Output

Write `seo_report.html` to the run directory.

**Requirements:**
- Single self-contained HTML file (inline CSS + JS, no external JS libs)
- Google Fonts CDN link OK (Inter or DM Sans)
- Calendly embed script OK (their official CDN)
- Minimum file size: 80KB (content-rich, not padded)
- Mobile-first — test mentally at 375px width

---

## CONFIG Block (top of `<script>` section)

```javascript
// ─── PROSPECT CONFIG ───────────────────────────────────────────────────────
const CONFIG = {
  practice_name: "{phase1_data.context → extract practice name}",
  doctor_name: "{phase1_data.context → extract doctor name and credential}",
  website: "{phase1_data.website}",
  logo_url: "{phase1_data → brand logo URL if found in scrape, else ''}",
  loom_id: "PASTE_LOOM_ID_HERE",   // ← person sending the email swaps this
  booking_url: "{phase1_data.context → Booking URL}",
  brand_primary: "{phase1_data.brand_colors.primary}",
  brand_accent: "{phase1_data.brand_colors.secondary OR '#00D084' fallback}",
};

// Loom URL param override: ?loom=abc123 overrides CONFIG.loom_id
const urlParams = new URLSearchParams(window.location.search);
const LOOM_ID = urlParams.get('loom') || CONFIG.loom_id;
```

---

## Full Content Map — All 14 Sections + FAQ

### Section 1 — Hero [SEMI-DYNAMIC]

**Personalization banner** (top of page, dismisses on scroll past hero):
```
"This strategy was built exclusively for {practice_name} ↓"
```
Company-focused — multiple staff may view this, not targeting a specific person.

**Sticky navbar:** prospect logo (hotlinked, `{logo_url}`) + "📅 Book a Call" button (smooth-scrolls to `#section-cta`)

**Hero content:**
- H1: `Plug and play AI, SEO, and Ad Strategy for {practice_name} to get More Patients.`
- Loom iframe embed:
  ```html
  <div class="video-wrap">
    <iframe src="https://www.loom.com/embed/{LOOM_ID}?autoplay=0&hide_owner=true"
      frameborder="0" allowfullscreen allow="fullscreen"
      style="width:100%;aspect-ratio:16/9;border-radius:12px;"></iframe>
  </div>
  ```
  If `LOOM_ID === "PASTE_LOOM_ID_HERE"`, show a placeholder card instead of a broken iframe: `<div class="video-placeholder">🎬 Personalized video loading — share with ?loom=YOUR_ID</div>`

- Callout card (accent border): **"Don't Skip The Video Above — This is a personalized strategy built specifically for {practice_name}."**

- **"3 things we built for {practice_name}" strip** (3 cards inline):
  - ✅ Patient Health Assessment (live)
  - ✅ Google Ad Campaigns (ready to run — {N} campaigns built)
  - ✅ SEO Quick Wins Mapped ({quick_wins_count} opportunities identified)

  Pull N from `phase2_output.ads.length`. Pull quick_wins_count from `phase1_data.semrush.quick_wins_count`.

- **SEMrush stats strip** (4 large numbers):
  - Global Rank: `#{phase1_data.semrush.domain_rank.toLocaleString()}`
  - Keywords Ranked: `{phase1_data.semrush.unique_keywords.toLocaleString()}`
  - Monthly Traffic: `~{phase1_data.semrush.estimated_traffic.toLocaleString()} visits`
  - Traffic Value: `${phase1_data.semrush.traffic_value.toLocaleString()}/mo`

---

### Section 2 — What's Inside Your Package [SEMI-DYNAMIC]

Title: "Here's Everything We Built For {practice_name}"

7 deliverable cards (expandable `<details><summary>`):
1. 🔍 **SEO Digital Health Report** — your complete keyword footprint, competitor gap, and attack plan
2. 📣 **3 Google Ad Campaigns** — ready to launch, with headlines, descriptions, and keyword targets
3. 📧 **3-Email Patient Nurture Sequence** — sent to new leads after assessment completion
4. 🩺 **Custom Health Assessment App** — branded intake quiz that converts website visitors to leads
5. 🎯 **100 SEO Keywords** — curated for {practice_name}'s exact specialty and service mix
6. ⚡ **{quick_wins_count} SEO Quick Wins** — pages you can push from page 2 to page 1 this month
7. 🤖 **AI Search Gap Analysis** — {ai_overview_serp_count} keywords trigger AI Overviews; {practice_name} cited in 0 of them

Callout: "How We Want To Help {practice_name}" — 2-3 sentences explaining the Done-For-You approach and the goal of getting 10 new patients/month.

---

### Section 3 — Social Proof [STATIC]

Title: "What Doctors Like You Are Saying"

Dr. Diane Mueller testimonial — YouTube embed (privacy-enhanced):
```html
<iframe src="https://www.youtube-nocookie.com/embed/VIDEO_ID?rel=0"
  frameborder="0" allowfullscreen style="width:100%;aspect-ratio:16/9;border-radius:12px;"></iframe>
```
Use VIDEO_ID placeholder. Add text card fallback.

3 result bullets from Dr. Mueller:
- "Tripled patient inquiries within 90 days of launching her assessment"
- "Reduced time spent on marketing from 10+ hours/week to under 1 hour"
- "First functional medicine practice in her city to appear in AI search results"

Small line: "(SEE MORE TESTIMONIALS AT THE BOTTOM ↓)"

---

### Section 4 — Special Offer [SEMI-DYNAMIC]

Title: "We'll Set This Up For {practice_name} — For Free"

Callout card (large, accent background): **"FOR FREE"** — we build everything. You keep it forever.

5 expandable do-for-you steps:
1. 🩺 Build your branded health assessment app (custom to your conditions)
2. 📣 Create your Google Ad campaigns (campaign structure, headlines, keywords)
3. 📧 Write your patient email sequence (3 emails, ready to send)
4. 🔍 Map your SEO quick wins (specific pages to optimize first)
5. 📊 Deliver your full digital health report (so you know exactly where you stand)

**Calendly inline widget** (first embed):
```html
<div id="section-book"
     class="calendly-inline-widget"
     data-url="https://calendly.com/mike-kohl/30min?hide_gdpr_banner=1"
     style="min-width:320px;height:700px;"></div>
<script type="text/javascript" src="https://assets.calendly.com/assets/external/widget.js" async></script>
```

"Or just reply to our email — we'll get everything set up from there."

---

### Section 5 — SMART Practice System [STATIC]

Title: "The SMART Practice System That Fills Calendars"

4 pillar cards (icon + title + one-line desc):
- **S**tory — Patient assessment that captures intent and builds trust before the first call
- **M**atch — AI-powered content that shows up when patients search for your specialty
- **A**ds — High-intent Google campaigns that reach patients who are ready to book
- **R**etain — Automated email sequences that nurture leads into booked appointments
- **T**rack — Clear data on what's working so you scale what drives revenue

Patient funnel flow (visual step strip):
```
Awareness → Assessment → Email Nurture → Booked Call → New Patient
```

Each pillar as expandable card with 2-3 sentences of explanation.

---

### Section 6 — Assessment CTA [SEMI-DYNAMIC]

Title: "The Problem With 1,000 Website Visitors"

Body: Most practices get traffic but lose 95%+ of visitors because there's nothing to capture them. A custom health assessment converts browsers into booked consultations — because patients self-identify their concern, and the practice follows up with precision.

"We built {practice_name}'s assessment. Launch it now:"

**Button:** `[🩺 Launch Your Health Assessment →]` → opens `#assessment-overlay`

Note: The assessment is the full 6-step flow embedded in this same file. See Assessment section below.

---

### Section 7 — SEO Audit [FULLY DYNAMIC — phase1_data.json]

Title: "Digital SEO Health Report — {domain}"

Pull domain from `phase1_data.website` (strip `https://`).

**Stats grid** (6 large-number cards):
- Global Rank: `#{semrush.domain_rank}`
- Keywords Ranked: `{semrush.unique_keywords}`
- Monthly Traffic: `~{semrush.estimated_traffic}`
- Traffic Value: `${semrush.traffic_value}/mo`
- Keywords in Top 10: `{semrush.pos1_count + semrush.pos4_10_count}` (pos1 + pos4-10)
- AI Overview SERPs: `{semrush.ai_overview_serp_count}`

**Position breakdown** — pure CSS bar chart (no libraries):
- #1: `{semrush.pos1_count}` keywords
- #2-3: `{semrush.pos2_3_count}` keywords
- #4-10: `{semrush.pos4_10_count}` keywords (quick wins)
- #11-20: `{semrush.pos11_20_count}` keywords

**AI Search Gap callout** (if `ai_overview_serp_count > 0`):
> "{ai_overview_serp_count} searches trigger AI Overviews for keywords {practice_name} ranks for — but {practice_name} is cited in 0 of them. Every uncited AI Overview is a patient going to a competitor."

**Quick Wins table** (keyword / position / volume / KD):
Pull from `phase1_data.semrush.top_quick_wins` — up to 6 rows.
Table with horizontal scroll on mobile. Each row clickable (no-op, just hover highlight).

**Competitor comparison table:**
Pull from `phase1_data.semrush.competitors` — up to 3 rows.
Columns: Domain / Keywords Ranked / Traffic / Traffic Value

**3-Priority Attack Plan** — 3 expandable cards with timeline badge:
Generate from the actual data. Each card:
- Priority name (CAPS)
- Specific tactic based on the data
- Timeline: "Within 2 weeks" / "30 days" / "60 days"

Base the attack plan on real data patterns:
- If quick_wins > 0: Priority 1 = push those specific keywords
- If ai_overview_serp_count > 0: Priority 2 = AI Overview strategy
- If competitors show large traffic gap: Priority 3 = competitor keyword gap analysis

---

### Section 8 — Google Ads Campaigns [FULLY DYNAMIC — phase2_output.json]

Title: "Your Google Ad Campaigns — Ready to Launch"

Pull `phase2_output.ads` array (3 campaigns).

Each campaign = expandable `<details>` card (collapsed by default):

```
▶ Campaign 1: {campaign_name} [click to expand]
  ├─ Target: {target_audience}
  ├─ Headlines
  │   • Headline 1  [📋]   • Headline 2  [📋]   ...
  ├─ Descriptions
  │   • Desc 1  [📋]       • Desc 2  [📋]
  └─ Keywords
      [📋 Copy All Keywords]
      • [keyword1]   • [keyword2]   ...
```

Each headline/description/keyword has an individual [📋] copy button using `navigator.clipboard.writeText()`.

Ad Extensions as a collapsible sub-card:
Pull from `phase2_output.ad_callouts` — sitelinks and callout_extensions.

Each extension also has a [📋] button.

---

### Section 9 — Email Sequences [FULLY DYNAMIC — phase2_output.json]

Title: "Your Patient Email Sequence — 3 Emails, Ready to Send"

Pull `phase2_output.emails` array (3 emails).

Each email = expandable card (collapsed by default):
```
▶ Email 1: {subject} [click to expand]
  Preview: {preview}
  ──────────────────────────────
  {full body text — preserve line breaks, use <pre-wrap> or white-space:pre-line}
  ──────────────────────────────
  [📋 Copy Full Email]
```

Order: Email 1 (Value Drop) → Email 2 (Mechanism Story) → Email 3 (Proof & Results)

---

### Section 10 — The Complete System [STATIC]

Title: "From Symptom Search to Booked Appointment — Automated"

3-act narrative:
1. **Symptom Hook** — Patients search for their symptoms, not your clinic name. Your content needs to meet them where they are.
2. **Clinical Clarity** — The health assessment qualifies them, captures their contact, and tells them exactly what to expect from their first visit.
3. **Automated CTA** — The email sequence does the follow-up work while you focus on existing patients.

4-part system breakdown (nested expandable cards):
1. 🔍 Search Visibility — organic keywords + AI Overview citations
2. 🩺 Assessment Conversion — turning visitors into identified leads
3. 📣 Paid Ads — instant visibility for high-intent searches
4. 📧 Email Nurture — warming leads until they book

Founder story (static):
> "We built this system because functional medicine practices consistently have the best outcomes but the worst online visibility. Your patients are searching — they just can't find you. We fix that."
> — Mike Kohl, AIAA

---

### Section 11 — More Client Reviews [STATIC]

Title: "More Practices, More Results"

3 testimonial cards:

**Dr. Piper Gibson** — The Hormone Dietitian
- "First Google page for 3 competitive terms within 60 days"
- "Assessment converted 40% of new visitors to booked consultations"
- "Team handles zero marketing — fully automated"

**Dr. Alison Egeland** — Functional Medicine Practice
- "12 new patients in the first month after launch"
- "Email sequence runs itself — zero effort after setup"
- "Finally visible to patients searching for root-cause medicine in my city"

**Dan Lievens** — Practice Administrator
- "Took less than a week to get everything running"
- "The ads were live and getting clicks before we even sent the first email"
- "Most clear ROI we've ever gotten from a marketing investment"

Each card expandable with result bullets.

---

### Section 12 — Done-For-You Service Details [STATIC]

Title: "Everything That's Included — Done For You"

5 grouped feature cards (each expandable):

**🩺 Health Assessment**
- Custom-branded 6-step patient quiz
- Conditions and symptoms matched to your specialty
- Lead capture with email integration
- Mobile-optimized, instant results page

**🔍 SEO & Content**
- Keyword research specific to your services and city
- Quick-win optimization plan (pages to update this month)
- AI search visibility roadmap
- Schema markup recommendations

**📣 Google Ads**
- 3 campaigns covering your top service categories
- 100 target keywords, segmented by intent
- All headlines, descriptions, and extensions written
- Ready to upload directly to Google Ads

**🔄 Conversion & Lead Nurture**
- 3-email patient sequence (value, mechanism, proof)
- Personalization tokens pre-mapped
- Compliant disclaimers included
- Ready for any email platform (Klaviyo, Mailchimp, ActiveCampaign)

**⚡ Speed-to-Lead**
- Everything built in 5-7 business days
- One hand-off call — we walk you through everything
- You own all assets forever
- We optimize the first 30 days at no additional cost

---

### Section 13 — Client Apps Built [STATIC]

Title: "Examples of Health Assessments We've Built"

4 example cards (can use placeholder screenshots or descriptive cards):
1. **Functional Medicine Centre** — 12-concern, 72-symptom assessment
2. **IV Lounge & Wellness** — 8-concern infusion and recovery quiz
3. **Integrative Women's Health** — hormone and fertility specialty flow
4. **Men's Health Clinic** — testosterone, performance, and vitality assessment

Each card: practice type + concern count + link placeholder (or screenshot image)

---

### Section 14 — Final CTA [SEMI-DYNAMIC]

Title: "10 New Patients — Or You Don't Pay"

Guarantee card:
> "We guarantee 10 new patient inquiries in the first 30 days — or we continue working for free until you get there. No contracts. No risk."

**Calendly inline widget** (second embed, same URL as Section 4):
```html
<div id="section-cta"
     class="calendly-inline-widget"
     data-url="https://calendly.com/mike-kohl/30min?hide_gdpr_banner=1"
     style="min-width:320px;height:700px;"></div>
```
(Calendly script only needs to load once — one `<script>` tag is enough for both embeds)

"Or just respond to our email — we'll set up a time from there."

---

### FAQ Section [STATIC]

Title: "Frequently Asked Questions"

8 Q&As using `<details><summary>` (zero-JS toggle):

1. **Is this done-for-you?** Yes. We build everything — assessment, ads, emails, SEO audit. You review and approve. We set it up.
2. **How much work is required from me?** One 30-minute call to review. Then you approve and we go live. Ongoing: zero.
3. **How much does this cost?** The strategy package shown here is provided free as a demonstration. Our done-for-you implementation packages start at $X/month. Book a call to discuss.
4. **How long does setup take?** 5-7 business days from first call to everything live.
5. **Do I need a Google Ads account?** Yes — you'll need an existing Google Ads account. We handle all campaign setup and management.
6. **What if I already have a website?** We work with any existing website. The assessment embeds on your site with one line of code.
7. **How is this different from other marketing agencies?** We specialize in functional medicine practices only. Everything here — assessment questions, ad copy, email sequence — was built for your specific type of practice.
8. **What happens after the 30-minute call?** We confirm the strategy, get your brand approvals, and have everything live within a week.

---

## Assessment Modal (Embedded Inline)

The full 6-step health assessment runs inside this HTML file as a fixed-position modal overlay.

**Structure:**
```
Step 1: Primary Health Concern (12 card options from phase2_output.app_config.concerns)
Step 2: Symptom Duration & Impact (2×2 card grid)
Step 3: Specific Symptoms (chip multi-select, dynamically populated from concern)
Step 4: Health Goals (chip multi-select, 8 options)
Step 5: Contact Info (name + email + phone)
Step 6: Results (personalized summary + booking CTA)
```

**Symptom map** — build from `phase2_output.app_config.concerns` + `phase2_output.app_config.symptoms`. Each concern maps to 8-12 relevant symptoms from the practice's specialty.

**Card-select pattern** (no radio buttons — cards are full-width `<button>` elements):
```html
<button class="card-opt" data-val="energy" onclick="pickCard(this,'g-concern')">
  <span class="co-icon">⚡</span>
  <span class="co-text">Energy & Fatigue</span>
  <span class="co-check">✓</span>
</button>
```

**localStorage caching:**
```javascript
// Save answers between sessions
function saveProgress() {
  localStorage.setItem('assessment_' + CONFIG.practice_name, JSON.stringify(answers));
}
function loadProgress() {
  const saved = localStorage.getItem('assessment_' + CONFIG.practice_name);
  if (saved) { Object.assign(answers, JSON.parse(saved)); }
}
```

**Results page** shows:
- Practice name + "Here's your personalized health plan"
- Concern label + matched symptoms summary
- 3-step next action card
- [Book Your Consultation] button → `CONFIG.booking_url`
- [Book a Free Strategy Call] button → `https://calendly.com/mike-kohl/30min`

---

## Design System

**Fonts:** Google Fonts — `Inter` (weights 400, 500, 600, 700, 800)

**Colors:**
```css
--bg-deep:    #0a0e1a;   /* section backgrounds */
--bg-alt:     #0f1420;   /* alternating sections */
--bg-card:    #141824;   /* card backgrounds */
--bg-card2:   #1a2030;   /* nested card backgrounds */
--text-white: #f0f4ff;   /* primary text */
--text-muted: #8896b0;   /* secondary text */
--accent:     var(--brand-accent);  /* from CONFIG */
--border:     rgba(255,255,255,0.08);
```

**Typography:**
```css
html { font-size: 18px; }
body { font-family: 'Inter', sans-serif; line-height: 1.75; }
h1   { font-size: clamp(32px, 6vw, 56px); font-weight: 800; }
h2   { font-size: clamp(28px, 4vw, 40px); font-weight: 700; }
h3   { font-size: clamp(20px, 3vw, 28px); font-weight: 600; }
p    { font-size: clamp(17px, 2vw, 19px); }
```

**Layout:**
```css
.section { padding: clamp(60px, 8vw, 120px) 24px; }
.content-wrap { max-width: 780px; margin: 0 auto; }
```

**Cards:**
```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
}
.card-accent { border-left: 3px solid var(--accent); }
```

**Stats grid:**
```css
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
}
.stat-card { text-align: center; }
.stat-num  { font-size: clamp(28px, 5vw, 48px); font-weight: 800; color: var(--accent); }
.stat-label { font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }
```

**Tables (mobile-safe):**
```css
.table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
table { width: 100%; min-width: 480px; border-collapse: collapse; }
th, td { padding: 12px 16px; border-bottom: 1px solid var(--border); text-align: left; }
th { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); }
```

**Expandable cards (`<details>`):**
```css
details summary {
  cursor: pointer;
  list-style: none;
  padding: 20px 24px;
  font-weight: 600;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
details summary::after { content: '＋'; color: var(--accent); font-size: 20px; }
details[open] summary::after { content: '－'; }
details .details-body { padding: 0 24px 24px; }
```

**Copy buttons:**
```css
.copy-btn {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-muted);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 13px;
  cursor: pointer;
}
.copy-btn:hover { border-color: var(--accent); color: var(--accent); }
.copy-btn.copied { border-color: #22c55e; color: #22c55e; }
```

---

## UX Features

**Scroll progress bar:**
```css
#progress-bar {
  position: fixed; top: 0; left: 0; height: 3px;
  background: var(--accent); z-index: 9999;
  width: 0%;
  animation: none; /* updated by JS */
}
```
```javascript
window.addEventListener('scroll', () => {
  const pct = window.scrollY / (document.body.scrollHeight - window.innerHeight) * 100;
  document.getElementById('progress-bar').style.width = pct + '%';
});
```

**Section jump nav** (floating pill, right side desktop / bottom drawer mobile):
```html
<nav id="jump-nav">
  <a href="#section-video">🎬 Video</a>
  <a href="#section-seo">📊 SEO</a>
  <a href="#section-ads">📣 Ads</a>
  <a href="#section-emails">📧 Emails</a>
  <a href="#section-assessment">🩺 Assessment</a>
  <a href="#section-cta">📅 Book</a>
</nav>
```

**Sticky floating book-a-call button (mobile, bottom-right):**
```html
<a href="#section-cta" id="sticky-cta">📅 Book a Call</a>
```
```css
#sticky-cta {
  position: fixed; bottom: 24px; right: 24px; z-index: 9000;
  background: var(--accent); color: #000; font-weight: 700;
  border-radius: 50px; padding: 14px 24px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}
@media (min-width: 768px) { #sticky-cta { display: none; } }
```

**Personalization banner** (dismisses on scroll past hero):
```javascript
window.addEventListener('scroll', () => {
  const hero = document.getElementById('section-hero');
  const banner = document.getElementById('pers-banner');
  if (hero && banner) {
    banner.style.display = window.scrollY > hero.offsetHeight ? 'none' : 'flex';
  }
});
```

---

## Copy Button JS

```javascript
function copyText(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = '✓ Copied';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = orig; btn.classList.remove('copied'); }, 2000);
  }).catch(() => {
    // Fallback for older browsers
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  });
}
```

---

## Output Validation

Before writing `seo_report.html`, verify:
- [ ] File size > 80KB
- [ ] All 14 sections + FAQ present
- [ ] Assessment modal included with 6 steps
- [ ] Loom embed OR placeholder present
- [ ] Both Calendly embeds present (sections 4 and 14)
- [ ] CONFIG block at top with all real values
- [ ] LOOM_ID URL param support (`?loom=`) working
- [ ] All SEMrush numbers from `phase1_data.semrush` (not fabricated)
- [ ] Ads from `phase2_output.ads` (not example data)
- [ ] Emails from `phase2_output.emails` (not example data)
- [ ] All copy [📋] buttons functional
- [ ] Mobile-readable at 375px (max-width 780px, 18px+ base font)

---

## Execution Steps

1. Read `phase1_data.json` → extract semrush, brand_colors, website, crawl, context
2. Read `phase2_output.json` → extract ads, emails, keywords, app_config
3. Parse practice name and doctor name from `phase1_data.context`
4. Extract domain from `phase1_data.website`
5. Build CONFIG block from extracted values
6. Build all 14 sections in order, injecting dynamic data
7. Build assessment modal using `app_config.concerns` and `app_config.symptoms`
8. Write complete HTML to `seo_report.html`
9. Confirm file exists and size > 80KB
