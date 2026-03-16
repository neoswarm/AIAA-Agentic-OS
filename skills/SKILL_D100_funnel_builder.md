# SKILL: D100 Funnel Builder — Landing Page Builder
**Version:** 1.0
**Phase:** 2 (Claude Code native — zero API cost)
**Input:** `output/funnel_builds/{slug}_{ts}/prospect_data.json`
**Output:** `output/funnel_builds/{slug}_{ts}/index.html`

---

## TRIGGER

Run this skill when `prospect_data.json` exists in a funnel build run dir and `index.html` does NOT yet exist.

---

## YOUR ROLE

You are a **conversion-focused landing page architect** specializing in functional/integrative medicine practices. You build demo pages that look like they were custom-built for the doctor — professionally designed, brand-matched, high-converting.

This is a **DEMO BUILD** to impress the prospect (a busy doctor). Quality matters. Placeholders are fine. Never fabricate testimonials.

---

## EXECUTION STEPS

### Step 1 — Find pending builds
```bash
find output/funnel_builds/ -name "prospect_data.json" | while read f; do
  dir=$(dirname "$f")
  if [ ! -f "$dir/index.html" ]; then
    echo "PENDING: $dir"
  fi
done
```

### Step 2 — For each pending build:

1. Read `prospect_data.json`
2. Read this skill file (SKILL_D100_funnel_builder.md) for the full page spec
3. Build `index.html` using the DATA and SPEC below
4. Write to the run dir

---

## INPUT DATA (from prospect_data.json)

All values are extracted by the runner. Access them directly:

| Field | Description |
|-------|-------------|
| `name` | Doctor/practice name (e.g., "Dr. Aaron Hartman") |
| `website` | Their live website URL |
| `notes` | Optional intel about the prospect |
| `assessment_url` | URL of their D100 health assessment (may be empty) |
| `raw_scrape` | First 8000 chars of scraped site content |
| `brand_colors` | Dict: `{primary, accent, secondary, background}` hex values |
| `images` | Dict: `{logo_url, hero_url, headshot_url}` from their live CDN |
| `booking_url` | Their booking/scheduling link (may be empty) |
| `testimonials` | List of scraped testimonial strings (may be empty) |
| `public_presence` | Dict: `{instagram, linkedin, youtube, media_mentions[]}` |
| `crawl` | Dict: `{ai_status, sitemap_urls}` |

---

## LANDING PAGE SPECIFICATION

### Design Rules (NON-NEGOTIABLE)

- **Single self-contained HTML file** — inline CSS + JS only. No external libraries except Google Fonts CDN.
- **Apply scraped brand colors** — use `brand_colors.primary` as main accent throughout. If extraction failed, use `#2D5A8E` (professional medical blue) as fallback.
- **Hotlink all images** — `<img src="[images.logo_url]">` — never embed base64, never use stock images
- **Mobile-first, fully responsive** — works on phone, tablet, desktop
- **Subtle premium animations** — CSS transitions, fade-ins, scroll-based reveals via IntersectionObserver. No JS libraries.
- **Voice matching** — infer tone from `raw_scrape` (formal/academic vs warm/conversational). Match it exactly.
- **No purple gradients** unless their brand uses them
- **No "what we built for you" summary** — the page IS the demo

### Font Selection

From the scraped CSS/content, infer the font. Functional medicine sites commonly use:
- Body: Inter, Open Sans, or Lato (load from Google Fonts CDN)
- Headings: Playfair Display, Cormorant, or Montserrat for premium feel
- Default if unknown: `font-family: 'Inter', sans-serif` (body) + `font-family: 'Playfair Display', serif` (headings)

### CTA URL Logic

```
assessment_cta_url = assessment_url if assessment_url else "#assessment"
booking_cta_url = booking_url if booking_url else "#contact"
```

All primary CTAs → `assessment_cta_url`
Secondary CTAs (schedule, book call) → `booking_cta_url`

---

## PAGE SECTIONS (build in this order)

