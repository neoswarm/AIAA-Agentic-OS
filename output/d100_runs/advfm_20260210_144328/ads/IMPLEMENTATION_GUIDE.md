# Google Ads Implementation Guide
## Advanced Functional Medicine - Quick Start

**Created:** February 10, 2026
**Estimated Setup Time:** 4-6 hours
**Recommended Launch Budget:** $3,000-5,000/month

---

## FILE MANIFEST

Your Google Ads campaigns include these files:

1. **google_ads_campaign.md** - Complete campaign strategy, copy, and optimization guide
2. **campaign1_medical_mystery_solver.csv** - 30 keywords for Campaign 1
3. **campaign2_condition_remission.csv** - 30 keywords for Campaign 2
4. **campaign3_virtual_authority.csv** - 29 keywords for Campaign 3
5. **negative_keywords.csv** - 40 negative keywords for all campaigns
6. **ad_copy_import.csv** - All ad copy for import
7. **sitelinks_import.csv** - 12 sitelinks with descriptions
8. **callouts_import.csv** - 18 callouts across all campaigns
9. **IMPLEMENTATION_GUIDE.md** - This file

---

## PRE-LAUNCH CHECKLIST

### Technical Setup (Do This First)
- [ ] Google Ads account created/accessed
- [ ] Google Analytics 4 installed on website
- [ ] Google Tag Manager installed
- [ ] Conversion tracking configured:
  - [ ] Form submissions
  - [ ] Phone calls (Google forwarding number)
  - [ ] Discovery call bookings
  - [ ] Chat initiations
- [ ] Google Ads and Analytics linked
- [ ] Billing information added to Google Ads

### Landing Page Readiness
- [ ] Diabetes reversal page exists and optimized
- [ ] Hormone therapy page exists and optimized
- [ ] Thyroid treatment page exists and optimized
- [ ] Autoimmune page exists and optimized
- [ ] General homepage optimized
- [ ] Telehealth/virtual care page exists
- [ ] All pages load in <3 seconds (test with PageSpeed Insights)
- [ ] All pages are mobile-responsive
- [ ] Phone numbers are click-to-call on mobile
- [ ] Forms are working and submitting correctly
- [ ] Free discovery call booking system is functional

### Legal & Compliance
- [ ] Medical advertising disclaimers added to landing pages
- [ ] "Results may vary" disclaimer present
- [ ] HIPAA compliance verified for testimonials
- [ ] Cash-pay policy clearly stated
- [ ] Virtual care licensure limitations noted if applicable

---

## IMPORT INSTRUCTIONS

### Step 1: Import Campaigns & Keywords

1. Open **Google Ads Editor** (download from ads.google.com/editor)
2. Select your account
3. Click **Import** > **From file**
4. Import in this order:
   - campaign1_medical_mystery_solver.csv
   - campaign2_condition_remission.csv
   - campaign3_virtual_authority.csv
5. Map columns:
   - Campaign → Campaign
   - Ad Group → Ad group
   - Keyword → Keyword
   - Match Type → Match type
   - Max CPC → Max CPC bid

### Step 2: Import Negative Keywords

1. In Google Ads Editor, click **Import** > **From file**
2. Select **negative_keywords.csv**
3. Map columns:
   - Campaign → Campaign (or Account for account-level negatives)
   - Negative Keyword → Keyword
   - Match Type → Match type

### Step 3: Import Ad Copy

1. In Google Ads Editor, click **Import** > **From file**
2. Select **ad_copy_import.csv**
3. Map columns:
   - Campaign → Campaign
   - Ad Group → Ad group
   - Headline 1-5 → Headlines
   - Description 1-2 → Descriptions
   - Final URL → Final URL

### Step 4: Import Sitelinks

1. In Google Ads Editor, navigate to **Shared library** > **Sitelinks**
2. Click **Import** > **From file**
3. Select **sitelinks_import.csv**
4. Map columns appropriately
5. After import, assign sitelinks to campaigns

### Step 5: Import Callouts

1. In Google Ads Editor, navigate to **Shared library** > **Callouts**
2. Click **Import** > **From file**
3. Select **callouts_import.csv**
4. Map columns appropriately
5. After import, assign callouts to campaigns

