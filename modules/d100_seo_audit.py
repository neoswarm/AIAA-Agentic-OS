"""
Dream 100 SEO Audit Module
Analyzes SEMrush data and screenshot to create doctor-friendly SEO insights
"""

import os
import json
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class D100SEOAudit:
    """Generate doctor-friendly SEO analysis from SEMrush data and screenshot"""

    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.seo_dir = self.run_dir / "seo_data"
        self.seo_dir.mkdir(exist_ok=True)

        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not self.openrouter_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env")

    def analyze(self, screenshot_path, keywords_csv_path, structured_data):
        """
        Analyze SEO data using screenshot + CSV + practice context

        Args:
            screenshot_path: Path to SEMrush site overview screenshot
            keywords_csv_path: Path to keyword rankings CSV export
            structured_data: Practice JSON data from scraper

        Returns:
            dict: {
                "success": bool,
                "analysis_path": Path,
                "error": str (if failed)
            }
        """
        # Extract practice context from structured JSON
        practice_name = structured_data.get("practice", {}).get("brand_name", {}).get("value", "Unknown Practice")
        specialty = structured_data.get("practice", {}).get("specialty", {}).get("value", "Healthcare")
        primary_city = self._extract_primary_city(structured_data)

        # Read CSV keywords
        keywords_data = self._parse_keywords_csv(keywords_csv_path)

        # Encode screenshot as base64
        screenshot_base64 = self._encode_image(screenshot_path)

        # Build prompt
        prompt = self._build_prompt(
            practice_name,
            specialty,
            primary_city,
            keywords_data,
            screenshot_base64
        )

        # Call Claude Opus 4 with vision
        try:
            analysis = self._generate_analysis_with_claude(prompt, screenshot_base64)

            # Save analysis
            analysis_path = self.seo_dir / "seo_analysis_for_doctors.md"
            with open(analysis_path, "w") as f:
                f.write(analysis)

            return {
                "success": True,
                "analysis_path": str(analysis_path),
                "analysis_text": analysis
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_primary_city(self, data):
        """Extract primary city from locations"""
        locations = data.get("locations", [])
        if locations:
            primary = next((loc for loc in locations if loc.get("type") == "primary"), locations[0])
            address = primary.get("address", {}).get("value", "")
            if "," in address:
                city = address.split(",")[0].strip()
                return city
        return "Unknown City"

    def _parse_keywords_csv(self, csv_path):
        """Parse SEMrush keyword CSV export"""
        import csv

        keywords = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    keywords.append({
                        "keyword": row.get("Keyword", row.get("keyword", "")),
                        "position": row.get("Position", row.get("position", "")),
                        "volume": row.get("Search Volume", row.get("volume", row.get("search_volume", ""))),
                        "traffic": row.get("Traffic", row.get("traffic", ""))
                    })
        except Exception as e:
            print(f"Warning: Could not parse CSV: {e}")

        return {
            "total_keywords": len(keywords),
            "top_10_keywords": keywords[:10],
            "sample_keywords": keywords[:20]
        }

    def _encode_image(self, image_path):
        """Encode image as base64 for Claude vision API"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _build_prompt(self, practice_name, specialty, primary_city, keywords_data, screenshot_base64):
        """Build the SEO analysis prompt"""
        # Format keyword data for prompt
        top_keywords = "\n".join([
            f"- {kw['keyword']} (Position: {kw['position']}, Volume: {kw['volume']})"
            for kw in keywords_data.get("top_10_keywords", [])[:10]
        ])

        return f"""You are a senior healthcare growth strategist who specializes in explaining SEO, AI search, and patient acquisition to BUSY DOCTORS who do NOT understand marketing.

TASK:
Evaluate this medical practice website using the following inputs:
- A SEMrush site overview screenshot (attached)
- SEO keyword rankings export
- Practice context

Your job is to translate this data into Dream 100–level insights that are:
- Extremely clear
- Honest (no hype, no jargon)
- Engaging and slightly provocative
- Easy enough to understand at an ELI5 level
- Written for a physician who has 90 seconds of attention

PRIMARY GOAL:
Help the doctor understand:
1) What is ACTUALLY happening with their site
2) Why traffic/patients are going up or down
3) How Google + AI are changing patient behavior
4) Whether this is a threat, an opportunity, or both
5) What happens if they do nothing vs act correctly

AUDIENCE:
- Busy doctors
- Practice owners
- Medical executives
- Zero marketing background
- Care about patients, authority, and revenue — not SEO terms

CONSTRAINTS:
- NO marketing jargon unless immediately explained in plain English
- NO tactical how-to steps
- NO selling services
- NO fluff, buzzwords, or generic SEO explanations
- Tone: calm, confident, direct, slightly urgent
- Write like a trusted advisor, not a marketer
- Format for LARGE text blocks suitable for pasting into Gamma (clean section breaks, strong headings, high visual clarity)
- Do NOT use parentheses in the final output
- Do NOT use bracketed placeholders in the final output
- Replace all variables with clean, natural language values
- The final output must contain zero brackets or placeholder markers of any kind

STRUCTURE (MANDATORY — USE THESE EXACT HEADINGS):

# What's Actually Happening With Your Website

## Bottom Line
2–3 sentences max.
Plain-English verdict on trust, visibility, and patient demand.

## What the Data Shows
Bulleted, simple language.
Explain ONLY what matters from:
- Organic traffic trend
- Keyword footprint
- Authority / backlinks
- AI visibility such as AI Overviews or Gemini

Translate metrics into real-world meaning such as patients, trust, and demand.

## What Changed And Why It Matters
Explain how Google and AI now answer patient questions directly.
Use analogies a doctor would understand.
Emphasize authority without clicks and answers without visits.

## The Real Problem
Clearly state how the practice is helping Google educate patients
without sending those patients to the practice.
Make the cost feel real but not alarmist.

## Why This Is Actually an Opportunity
Contrast the practice against competitors:
- Most have declining traffic and zero AI visibility
- This site has AI trust but poor conversion and control

Explain why this is a leverage position, not a rebuild.

## If Nothing Changes
Use ranges and plain consequences:
- Patient inquiries
- Cost of ads
- Competitive positioning

No fear-mongering. Just reality.

## If This Is Handled Correctly
Paint a clear, credible upside:
- Recapturing demand already being answered by AI
- Becoming the named authority AI systems recommend
- Turning visibility into booked appointments

---

INPUT DATA:

**Practice Name:** {practice_name}
**Specialty:** {specialty}
**Primary Market:** {primary_city}

**Top 10 Ranking Keywords:**
{top_keywords}

**Total Keywords Tracked:** {keywords_data['total_keywords']}

**SEMrush Screenshot:** Attached (analyze traffic trends, domain authority, backlinks, and any visible metrics)

---

OUTPUT RULES:
- Write in short paragraphs
- Use bold for emphasis sparingly
- Speak directly to "you" (the doctor)
- No emojis
- No disclaimers
- No marketing terminology unless explained like speaking to a busy doctor
- Return ONLY the final narrative
- No explanations
- No meta commentary
- No parentheses
- No brackets
- No placeholder text of any kind

BEGIN ANALYSIS:"""

    def _generate_analysis_with_claude(self, prompt, screenshot_base64):
        """Call Claude Sonnet 3.7 with vision to analyze SEO data"""
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://aiaa-agentic-os.local",
                "X-Title": "AIAA D100 SEO Audit"
            },
            json={
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": screenshot_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                "temperature": 0.4,
                "max_tokens": 4000
            },
            timeout=180
        )

        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]