### 1. NAVBAR (sticky)
```
[ Logo img ]     [ Home ] [ About ] [ Services ]     [ CTA Button: "Take Free Assessment →" ]
```
- `<img>` tag using `images.logo_url` — if empty, use practice name as text logo
- Sticky top, backdrop-blur on scroll
- Mobile: hamburger menu (pure CSS or minimal JS)
- CTA button → `assessment_cta_url`
- Background: white with subtle shadow on scroll

---

### 2. HERO

**Goal:** Immediately establish relevance and drive to assessment CTA

**Layout:** Split — left: copy, right: headshot/hero image

**Elements:**
- **Tag line** (small caps, brand color): e.g., "Functional Medicine · Richmond, VA"
- **Headline** (H1, 50-60px): Pain-point focused. Write from `raw_scrape`. Example structure:
  `"[Specific Condition] Doesn't Have to Be Your Forever Story"`
  or `"Finally: [Their Method] That Actually Finds [Root Cause]"`
- **Subheadline** (20px, muted): Reinforce the promise. Pull their unique method from scrape.
- **Primary CTA button** (large, brand-color bg): "Take the Free Health Assessment →" → `assessment_cta_url`
- **Trust micro-copy** under CTA: e.g., "Free • Takes 5 minutes • See your personalized plan"
- **Secondary CTA** (text link): "Or book a discovery call →" → `booking_cta_url`
- **Image** (right): Use `images.headshot_url` or `images.hero_url`. If both empty, use a CSS gradient shape as placeholder. **Never use a stock photo URL.**
- **Social proof bar** below hero: "As seen on: [media logos if found in presence.media_mentions]" OR patient count/years in practice pulled from scrape

**Animation:** Fade-up on load (CSS keyframes, 0.6s ease-out)

---

### 3. CREDIBILITY BAR

Only include if `public_presence.media_mentions` has items OR scrape mentions specific media/podcast names.