---

## CAMPAIGN SETTINGS CONFIGURATION

### Campaign 1: Medical Mystery Solver
- **Campaign Type:** Search
- **Networks:** Google Search only (uncheck Search Partners initially)
- **Locations:**
  - Primary: San Diego County, Orange County, Los Angeles County
  - Secondary: California
  - Tertiary: United States
- **Location Options:** People in or regularly in your targeted locations
- **Languages:** English
- **Budget:** $1,600/month ($40/day minimum, adjust based on total budget)
- **Bidding:** Maximize Conversions with Target CPA of $200
- **Ad Rotation:** Optimize (prefer best performing ads)
- **Start Date:** Set to launch date
- **End Date:** None

### Campaign 2: Condition Remission
- **Campaign Type:** Search
- **Networks:** Google Search only
- **Locations:** Same as Campaign 1
- **Languages:** English
- **Budget:** $1,400/month ($35/day minimum)
- **Bidding:** Maximize Conversions with Target CPA of $200
- **Ad Rotation:** Optimize
- **Start Date:** Set to launch date
- **End Date:** None

### Campaign 3: Virtual Authority
- **Campaign Type:** Search
- **Networks:** Google Search only
- **Locations:**
  - Primary: United States
  - Bid Adjustment: +50% for California
- **Languages:** English
- **Budget:** $1,000/month ($25/day minimum)
- **Bidding:** Maximize Conversions with Target CPA of $200
- **Ad Rotation:** Optimize
- **Start Date:** Set to launch date
- **End Date:** None

---

## AD EXTENSIONS SETUP

### Structured Snippets (Manual Setup Required)
Add these manually in Google Ads Editor:

**Type:** Services
**Values:**
- Diabetes Reversal
- Hormone Therapy
- Thyroid Care
- Autoimmune Treatment
- Gut Health
- Chronic Fatigue

**Type:** Locations
**Values:**
- San Diego
- Orange County
- Los Angeles
- Virtual Nationwide

### Price Extensions (Manual Setup Required)
Add these manually in Google Ads interface:

**Header:** Services
- **Diabetes Reversal - Initial Visit:** $295 | Per visit
- **Follow-Up Visits:** $199 | Per visit
- **Free Discovery Call:** Free | Per call

### Location Extensions
Link your Google Business Profile to automatically show:
- Address
- Phone number
- Business hours
- Directions link

### Call Extensions
Add practice phone number:
- Enable call reporting
- Set call reporting to count calls over 60 seconds
- Show number: All devices
- Add conversion tracking

---

## AD SCHEDULE SETUP

Set these bid adjustments by day/time:

**Monday-Friday:**
- 8 AM - 12 PM: +20% (peak research hours)
- 12 PM - 2 PM: 0% (lunch, lower intent)
- 2 PM - 6 PM: +10% (afternoon research)
- 6 PM - 8 PM: 0% (evening)
- 8 PM - 8 AM: -30% (overnight, lower quality)

**Saturday-Sunday:**
- All day: -10% (lower search volume)
- Overnight (8 PM - 8 AM): -50%

---

## DEVICE BID ADJUSTMENTS

Initial settings (adjust after 2 weeks of data):
- **Mobile:** 0% (baseline)
- **Desktop:** +10% (typically higher conversion rate)
- **Tablet:** -10% (lower volume)

---

## AUDIENCE TARGETING (Observation Mode)

Add these audiences in **Observation** mode to gather data:

**In-Market Audiences:**
- Health & Fitness
- Healthy Living
- Weight Loss

**Affinity Audiences:**
- Health & Fitness Buffs
- Organic Food Enthusiasts

**Custom Intent Audiences (Create These):**
- People searching for: functional medicine, holistic health, alternative medicine, integrative medicine
- People who visited URLs containing: functionalmedicinenews.com, ifm.org, chriskresser.com

**Remarketing Audiences (Set Up After Launch):**
- Website visitors last 30 days
- Website visitors last 7 days (higher bid)
- Service page viewers
- Pricing page viewers
- Abandoned discovery call forms

---

## CONVERSION TRACKING VERIFICATION

Test each conversion before launch:

### Discovery Call Form Submission
1. Fill out form on website
2. Check Google Ads > Tools > Conversions
3. Verify conversion recorded within 3 hours
4. Value: $200 (estimated value)
5. Count: One

### Phone Calls
1. Click phone number from ad preview
2. Call Google forwarding number
3. Stay on line >60 seconds
4. Verify conversion recorded
5. Value: $200
6. Count: One

### Chat Initiation
1. Start chat from website
2. Send at least one message
3. Verify conversion recorded
4. Value: $50
5. Count: One

---

## LAUNCH DAY CHECKLIST

**Morning of Launch:**
- [ ] Final landing page check (all links working)
- [ ] Phone number test (ensure it rings to practice)
- [ ] Form submission test
- [ ] Mobile experience check
- [ ] Conversion tracking verification
- [ ] Budget verification in Google Ads
- [ ] Ad copy preview (check for typos, policy violations)
- [ ] Sitelinks preview
- [ ] Call extensions showing

**Launch Process:**
1. In Google Ads Editor, select all campaigns
2. Click **Post** > **Post to Google Ads**
3. Review changes summary
4. Click **Post**
5. Wait 5-10 minutes for sync
6. Log into Google Ads web interface
7. Navigate to Campaigns
8. Enable all 3 campaigns
9. Verify status shows "Eligible" (may take 1-24 hours for approval)

**First Hour After Launch:**
- [ ] Check impressions are starting
- [ ] Monitor for disapprovals (fix immediately)
- [ ] Verify ads showing in preview tool
- [ ] Check search impression share
- [ ] Verify conversion tracking tag firing (use Tag Assistant)

---

## FIRST WEEK MONITORING

**Daily Tasks:**
- Check budget pacing (should spend ~14% of monthly budget per day)
- Review search terms report - add negatives
- Check for disapproved ads
- Monitor conversion rate
- Review impression share lost to budget/rank

**Key Metrics to Watch:**
- **Impressions:** Should see 500-1,000+ daily
- **CTR:** Target 6%+ (if below 3%, review ad copy)
- **CPC:** Expected $3-6 range
- **Conversions:** Should see 1-3 daily minimum
- **Cost/Conv:** Target $150-250

**Red Flags (Take Action Immediately):**
- CTR below 2% → Ad copy not resonating, review and test new headlines
- CPC above $8 → Too competitive, lower bids or pause expensive keywords
- Zero conversions after 3 days → Landing page issue or tracking problem
- Impression share below 30% → Budget too low or bids too low

---

## WEEK 2-4 OPTIMIZATION

### Search Terms Analysis (Weekly)
1. Navigate to Keywords > Search terms
2. Look for:
   - **High-converting terms** → Add as exact match keywords
   - **High-volume irrelevant terms** → Add as negative keywords
   - **Question-based searches** → Consider adding to content/FAQ
   - **Competitor names** → Decide if you want to bid

### Keyword Performance Review (Weekly)
Pause keywords that have:
- 0 conversions and >100 clicks
- CPA >$400
- CTR <1%

Increase bids on keywords that have:
- CPA <$150
- Conversion rate >10%
- Impression share lost to rank >20%

### Ad Copy Testing (Every 2 Weeks)
Test new variations:
- Headlines emphasizing different benefits
- Descriptions with different CTAs
- Emotional vs. logical appeals
- Urgency-based messaging

### Landing Page A/B Tests
Test variations of:
- Headline positioning (above fold vs. hero section)
- CTA button text ("Book Free Call" vs. "Start Now")
- CTA button color
- Form length (short lead capture vs. full intake)
- Trust signals (certifications, awards, press)
- Video placement (auto-play vs. click-to-play)

---

## BUDGET SCALING STRATEGY

**If CPA is on target ($150-250) after 2 weeks:**

**Week 3:** Increase budget by 20%
- Medical Mystery Solver: $1,920/month
- Condition Remission: $1,680/month
- Virtual Authority: $1,200/month
- **New Total:** $4,800/month

**Week 5:** Increase budget by another 20%
- Medical Mystery Solver: $2,304/month
- Condition Remission: $2,016/month
- Virtual Authority: $1,440/month
- **New Total:** $5,760/month

