# Dream 100 Automation - Quick Start Guide

## ⚡ 5-Minute Setup

### Step 1: Verify API Keys

Check that your `.env` file has these keys:

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENAI_API_KEY=sk-xxxxx
```

**Don't have API keys?**
- OpenRouter: https://openrouter.ai/keys
- OpenAI: https://platform.openai.com/api-keys

**Cost:** ~$0.71 per complete run

---

### Step 2: Run Your First Automation

In Claude Code, simply say:

```
Run Dream 100 automation for https://example-clinic.com
```

Replace `example-clinic.com` with your target healthcare practice website.

---

### Step 3: Provide Required Info

You'll be asked for:

1. **Website URL** ✓ (already provided)
2. **Booking URL** (e.g., https://calendly.com/clinic/book)
   - OR phone number (e.g., +1-555-123-4567)
3. **Additional context** (optional)
   - e.g., "Functional medicine practice in Austin, TX"

---

### Step 4: Wait for SEO Pause

After ~3-5 minutes, you'll see:

```
═══════════════════════════════════════════════════════════
WORKFLOW PAUSED - Manual SEO Data Collection Required
═══════════════════════════════════════════════════════════

✓ 100 BrightLocal keywords generated
✓ SEMrush link opened in browser

NEXT STEPS:
1. Run BrightLocal audit (copy keywords from terminal)
2. Download BrightLocal PDF
3. Download SEMrush CSV (from opened tab)
4. Type: RESUME D100 [TIMESTAMP]
```

---

### Step 5: Complete SEO Data Collection

**BrightLocal** (5 minutes):
1. Go to: https://www.brightlocal.com/local-search-audit/
2. Paste the 100 keywords from terminal
3. Enter website URL
4. Run audit
5. Download PDF

**SEMrush** (2 minutes):
1. Browser tab auto-opened to SEMrush
2. Click "Export" → Download CSV
3. Keep the file

---

### Step 6: Resume & Complete

Back in Claude Code:

```
RESUME D100 20250210_123456
```

Then **attach both files:**
- BrightLocal PDF
- SEMrush CSV

---

### Step 7: Review Your Assets (1 minute)

Navigate to:
```
/output/d100_runs/[TIMESTAMP]/
```

You'll find:
- ✅ **Health Assessment App** - Ready to deploy HTML
- ✅ **Google Ads Campaigns** - 3 campaigns, import-ready
- ✅ **Email Sequence** - 3 emails, ESP-ready
- ✅ **SEO Intelligence** - Keywords + audit + insights
- ✅ **Structured Data** - Full JSON export

---

## 📦 What You Get

### 1. Health Assessment App
**File:** `app/health_assessment.html`
- Single-file HTML (no dependencies)
- Mobile-responsive, WCAG-compliant
- Brand-aligned (auto-extracted colors)
- Booking redirect built-in

**Deploy in 30 seconds:**
- Upload to your website, OR
- Host on Vercel (drag & drop), OR
- Embed in page builder

---

### 2. Google Ads Campaigns
**Files:** `ads/google_ads_campaign.md`, CSV imports

**3 Campaigns:**
1. **Medical Mystery Solver** - High intent, symptom-based
2. **Condition Remission** - Volume driver, condition-based
3. **Virtual Authority** - Trust builder, brand/location

**Includes:**
- 15 headlines (5 per campaign, ≤30 chars)
- 6 descriptions (2 per campaign, ≤90 chars)
- 4 sitelinks with descriptions
- 6 callouts
- 5 high-value keywords with buyer psychology

**Setup time:** 30 minutes (follow SETUP_GUIDE.md)

---

### 3. Email Nurture Sequence
**Files:** `emails/sequence.md`, HTML, ESP imports

**3 Emails:**
1. **Smart Practice Value Drop** (Send: Immediately)
   - Validates patient's symptoms
   - Shares high-value insight
   - Reframes their problem

2. **Mechanism Story** (Send: Day 2)
   - Explains the "why" behind symptoms
   - Shows root-cause understanding
   - Differentiates from standard care

3. **Proof & Results** (Send: Day 6)
   - Patient story (anonymized)
   - Transfer belief
   - Clear booking CTA

**Import formats:**
- Klaviyo CSV
- ConvertKit JSON
- Plain text (universal)
- HTML preview

**Setup time:** 15-30 minutes per ESP

---

### 4. SEO Intelligence Package
**Files:** `seo_data/` directory

**Includes:**
- **100 BrightLocal keywords** - Copy-ready for rank tracking
- **Local Audit Insights** - 3 critical revenue-blocking issues
- **SEMrush Analysis** - Organic performance, AI visibility, opportunities
- **Master Report** - Executive summary + action plan

---

### 5. Structured Practice Data (JSON)
**File:** `scrape_data/structured_data.json`

**Complete extraction:**
- Practice details (name, specialty, locations)
- All providers (bios, credentials, specialties)
- Services & treatments (verbatim from site)
- Conditions treated (categorized)
- Patient journey & intake process
- Pricing & insurance
- Trust signals (testimonials, awards, certifications)
- SEO intelligence

**Use for:**
- CRM import
- Sales enablement
- Future automations
- RAG/AI training

---

## 🚀 Real-World Use Cases

### Use Case 1: Dream 100 Outreach Campaign
**Scenario:** Agency targeting high-value functional medicine practices

**Workflow:**
1. Run automation for target practice
2. Get health app + ads + emails in 15 minutes
3. Send personalized Loom using SEO insights
4. Attach health app demo as "gift"
5. Follow up with Google Ads audit
6. Close with email sequence as bonus

**Assets created:** Everything needed for personalized pitch

---

### Use Case 2: Client Onboarding Accelerator
**Scenario:** New client signed, need assets fast

**Workflow:**
1. Run automation for client's site
2. Deploy health app (lead gen)
3. Import Google Ads campaigns (patient acquisition)
4. Set up email automation (nurture)
5. Use SEO report for strategy session

**Time saved:** 10-15 hours of manual work

---

### Use Case 3: Competitive Intelligence
**Scenario:** Analyzing competitor for sales pitch

**Workflow:**
1. Run automation for competitor
2. Review structured JSON for gaps
3. Use SEO insights to identify weaknesses
4. Create differentiation strategy
5. Build counter-positioning in pitch

**Assets created:** Deep competitive intelligence

---

## 🔧 Troubleshooting

### "Scrape failed - website blocked"
**Solution:** Use Grok DeepSearch fallback
1. Go to https://x.com/i/grok
2. Paste: "Deep search {website_url} for healthcare practice data"
3. Copy JSON response
4. Paste when prompted

---

### "Can't find API key"
**Solution:** Check .env file
```bash
cat /Users/neo/Documents/Claude\ Code/AIAA-Agentic-OS/.env
```
Should show:
```
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENAI_API_KEY=sk-xxxxx
```

---

### "Generated app has broken colors"
**Solution:** Manually provide brand colors
When prompted:
```json
{
  "primary": "#2563eb",
  "secondary": "#1e40af",
  "accent": "#3b82f6",
  "text": "#1f2937",
  "background": "#ffffff"
}
```

---

### "Email sequence too generic"
**Cause:** Limited context from website scrape
**Solution:** Add more context in initial input
```
Run Dream 100 automation for {url}