**Layout:** Horizontal scrolling strip with grayscale logos + "As featured in" label
**If no media found:** Skip this section entirely (don't show empty bar)

---

### 4. PROBLEM-AGITATION

**Goal:** Make the reader feel deeply seen and understood

**Layout:** 2-column at desktop, stacked mobile

**Left side:**
- H2: "Does This Sound Familiar?"
- Bullet list of 5-7 pain points extracted verbatim from scrape (the conditions/symptoms they treat)
- Use their exact language — "brain fog" not "cognitive impairment"
- Each bullet: emoji + short phrase

**Right side:**
- Pull-quote or testimonial snippet (from `testimonials[0]` if available)
- If no testimonials: use a relevant scrape quote from the doctor themselves, in blockquote format
- Attribution: "[Patient Name]" or "— Anonymous Patient" if name unknown

**Animation:** Fade-in on scroll via IntersectionObserver

---

### 5. SOLUTION / MECHANISM

**Goal:** Introduce their unique approach/framework

**Layout:** Feature cards (3 columns desktop, stacked mobile)

**Header:**
- H2: "A Different Approach to [Their Specialty]"
- Subtext: 1-2 sentences from scrape describing their philosophy

**Cards (3):** Extract from `raw_scrape`:
1. **Their diagnostic/testing approach** (e.g., "Comprehensive Lab Panel" / "Root Cause Analysis")
2. **Their treatment philosophy** (e.g., "Personalized Protocols" / "Functional Nutrition")
3. **Their outcome/result promise** (e.g., "Lasting Resolution" / "Whole-Body Optimization")

Each card: icon (Unicode emoji or simple CSS shape) + title + 2-sentence description from scrape

---

### 6. SOCIAL PROOF

**CRITICAL RULE: Never fabricate testimonials. Use ONLY scraped testimonials or placeholders.**

**If `testimonials` array has items:**
- Show up to 3 testimonials in card format
- Display exactly as scraped — no editing, no embellishment
- Attribution: show scrape text as-is (may include patient name or be anonymous)

**If `testimonials` array is empty:**
- Show `[ADD TESTIMONIALS]` placeholder card × 3
- Style them identically to real cards (gray dashed border, same layout)
- Small italic note inside: "Real patient testimonial will go here"

**Layout:** 3-card grid with star ratings (★★★★★), quote, name/attribution
**Section header:** "What Our Patients Are Saying"

---

### 7. PATIENT ASSESSMENT CTA

**This is the PRIMARY lead-capture section — make it prominent.**

**Background:** Brand primary color (full-width section, white text)

**Elements:**
- **H2:** "Discover What's Really Going On With Your Health"
- **Subtext:** "Take our free 5-minute Health Assessment to identify the root patterns behind your symptoms — and see a personalized next-step plan."
- **Large CTA button** (white bg, brand-color text): "Take the Free Assessment →" → `assessment_cta_url`
- **If `assessment_url` is empty:** Show button that links to `#contact` + note: "Assessment link coming soon"
- **3 feature bullets** below button:
  - ✓ Free & confidential
  - ✓ Results in under 5 minutes
  - ✓ Personalized recommendations

**Design:** Full-width, ample padding, centered content. This section must be impossible to miss.

---

### 8. OFFER / PRICING

**Goal:** Reduce friction, give next step

**Layout:** 1-2 offer cards or a single "Book a Call" section

**Logic:**
- If scrape mentions specific programs/pricing → show those (use exact names from scrape)
- If no pricing found → show a single "Discovery Call" card:
  - Title: "Free Discovery Call"
  - Duration: "15-20 minutes"
  - What's included: pulled from scrape (what they offer in consultations)
  - CTA: "Book Your Call →" → `booking_cta_url`

**Note:** "Pricing" means what's available on their site. If they don't publish pricing, don't invent it.

---

### 9. AUTHORITY / ABOUT

**Goal:** Build trust with credentials and story

**Layout:** Left: large headshot photo, Right: bio content

**Elements:**
- **H2:** "Meet [Dr. Name / Practice Name]"
- **Photo:** `images.headshot_url` — if empty, use a styled placeholder circle
- **Bio:** Use verbatim from `raw_scrape` — their credentials, training, philosophy, personal story
- **Credentials bar:** Extract any degrees, certifications, board memberships from scrape
  (Format: badge-style chips: "MD · Functional Medicine Certified · IFM Member")
- **Social links** (if found in `public_presence`):
  - Instagram icon → `public_presence.instagram`
  - LinkedIn icon → `public_presence.linkedin`
  - YouTube icon → `public_presence.youtube`
  - All open in new tab

**Important:** Use what's in the scrape as-is. Demo build — no need to verify credentials.

---

### 10. FINAL CTA

**Goal:** Last chance conversion

**Background:** Dark (near-black or deep brand color)

**Elements:**
- **H2:** "Ready to Start Your Healing Journey?"
- **Subtext:** 1-2 sentences — reinforcing their promise
- **Primary CTA:** "Take the Free Assessment →" → `assessment_cta_url`
- **Secondary CTA:** "Schedule a Consultation →" → `booking_cta_url`
- **Trust line:** Their name + practice + brief tagline from scrape

---

### 11. FOOTER

- Logo (text or `images.logo_url`)
- Practice name + address (from scrape if found)
- Phone/email (from scrape if found)
- Links: Privacy Policy | Terms (placeholder hrefs)
- Copyright: `© [Year] [Practice Name]. All rights reserved.`
- Social icons (if `public_presence` has links)
- **Disclaimer** (required for medical sites):
  ```
  This website is for informational purposes only and does not constitute medical advice.
  Always consult a qualified healthcare provider before making health decisions.
  ```

---

## CSS ARCHITECTURE

```html
<style>
  /* ── CSS Custom Properties (auto-populated from brand_colors) ── */
  :root {
    --brand-primary: [brand_colors.primary or #2D5A8E];
    --brand-accent: [brand_colors.accent or #4A90D9];
    --brand-secondary: [brand_colors.secondary or #F0F4F8];
    --brand-bg: [brand_colors.background or #FFFFFF];
    --brand-dark: [darken primary by 15%];
    --text-primary: #1A1A2E;
    --text-secondary: #6B7280;
    --text-light: #9CA3AF;
    --radius-sm: 8px;
    --radius-md: 16px;
    --radius-lg: 24px;
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
    --shadow-md: 0 4px 20px rgba(0,0,0,0.08);
    --shadow-lg: 0 20px 60px rgba(0,0,0,0.12);
    --transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  /* ── Reset + Base ── */
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }
  body { font-family: 'Inter', sans-serif; color: var(--text-primary); background: var(--brand-bg); line-height: 1.6; }
  img { max-width: 100%; height: auto; }
  a { color: var(--brand-primary); text-decoration: none; }
  a:hover { text-decoration: underline; }

  /* ── Container ── */
  .container { max-width: 1200px; margin: 0 auto; padding: 0 24px; }

  /* ── Section spacing ── */
  section { padding: 80px 0; }
  @media (max-width: 768px) { section { padding: 48px 0; } }

  /* ── Buttons ── */
  .btn-primary {
    display: inline-block;
    background: var(--brand-primary);
    color: white;
    padding: 16px 32px;
    border-radius: var(--radius-sm);
    font-weight: 600;
    font-size: 1rem;
    letter-spacing: 0.02em;
    transition: var(--transition);
    border: none;
    cursor: pointer;
  }
  .btn-primary:hover {
    background: var(--brand-dark);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
    text-decoration: none;
  }
  .btn-secondary {
    display: inline-block;
    background: transparent;
    color: var(--brand-primary);
    padding: 14px 28px;
    border-radius: var(--radius-sm);
    font-weight: 600;
    border: 2px solid var(--brand-primary);
    transition: var(--transition);
    cursor: pointer;
  }
  .btn-secondary:hover {
    background: var(--brand-primary);
    color: white;
    text-decoration: none;
  }

  /* ── Animations ── */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(24px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .fade-up { animation: fadeUp 0.6s ease-out forwards; }
  .fade-up-delay-1 { animation-delay: 0.1s; opacity: 0; }
  .fade-up-delay-2 { animation-delay: 0.2s; opacity: 0; }
  .fade-up-delay-3 { animation-delay: 0.3s; opacity: 0; }

  /* Scroll-reveal (set by IntersectionObserver) */
  .reveal { opacity: 0; transform: translateY(20px); transition: opacity 0.6s ease, transform 0.6s ease; }
  .reveal.visible { opacity: 1; transform: translateY(0); }
</style>
```

**Inline JS for scroll reveal (add before `</body>`):**
```html
<script>
  // Scroll reveal
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); } });
  }, { threshold: 0.1 });
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

  // Navbar scroll effect
  const navbar = document.querySelector('.navbar');
  window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 50);
  });

  // Mobile menu (if hamburger implemented)
  const hamburger = document.querySelector('.hamburger');
  const navMenu = document.querySelector('.nav-menu');
  if (hamburger && navMenu) {
    hamburger.addEventListener('click', () => navMenu.classList.toggle('open'));
  }
</script>
```

---

## QUALITY CHECKLIST (verify before writing file)

- [ ] All brand colors applied from `brand_colors` dict (not hardcoded defaults)
- [ ] Logo and images hotlinked from their CDN (not embedded or stock)
- [ ] `assessment_url` used correctly in all primary CTAs (or `#assessment` placeholder if empty)
- [ ] `booking_url` used in secondary CTAs (or `#contact` if empty)
- [ ] Testimonials: ONLY scraped verbatim — no fabrications; `[ADD TESTIMONIALS]` if none
- [ ] Credentials/bio from scrape — no invented qualifications
- [ ] Mobile-responsive (flexbox/grid, media queries)
- [ ] No external JS libraries (only Google Fonts CDN allowed)
- [ ] Footer includes medical disclaimer
- [ ] File is fully self-contained (no broken relative imports)

---

## OUTPUT

Write the complete `index.html` to the run dir. File should be 30-80KB for a full page.

Then confirm:
```
✅ index.html written → output/funnel_builds/{run_dir}/index.html
   Size: XX KB
   Next: python3 -u scripts/d100_funnel_builder.py --csv prospects.csv --deploy-only
```
