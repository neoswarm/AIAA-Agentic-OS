# SKILL: Dream 100 Gamma Presentation Builder

## METADATA
- **Skill Name**: Dream 100 Gamma Integration
- **Version**: 2.0
- **Category**: Presentation Generation
- **API Requirements**: Gamma API (GAMMA_API_KEY)
- **Parent Skill**: SKILL_D100_orchestrator
- **Module**: `modules/d100_gamma.py`

---

## MISSION
Generate a Gamma presentation from completed D100 run assets using a pre-built template.
Sends a Slack notification with the live Gamma URL when complete.

---

## TEMPLATE

**Template ID:** `g_tibdaac6hk58l4v`

---

## PLACEHOLDERS

| Placeholder     | Source                                      |
|-----------------|---------------------------------------------|
| `[COMPANY]`     | `structured_json.practice.brand_name.value` |
| `[APP_URL]`     | `https://portal.healthbizscale.com/[Company-slug]` (spaces → `-`) |
| `[SEO_INSIGHTS]`| `seo_data/seo_analysis.md` (stripped of `#` headers, max 4,000 chars) |
| `[AD_CAMPAIGN1]`| Campaign 1 from `ads/google-ads-campaigns.md` (max 2,000 chars) |
| `[AD_CAMPAIGN2]`| Campaign 2 |
| `[AD_CAMPAIGN3]`| Campaign 3 |
| `[AD_CAMPAIGN4]`| Campaign 4 |
| `[AD_CAMPAIGN5]`| Campaign 5 |
| `[EMAIL1]`      | Email 1 from `emails/nurture-sequences.md` (max 2,000 chars) |
| `[EMAIL2]`      | Email 2 |
| `[EMAIL3]`      | Email 3 |

---

## EXECUTION LOGIC

### STEP 1: LOAD ASSETS
- Read `structured_data.json` → extract company name
- Read `seo_data/seo_analysis.md`
- Parse `ads/google-ads-campaigns.md` into 5 campaigns (split on `## [n].` headers)
- Parse `emails/nurture-sequences.md` into 3 emails (split on `Email 1/2/3` markers)

### STEP 2: BUILD SLUG & APP URL
```python
slug = company_name.strip().replace(" ", "-")
app_url = f"https://portal.healthbizscale.com/{slug}"
```

### STEP 3: CALL GAMMA API
```
POST https://public-api.gamma.app/v1.0/generations/from-template
Headers:
  X-API-KEY: {GAMMA_API_KEY}
  Content-Type: application/json

Body:
{
  "gammaId": "g_tibdaac6hk58l4v",
  "prompt":  "<all placeholder content packed as free-form text>"
}
```
Note: Gamma uses a free-form `prompt` field (not a substitutions map) to adapt the template.
All 10 placeholder values are packed into the prompt with clear labels.

### STEP 4: SAVE & NOTIFY
- Save raw API response to `{run_dir}/gamma_response.json`
- Send Slack message:
  ```
  📊 Gamma Presentation Created: {company_name}
  🔗 View: {gamma_url}
  ```

---

## OUTPUT

**Success:**
```json
{
  "status":    "success",
  "gamma_url": "https://gamma.app/docs/...",
  "doc_id":    "abc123",
  "company":   "Raby Institute",
  "app_url":   "https://portal.healthbizscale.com/Raby-Institute",
  "timestamp": "ISO-8601"
}
```

**Error:**
```json
{
  "status":    "error",
  "error":     "Gamma API error 401: ...",
  "timestamp": "ISO-8601"
}
```

---

## SLACK NOTIFICATIONS

Two Slack messages are sent during a full D100 run:

1. **After BrightLocal Keywords** (from `d100_brightlocal_keywords.py`):
   ```
   🎯 BrightLocal Keywords: {company_name}
   📍 {location}
   🔢 Total: 100 keywords
   Preview: [first 15]
   ```

2. **After Gamma Generation** (from `d100_gamma.py`):
   ```
   📊 Gamma Presentation Created: {company_name}
   🔗 View: {gamma_url}
   ```

---

## ERROR HANDLING

| Error                  | Action                                      |
|------------------------|---------------------------------------------|
| Missing SEO file       | Use `[SEO analysis not available]`          |
| Missing ads file       | Use `[Ad campaign not available]` × 5       |
| Missing email file     | Use `[Email not available]` × 3             |
| < 5 ad campaigns found | Pad remaining with placeholder text         |
| < 3 emails found       | Pad remaining with placeholder text         |
| Gamma API 4xx          | Raise error, log to `error_log.txt`         |
| Gamma API 5xx          | Raise error, do not retry automatically     |
| Slack failure          | Silent (never blocks main flow)             |

---

## VERSION HISTORY

**1.0** - Initial release
- Gamma template integration (`g_tibdaac6hk58l4v`)
- Auto-parses 5 ad campaigns + 3 emails from run output files
- APP_URL slug generation (spaces → hyphens)
- Dual Slack notifications (keywords + Gamma URL)
- Full error handling with fallback placeholders
