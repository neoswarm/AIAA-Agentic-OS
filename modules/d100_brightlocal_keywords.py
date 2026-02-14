"""
Dream 100 BrightLocal Keyword Generator
Generates 100 local SEO keywords from structured_data.json and sends to Slack
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class D100BrightLocalKeywords:
    """Generate BrightLocal keywords from structured practice data"""

    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.seo_dir = self.run_dir / "seo_data"
        self.seo_dir.mkdir(exist_ok=True)

        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

        if not self.openrouter_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env")

    def generate(self, structured_data):
        """
        Generate BrightLocal keywords from structured JSON

        Returns:
            dict: {
                "success": bool,
                "keywords": list,
                "keywords_path": Path,
                "slack_sent": bool,
                "error": str (if failed)
            }
        """
        # Extract data from JSON
        services = self._extract_services(structured_data)
        conditions = self._extract_conditions(structured_data)
        primary_city = self._extract_primary_city(structured_data)
        adjacent_cities = self._extract_adjacent_cities(structured_data)

        # Build prompt
        prompt = self._build_prompt(services, conditions, primary_city, adjacent_cities)

        # Call Claude to generate keywords
        try:
            keywords = self._generate_keywords_with_claude(prompt)

            # Save keywords
            keywords_path = self.seo_dir / "brightlocal_keywords.txt"
            with open(keywords_path, "w") as f:
                f.write("\n".join(keywords))

            # Also save as JSON for programmatic access
            keywords_json_path = self.seo_dir / "brightlocal_keywords.json"
            with open(keywords_json_path, "w") as f:
                json.dump({
                    "keywords": keywords,
                    "total": len(keywords),
                    "primary_city": primary_city,
                    "adjacent_cities": adjacent_cities,
                    "services_count": len(services),
                    "conditions_count": len(conditions)
                }, f, indent=2)

            # Send to Slack
            slack_sent = False
            if self.slack_webhook:
                slack_sent = self._send_to_slack(
                    keywords,
                    primary_city,
                    adjacent_cities,
                    len(services),
                    len(conditions)
                )

            return {
                "success": True,
                "keywords": keywords,
                "keywords_path": str(keywords_path),
                "keywords_json_path": str(keywords_json_path),
                "total_keywords": len(keywords),
                "slack_sent": slack_sent
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_services(self, data):
        """Extract service names from structured data"""
        services = []
        for service in data.get("services", []):
            name = service.get("name", {}).get("value")
            if name:
                services.append(name)
        return services[:20]  # Limit to top 20

    def _extract_conditions(self, data):
        """Extract condition names from structured data"""
        conditions = []
        for condition in data.get("conditions", []):
            name = condition.get("name", {}).get("value")
            if name:
                conditions.append(name)
        return conditions[:20]  # Limit to top 20

    def _extract_primary_city(self, data):
        """Extract primary city from locations"""
        locations = data.get("locations", [])
        if locations:
            primary = next((loc for loc in locations if loc.get("type") == "primary"), locations[0])
            address = primary.get("address", {}).get("value", "")
            # Simple city extraction (assumes "City, State" format)
            if "," in address:
                city = address.split(",")[0].strip()
                return city
        return "San Diego"  # Default fallback

    def _extract_adjacent_cities(self, data):
        """Extract or infer 3 adjacent cities"""
        # Check if already in locations
        locations = data.get("locations", [])
        adjacent = [loc.get("address", {}).get("value", "").split(",")[0].strip()
                    for loc in locations if loc.get("type") == "additional"]

        # If we have at least 3, return first 3
        if len(adjacent) >= 3:
            return adjacent[:3]

        # Otherwise, infer based on primary city (hardcoded for common cities)
        primary_city = self._extract_primary_city(data)

        # Common adjacent city mappings
        adjacent_map = {
            "San Diego": ["La Jolla", "Del Mar", "Encinitas"],
            "Los Angeles": ["Santa Monica", "Beverly Hills", "Pasadena"],
            "New York": ["Brooklyn", "Queens", "Manhattan"],
            "Chicago": ["Evanston", "Oak Park", "Naperville"],
            "Austin": ["Round Rock", "Cedar Park", "Georgetown"],
            "Miami": ["Coral Gables", "Miami Beach", "Aventura"],
            "Seattle": ["Bellevue", "Redmond", "Kirkland"],
            "Boston": ["Cambridge", "Brookline", "Somerville"],
            "Phoenix": ["Scottsdale", "Tempe", "Mesa"],
            "Denver": ["Aurora", "Lakewood", "Boulder"]
        }

        return adjacent_map.get(primary_city, [
            f"{primary_city} North",
            f"{primary_city} South",
            f"{primary_city} East"
        ])

    def _build_prompt(self, services, conditions, primary_city, adjacent_cities):
        """Build the keyword generation prompt"""
        services_text = "\n".join(f"- {s}" for s in services)
        conditions_text = "\n".join(f"- {c}" for c in conditions)
        adjacent_text = ", ".join(adjacent_cities)

        return f"""You are a senior local SEO strategist preparing a BrightLocal rank-tracking and audit keyword set for a medical or healthcare practice.