**Week 7:** Increase budget by another 20%
- Medical Mystery Solver: $2,765/month
- Condition Remission: $2,419/month
- Virtual Authority: $1,728/month
- **New Total:** $6,912/month

**Maximum Recommended Scale:**
Continue scaling until:
- CPA exceeds $300, OR
- Conversion rate drops below 8%, OR
- Impression share exceeds 80% (diminishing returns)

**Typical Ceiling:** $10,000-15,000/month for this market size

---

## TROUBLESHOOTING COMMON ISSUES

### Issue: Low Impressions
**Causes:**
- Budget too low
- Bids too low
- Keywords too specific
- Ads not approved

**Solutions:**
1. Check campaign status (should be "Eligible")
2. Increase daily budget by 30%
3. Increase keyword bids by 20%
4. Add broader match types (phrase)
5. Expand geographic targeting

### Issue: Low CTR (<3%)
**Causes:**
- Ad copy not compelling
- Ad doesn't match search intent
- Competitor ads more attractive

**Solutions:**
1. Review top-performing competitor ads
2. Test headlines with numbers (96% success)
3. Add urgency ("Limited Slots", "Book Today")
4. Emphasize unique differentiators (200+ biomarkers)
5. Test question-based headlines

### Issue: High CPC (>$8)
**Causes:**
- Bidding on extremely competitive keywords
- Low quality score
- Ad relevance issues

**Solutions:**
1. Check quality score (should be 7+)
2. Improve ad-to-keyword relevance
3. Improve landing page experience
4. Bid on long-tail variations
5. Pause top 5 most expensive keywords temporarily

### Issue: Low Conversion Rate (<5%)
**Causes:**
- Landing page not optimized
- Wrong traffic (search intent mismatch)
- Form too long/complicated
- Phone number not prominent

**Solutions:**
1. Run heat mapping on landing page (Hotjar)
2. Reduce form fields to minimum
3. Add click-to-call button above fold on mobile
4. Add trust signals (reviews, credentials)
5. Test video vs. text-based landing page

### Issue: High Cost Per Conversion (>$350)
**Causes:**
- Bidding on low-intent keywords
- Landing page conversion issues
- Budget spread too thin

**Solutions:**
1. Pause bottom 30% of keywords by performance
2. Focus budget on top 10 keywords
3. Improve landing page conversion rate
4. Add negative keywords aggressively
5. Review search terms for irrelevant traffic

---

## MONTH 2+ ADVANCED STRATEGIES

### Expand to Google Display Network
Once Search is profitable:
- Create remarketing campaigns
- Target in-market audiences
- Use responsive display ads
- Budget: 20% of Search budget

### Test Responsive Search Ads (RSAs)
Provide Google with:
- 15 headline variations
- 4 description variations
- Let Google optimize combinations
- Compare performance to standard ads

### Implement RLSA (Remarketing Lists for Search Ads)
Bid higher on keywords for:
- Previous website visitors
- Discovery call no-shows
- Service page viewers
- Add +30-50% bid adjustment

### Create YouTube Pre-Roll Campaigns
Target:
- Health & wellness channels
- Diabetes education videos
- Hormone health content
- 30-second intro to practice

### Expand Geographic Targeting
If California campaigns are profitable:
- Test expansion to: Arizona, Nevada, Oregon, Washington
- Start at 50% of California bid
- Monitor CPA closely

### Create Smart Campaigns for Gmail Ads
Target:
- People who receive emails about: diabetes, functional medicine, health optimization
- Show sponsored promotions in Gmail
- Lower cost, higher volume

---

## REPORTING & ANALYTICS SETUP

### Create Custom Dashboard in Google Ads
Add these widgets:
- Impressions, Clicks, CTR (line graph by day)
- Conversions by campaign (table)
- Cost per conversion by campaign (bar chart)
- Top 10 keywords by conversions (table)
- Search impression share by campaign
- Hour of day performance (heatmap)

### Set Up Automated Reports (Weekly Email)
Include:
- Week-over-week performance comparison
- Top 10 converting keywords
- Top 10 converting search terms
- Quality score distribution
- Budget pacing