Additional context:
- Specialty: Functional medicine
- Focus: Chronic fatigue, gut health, hormone balance
- Ideal patient: Professional women 35-55
- Differentiator: Advanced lab testing + personalized protocols
```

---

## 📊 Success Metrics

Track these to measure automation value:

**Time Saved:**
- Manual research: 2-3 hours
- Asset creation: 8-10 hours
- **Total saved:** ~12 hours per run

**Asset Quality:**
- Health app: Production-ready (WCAG-compliant)
- Google Ads: Import-ready (character limits enforced)
- Emails: ESP-ready (multiple formats)
- SEO: Actionable insights (revenue-focused)

**Cost Efficiency:**
- API costs: ~$0.71 per run
- Manual alternative: $500-1000 (freelancer)
- **ROI:** 700-1400x

---

## 🎯 Pro Tips

### Tip 1: Batch Process Dream 100 List
Create a CSV with your target list:
```csv
website_url,booking_url,context
https://clinic1.com,https://cal.com/clinic1,Functional medicine NYC
https://clinic2.com,tel:+15551234567,Integrative health LA
```

Run automation for each in sequence.

---

### Tip 2: Customize Email Tone
Edit `SKILL_D100_email_builder.md` line 85:
```markdown
- Tone: calm, confident, intelligent, reassuring.
```
Change to: `authoritative`, `friendly`, `scientific`, etc.

---

### Tip 3: Add More Campaigns
Edit `SKILL_D100_ads_builder.md`:
Add Campaign 4: Retargeting
Add Campaign 5: Brand defense

---

### Tip 4: Create Presentation (Manual - Gamma Coming)
Use outputs to create pitch deck:
1. SEO insights → Slide 1-3 (Current state)
2. Health app screenshot → Slide 4 (Solution demo)
3. Google Ads copy → Slide 5 (Acquisition strategy)
4. Email sequence → Slide 6 (Nurture system)

---

## 📚 Next Steps

**Immediate (Today):**
1. ✅ Run your first automation
2. ✅ Deploy health assessment app
3. ✅ Review all outputs

**This Week:**
1. Import Google Ads campaigns (test with $50/day)
2. Set up email automation in ESP
3. Use SEO report for outreach

**This Month:**
1. Run automation for 10+ prospects
2. A/B test different email variants
3. Track conversion rates

---

## 🆘 Need Help?

**Documentation:**
- Full details: `/skills/SKILL_D100_README.md`
- Individual skills: `/skills/SKILL_D100_*.md`

**Errors:**
- Check: `/output/d100_runs/[TIMESTAMP]/error_log.txt`

**Re-run Skills:**
```
"Run SKILL_D100_scraper for {url}"
"Run SKILL_D100_app_builder with {json_path}"
```

---

## 🔄 Updates

**Version 1.0** (Current)
- 6 modular skills
- 5 output types
- ~15 min execution time
- $0.71 per run

**Coming in v1.1:**
- Gamma API integration (auto-presentation)
- BrightLocal API (remove manual step)
- SEMrush API (remove manual step)
- Multi-language support

---

**Ready to start?**

```
Run Dream 100 automation for [YOUR_TARGET_URL]
```

🚀 Let's go!