TASK:
Using the company context I provide (services, conditions treated, primary city, and adjacent cities), generate a list of up to **100 UNIQUE, high-intent keywords** suitable for a BrightLocal Local SEO Audit and Rank Tracking setup.

GOAL:
Create a clean, non-duplicative keyword list that accurately reflects:
- Core commercial intent
- Local intent ("near me" and city-modified searches)
- Service-based and condition-based demand

INPUT DATA:

[SERVICES]:
{services_text}

[CONDITIONS]:
{conditions_text}

[PRIMARY_CITY]: {primary_city}

[ADJACENT_CITIES]: {adjacent_text}

KEYWORD RULES:
- Max 100 total keywords
- One keyword per line
- No duplicates or close variants
- Use natural, real search phrases (no keyword stuffing)
- Prioritize patient / appointment intent
- Mix singular and plural ONLY when meaningfully different
- Do NOT add extra cities beyond those provided
- Do NOT include brand terms

KEYWORD CATEGORIES TO COVER (DISTRIBUTE EVENLY):
1. SERVICES
2. CONDITIONS
3. X near me
4. SERVICES [{primary_city}]
5. CONDITIONS [{primary_city}]
6. X near [{primary_city}]
7. SERVICES [{adjacent_cities[0]}]
8. SERVICES [{adjacent_cities[1]}]
9. SERVICES [{adjacent_cities[2]}]
10. CONDITIONS [{adjacent_cities[0]}]
11. CONDITIONS [{adjacent_cities[1]}]
12. CONDITIONS [{adjacent_cities[2]}]
13. X near me [{adjacent_cities[0]}]
14. X near me [{adjacent_cities[1]}]
15. X near me [{adjacent_cities[2]}]

OUTPUT FORMAT (STRICT – BRIGHTLOCAL READY):
- Plain text
- One keyword per line
- No headings
- No numbering
- No explanations
- Copy & paste ready for BrightLocal

BEGIN KEYWORD GENERATION:"""

    def _generate_keywords_with_claude(self, prompt):
        """Call Claude Opus 4 via OpenRouter to generate keywords"""
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://aiaa-agentic-os.local",
                "X-Title": "AIAA D100 BrightLocal Keywords"
            },
            json={
                "model": "anthropic/claude-opus-4",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 3000
            },
            timeout=120
        )

        response.raise_for_status()
        data = response.json()

        keywords_text = data["choices"][0]["message"]["content"]

        # Parse keywords (one per line, skip empty lines)
        keywords = [
            line.strip()
            for line in keywords_text.strip().split("\n")
            if line.strip() and not line.startswith("#")
        ]

        return keywords[:100]  # Ensure max 100

    def _send_to_slack(self, keywords, primary_city, adjacent_cities, services_count, conditions_count):
        """Send keywords to Slack"""
        if not self.slack_webhook:
            return False

        # Create keyword preview (first 10 + last 5)
        preview_keywords = keywords[:10] + ["..."] + keywords[-5:]
        keywords_preview = "\n".join(f"• {kw}" for kw in preview_keywords)

        message = {
            "text": f"✅ BrightLocal Keywords Generated: {primary_city}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"✅ BrightLocal Keywords: {primary_city}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Total Keywords:* {len(keywords)}\n*Primary City:* {primary_city}\n*Adjacent Cities:* {', '.join(adjacent_cities)}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Input Data:*\n• Services: {services_count}\n• Conditions: {conditions_count}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Keyword Preview (first 10 + last 5):*\n{keywords_preview}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "📄 *Full keyword list saved to:* `seo_data/brightlocal_keywords.txt`"
                    }
                }
            ]
        }

        try:
            response = requests.post(self.slack_webhook, json=message, timeout=10)
            return response.status_code == 200
        except:
            return False