### Google Analytics 4 Custom Reports
Create reports for:
- Landing page performance (bounce rate, time on page, conversions)
- Traffic source comparison (Paid vs. Organic)
- User flow from ad click to conversion
- Device performance comparison
- Geographic performance

### Monthly Performance Review Template
Track these KPIs:
- Total spend
- Total conversions
- Cost per conversion
- Conversion rate
- Average CPC
- Impression share
- Quality score average
- Discovery call show rate
- Discovery call to patient conversion
- Patient lifetime value
- ROAS (Return on Ad Spend)

---

## COMPLIANCE & POLICY REMINDERS

### Google Ads Healthcare Policy
- ✅ Can advertise: Diabetes reversal, hormone therapy, functional medicine
- ❌ Cannot advertise: Cures for diseases, miracle treatments, unapproved therapies
- ⚠️ Use: "Reverse" not "cure" for diabetes
- ⚠️ Include: Disclaimers about individual results

### Medical Advertising Best Practices
- Always substantiate claims (96% success rate should be documented)
- Include physician credentials
- Disclose cash-pay model
- State geographic service areas
- Mention telehealth limitations if applicable

### FTC Endorsement Guidelines
- Patient testimonials must be representative
- Cannot imply typical results if not typical
- Disclose material connections (if any)
- Use "Results may vary" or similar disclaimer

---

## SUCCESS BENCHMARKS (90-Day Goals)

### Traffic Goals
- **Impressions:** 50,000-100,000 total
- **Clicks:** 4,000-8,000 total
- **CTR:** 8-12% average

### Conversion Goals
- **Form Conversions:** 200-400 total
- **Phone Conversions:** 100-200 total
- **Total Leads:** 300-600

### Cost Goals
- **Average CPC:** $3-5
- **Cost Per Lead:** $150-250
- **Total Ad Spend:** $9,000-15,000 (if scaling went well)

### Business Goals
- **Discovery Calls Booked:** 250-500
- **Discovery Call Show Rate:** 70%+ (175-350 shows)
- **Discovery to Patient Conversion:** 40%+ (70-140 new patients)
- **Revenue from Google Ads:** $100,000-200,000
- **ROAS:** 7:1 to 15:1

---

## CONTACT FOR TECHNICAL SUPPORT

**Google Ads Support:**
- Phone: 1-866-2GOOGLE (1-866-246-6453)
- Available: Monday-Friday, 9 AM - 8 PM EST
- Email: Through Google Ads interface (Help > Contact Us)

**Google Ads Editor Support:**
- Help Center: support.google.com/google-ads/editor

**Conversion Tracking Issues:**
- Google Tag Manager: support.google.com/tagmanager
- Google Analytics: support.google.com/analytics

---

## FINAL PRE-LAUNCH CHECKLIST

Print this and check off before going live:

- [ ] All CSV files imported successfully
- [ ] All ad groups have 2+ ads
- [ ] All sitelinks have descriptions
- [ ] All callouts imported and assigned
- [ ] Negative keywords applied at account level
- [ ] Location targeting verified (right cities/states)
- [ ] Budget set correctly ($3,000-5,000/month minimum)
- [ ] Conversion tracking tested and working
- [ ] Landing pages load in <3 seconds
- [ ] Phone number click-to-call on mobile
- [ ] Forms tested and submitting correctly
- [ ] Ad schedule set (with bid adjustments)
- [ ] Device bid adjustments configured
- [ ] Remarketing audiences created (will populate after launch)
- [ ] Google Analytics linked to Google Ads
- [ ] Credit card added and valid
- [ ] First month budget allocated
- [ ] Team briefed on expected call volume increase
- [ ] Discovery call booking calendar has availability
- [ ] All campaigns enabled in Google Ads interface

---

**You're ready to launch!**

Expected timeline to first conversion: 1-7 days
Expected timeline to profitability: 2-4 weeks
Expected timeline to scale: 4-8 weeks

Questions? Review the main strategy document: **google_ads_campaign.md**

Good luck with your campaign launch!

---

**Document Version:** 1.0
**Last Updated:** February 10, 2026
**Created For:** Advanced Functional Medicine
**Created By:** Claude (Anthropic)
