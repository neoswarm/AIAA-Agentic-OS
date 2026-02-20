"""D100 Google Ads Campaign Builder - GPT-4o via OpenRouter"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime


class D100AdsBuilder:
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")

        if not self.openrouter_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

    def build(self, structured_data, booking_url=None):
        """
        Generate 5 Google Ads campaigns from structured JSON data.

        Returns:
            dict: { status, ads_path, timestamp }
        """
        try:
            # Extract context
            practice   = structured_data.get("practice", {})
            services   = structured_data.get("services", [])
            conditions = structured_data.get("conditions", [])

            company_name  = (
                practice.get("brand_name", {}).get("value") or
                practice.get("legal_name", {}).get("value") or
                "Healthcare Practice"
            )
            specialty     = practice.get("specialty", {}).get("value", "Integrative Medicine")
            service_list  = [s.get("name", {}).get("value", "") for s in services if s.get("name", {}).get("value")]
            condition_list = [c.get("name", {}).get("value", "") for c in conditions if c.get("name", {}).get("value")]

            # Build prompt
            prompt = f"""Create a comprehensive Google Ads campaign structure for this healthcare practice.

PRACTICE:
- Name: {company_name}
- Specialty: {specialty}
- Services: {', '.join(service_list[:10])}
- Conditions: {', '.join(condition_list[:10])}
- Booking URL: {booking_url or '[BOOKING_URL]'}

CREATE EXACTLY 5 CAMPAIGNS with these headers:
## 1. Brand Protection Campaign
## 2. Service High-Intent Campaign
## 3. Competitor/Local Campaign
## 4. Remarketing Campaign
## 5. Assessment App Traffic Campaign

For each campaign include:
- Objective & monthly budget recommendation
- 15-20 exact/phrase match keywords
- 3 Responsive Search Ads (15 headlines + 4 descriptions each)
- Sitelink, callout, and structured snippet extensions
- Negative keywords list
- Landing page recommendation
- Expected CPC range and ROI projection

Use clean markdown. Be specific to the practice market and audience."""

            print(f"  🏗️  Building Google Ads campaigns...")

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type":  "application/json"
                },
                json={
                    "model":       "openai/gpt-4o",
                    "messages":    [{"role": "user", "content": prompt}],
                    "temperature": 0.6,
                    "max_tokens":  8000
                },
                timeout=180
            )

            if response.status_code != 200:
                raise ValueError(f"OpenRouter error: {response.status_code}")

            ads_content = response.json()["choices"][0]["message"]["content"]

            # Save
            ads_dir = self.run_dir / "ads"
            ads_dir.mkdir(parents=True, exist_ok=True)
            ads_path = ads_dir / "google-ads-campaigns.md"
            ads_path.write_text(ads_content, encoding="utf-8")

            print(f"  ✅ Ads saved ({len(ads_content):,} chars)")

            return {
                "status":    "success",
                "ads_path":  str(ads_path),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "status":    "error",
                "error":     str(e),
                "timestamp": datetime.now().isoformat()
            }
