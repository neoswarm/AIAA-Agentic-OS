"""
D100 Gamma API Integration
Generates a Gamma presentation from Dream 100 deliverables.

Template ID: g_tibdaac6hk58l4v

Placeholders:
  [COMPANY]       - company name
  [APP_URL]       - https://portal.healthbizscale.com/[COMPANY-slug]
  [SEO_INSIGHTS]  - SEMrush SEO analysis text
  [AD_CAMPAIGN1]  - Google Ads campaign 1 text
  [AD_CAMPAIGN2]  - Google Ads campaign 2 text
  [AD_CAMPAIGN3]  - Google Ads campaign 3 text
  [AD_CAMPAIGN4]  - Google Ads campaign 4 text
  [AD_CAMPAIGN5]  - Google Ads campaign 5 text
  [EMAIL1]        - Email 1 full text
  [EMAIL2]        - Email 2 full text
  [EMAIL3]        - Email 3 full text
"""

import os
import re
import json
import requests
from pathlib import Path
from datetime import datetime


class D100Gamma:
    TEMPLATE_ID = "g_tibdaac6hk58l4v"
    GAMMA_API_BASE = "https://public-api.gamma.app/v1.0"

    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.api_key = os.getenv("GAMMA_API_KEY")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

        if not self.api_key:
            raise ValueError("GAMMA_API_KEY not found in environment")

    # ------------------------------------------------------------------
    # PUBLIC ENTRY POINT
    # ------------------------------------------------------------------

    def generate(self, structured_data, booking_url=None):
        """
        Build a Gamma presentation from D100 run outputs.

        Args:
            structured_data (dict): JSON from d100_scraper
            booking_url (str): Optional booking URL

        Returns:
            dict: { status, gamma_url, doc_id, timestamp }
        """
        try:
            # 1. Extract company name & build APP_URL slug
            company_name = self._get_company_name(structured_data)
            app_url = self._build_app_url(company_name)

            print(f"  📐 Building Gamma for: {company_name}")
            print(f"  🔗 App URL: {app_url}")

            # 2. Load all content files from the run directory
            seo_insights   = self._load_seo_insights()
            campaigns      = self._load_ad_campaigns()   # list of 5 strings
            emails         = self._load_emails()         # list of 3 strings

            # 3. Build placeholder map
            placeholders = self._build_placeholders(
                company_name, app_url, seo_insights, campaigns, emails
            )

            # 4. Call Gamma API
            result = self._call_gamma_api(placeholders)

            # 5. Notify Slack
            gamma_url = result.get("url", "")
            doc_id    = result.get("generationId") or result.get("id", "")
            self._slack_gamma_done(company_name, gamma_url)

            return {
                "status":    "success",
                "gamma_url": gamma_url,
                "doc_id":    doc_id,
                "company":   company_name,
                "app_url":   app_url,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "status":    "error",
                "error":     str(e),
                "timestamp": datetime.now().isoformat()
            }

    # ------------------------------------------------------------------
    # CONTENT LOADERS
    # ------------------------------------------------------------------

    def _get_company_name(self, structured_data):
        practice = structured_data.get("practice", {})
        name = (
            practice.get("brand_name", {}).get("value") or
            practice.get("legal_name", {}).get("value") or
            "Healthcare Practice"
        )
        return name.strip()

    def _build_app_url(self, company_name):
        slug = company_name.strip().replace(" ", "-")
        return f"https://portal.healthbizscale.com/{slug}"

    def _load_seo_insights(self):
        """Load SEO analysis markdown, strip markdown headers for cleaner Gamma text."""
        path = self.run_dir / "seo_data" / "seo_analysis.md"
        if not path.exists():
            return "[SEO analysis not available]"
        text = path.read_text(encoding="utf-8")
        # Remove leading # headers to keep it prose-friendly inside Gamma
        text = re.sub(r'^#{1,3} .+\n', '', text, flags=re.MULTILINE)
        return text.strip()[:4000]  # Gamma placeholder cap

    def _load_ad_campaigns(self):
        """
        Parse google-ads-campaigns.md into exactly 5 campaign strings.
        Splits on '## [0-9]+.' or '## Campaign' headers.
        Falls back to empty strings if not enough campaigns.
        """
        # v2.0 filename first, then v1.0 fallback
        path = self.run_dir / "ads" / "google_ads_campaign.md"
        if not path.exists():
            path = self.run_dir / "ads" / "google-ads-campaigns.md"
        if not path.exists():
            return ["[Ad campaign not available]"] * 5

        text = path.read_text(encoding="utf-8")

        # Split on campaign section headers (## 1. or ## Campaign 1 or similar)
        sections = re.split(r'\n(?=## (?:\d+\.|\w+ \d+|Campaign \d+))', text)

        # Drop the first chunk if it's a title line only (< 100 chars, no ## header)
        campaigns = []
        for s in sections:
            s = s.strip()
            if not s or len(s) < 30:
                continue
            # Skip if it's a top-level title (# heading) with no campaign body
            if s.startswith('# ') and '##' not in s:
                continue
            campaigns.append(s)

        # Pad or trim to exactly 5
        while len(campaigns) < 5:
            campaigns.append("[Ad campaign not available]")
        campaigns = campaigns[:5]

        # Cap each at 2000 chars for Gamma
        return [c[:2000] for c in campaigns]

    def _load_emails(self):
        """
        Parse nurture-sequences.md into exactly 3 email strings.
        Splits on 'Email 1', 'Email 2', 'Email 3' markers.
        """
        # v2.0 filename first, then v1.0 fallback
        path = self.run_dir / "emails" / "sequence.md"
        if not path.exists():
            path = self.run_dir / "emails" / "nurture-sequences.md"
        if not path.exists():
            return ["[Email not available]"] * 3

        text = path.read_text(encoding="utf-8")

        # Split on Email 1 / Email 2 / Email 3 markers (flexible)
        sections = re.split(r'\n(?=Email \d|EMAIL \d|## Email \d)', text)

        emails = [s.strip() for s in sections if s.strip() and len(s.strip()) > 20]

        while len(emails) < 3:
            emails.append("[Email not available]")
        emails = emails[:3]

        return [e[:2000] for e in emails]

    # ------------------------------------------------------------------
    # PLACEHOLDER BUILDER
    # ------------------------------------------------------------------

    def _build_placeholders(self, company_name, app_url, seo_insights, campaigns, emails):
        return {
            "[COMPANY]":       company_name,
            "[APP_URL]":       app_url,
            "[SEO_INSIGHTS]":  seo_insights,
            "[AD_CAMPAIGN1]":  campaigns[0],
            "[AD_CAMPAIGN2]":  campaigns[1],
            "[AD_CAMPAIGN3]":  campaigns[2],
            "[AD_CAMPAIGN4]":  campaigns[3],
            "[AD_CAMPAIGN5]":  campaigns[4],
            "[EMAIL1]":        emails[0],
            "[EMAIL2]":        emails[1],
            "[EMAIL3]":        emails[2],
        }

    # ------------------------------------------------------------------
    # GAMMA API CALL
    # ------------------------------------------------------------------

    def _build_prompt(self, placeholders):
        """
        Build the prompt string that drives template adaptation.
        Gamma uses free-form prompt text (not a substitutions map).
        Pack all placeholder values clearly so Gamma fills the template correctly.
        """
        p = placeholders
        return f"""Fill in this Dream 100 presentation template for a healthcare practice.

COMPANY NAME: {p['[COMPANY]']}
APP URL: {p['[APP_URL]']}

SEO INSIGHTS:
{p['[SEO_INSIGHTS]']}

GOOGLE ADS CAMPAIGN 1:
{p['[AD_CAMPAIGN1]']}

GOOGLE ADS CAMPAIGN 2:
{p['[AD_CAMPAIGN2]']}

GOOGLE ADS CAMPAIGN 3:
{p['[AD_CAMPAIGN3]']}

GOOGLE ADS CAMPAIGN 4:
{p['[AD_CAMPAIGN4]']}

GOOGLE ADS CAMPAIGN 5:
{p['[AD_CAMPAIGN5]']}

EMAIL 1 (Smart Practice Value Drop):
{p['[EMAIL1]']}

EMAIL 2 (Mechanism Story):
{p['[EMAIL2]']}

EMAIL 3 (Proof & Results):
{p['[EMAIL3]']}

Replace every placeholder in the template with the matching content above.
Keep all slide structure, headings, and formatting from the original template."""

    def _call_gamma_api(self, placeholders):
        """
        POST to Gamma API — Create from Template.
        Endpoint: POST /v1.0/generations/from-template
        Auth:     X-API-KEY header
        Body:     { gammaId, prompt }
        """
        prompt = self._build_prompt(placeholders)

        payload = {
            "gammaId": self.TEMPLATE_ID,
            "prompt":  prompt,
        }

        headers = {
            "X-API-KEY":    self.api_key,
            "Content-Type": "application/json",
            "Accept":       "application/json"
        }

        print(f"  🌐 Calling Gamma API (template: {self.TEMPLATE_ID})...")

        response = requests.post(
            f"{self.GAMMA_API_BASE}/generations/from-template",
            headers=headers,
            json=payload,
            timeout=180
        )

        if response.status_code not in (200, 201):
            raise ValueError(
                f"Gamma API error {response.status_code}: {response.text[:500]}"
            )

        data = response.json()

        # POST returns only { generationId } — poll GET until gammaUrl is available
        import time
        generation_id = data.get("generationId", "")
        if generation_id:
            print(f"  🔍 Polling Gamma for real URL (generationId: {generation_id})...")
            gamma_url = None
            # Poll up to 20 attempts × 15s = 5 minutes
            for attempt in range(20):
                status_resp = requests.get(
                    f"{self.GAMMA_API_BASE}/generations/{generation_id}",
                    headers=headers,
                    timeout=30
                )
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    gamma_url = status_data.get("gammaUrl", "")
                    gen_status = status_data.get("status", "")
                    if gamma_url and gamma_url not in ("unknown", ""):
                        data["url"] = gamma_url
                        data["gammaUrl"] = gamma_url
                        data["id"] = generation_id
                        data["credits"] = status_data.get("credits", {})
                        print(f"  ✅ Real Gamma URL: {gamma_url}")
                        break
                    elif gen_status == "failed":
                        raise ValueError(f"Gamma generation failed: {status_data}")
                    print(f"  ⏳ Still generating (attempt {attempt+1}/20)...")
                    time.sleep(15)
            else:
                # Timed out — save what we have
                data["url"] = f"https://gamma.app (pending — generationId: {generation_id})"
                data["id"] = generation_id
                print(f"  ⚠️ Timed out — generationId saved: {generation_id}")
        elif "gammaUrl" in data:
            data["url"] = data["gammaUrl"]
        elif "url" not in data:
            data["url"] = "unknown"

        # Save full enriched response for debugging
        debug_path = self.run_dir / "gamma_response.json"
        debug_path.write_text(json.dumps(data, indent=2))

        return data

    # ------------------------------------------------------------------
    # SLACK NOTIFICATION
    # ------------------------------------------------------------------

    def _slack_gamma_done(self, company_name, gamma_url):
        if not self.slack_webhook:
            return
        msg = (
            f"📊 *Gamma Presentation Created: {company_name}*\n\n"
            f"🔗 View: {gamma_url}\n"
            f"📋 Template: `{self.TEMPLATE_ID}`\n"
            f"⏱️ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        try:
            requests.post(self.slack_webhook, json={"text": msg}, timeout=10)
        except Exception:
            pass  # Slack failure never blocks main flow
