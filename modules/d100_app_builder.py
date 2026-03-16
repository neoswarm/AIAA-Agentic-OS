"""Dream 100 Health Assessment App Builder - Claude Opus 4.6"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path


class D100AppBuilder:
    def __init__(self, run_dir):
        self.run_dir = run_dir
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.openrouter_key = os.getenv('OPENROUTER_API_KEY')

        # Prefer Anthropic API, fallback to OpenRouter
        if not self.anthropic_key and not self.openrouter_key:
            raise ValueError("Neither ANTHROPIC_API_KEY nor OPENROUTER_API_KEY found in environment")

    def build(self, structured_data, booking_url):
        """
        Build health assessment app using Claude Opus 4.6 via Anthropic API

        Args:
            structured_data: JSON output from D100 scraper
            booking_url: Booking URL for redirect

        Returns:
            dict: Status and file paths
        """
        try:
            # STEP 1: Extract context from JSON
            context = self._extract_context(structured_data, booking_url)

            # STEP 2: Use default configuration (simplified - not asking questions in this automation)
            config = self._get_default_config(booking_url)

            # STEP 3: Build app with Claude Opus 4.6
            print(f"\n🤖 Calling Claude Opus 4.6 to build health assessment app...")
            html_content = self._call_opus_4_6(context, config)

            # STEP 4: Validate and save output
            app_dir = Path(self.run_dir) / "app"
            app_dir.mkdir(parents=True, exist_ok=True)

            html_path = app_dir / "health-assessment.html"
            readme_path = app_dir / "README.md"
            config_path = app_dir / "config.json"

            # Save raw HTML first (before validation)
            raw_html_path = app_dir / "health-assessment-raw.html"
            raw_html_path.write_text(html_content, encoding='utf-8')
            print(f"📄 Raw HTML saved: {raw_html_path} ({len(html_content)} chars)")

            # Validate HTML
            validation_result = self._validate_html(html_content)
            if not validation_result:
                raise ValueError(f"Generated HTML failed validation. Raw HTML saved to {raw_html_path}")

            # Save files
            html_path.write_text(html_content, encoding='utf-8')

            # Generate README
            readme_content = self._generate_readme(context, datetime.now().isoformat())
            readme_path.write_text(readme_content, encoding='utf-8')

            # Save config
            config_data = {
                "app_version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "company_name": context["company_name"],
                "booking_url": booking_url,
                "brand_colors": context["brand_colors"],
                "assessment_depth": config["assessment_depth"],
                "redirect_method": config["redirect_method"],
                "payload_char_limit": config["payload_char_limit"],
                "required_fields": config["required_fields"],
                "sections_included": ["landing", "assessment", "results"]
            }
            config_path.write_text(json.dumps(config_data, indent=2), encoding='utf-8')

            file_size_kb = round(len(html_content) / 1024, 2)

            return {
                "status": "success",
                "html_path": str(html_path),
                "readme_path": str(readme_path),
                "config_path": str(config_path),
                "file_size_kb": file_size_kb,
                "validation_passed": True,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _extract_context(self, structured_data, booking_url):
        """Extract context from structured JSON data"""

        # Extract practice info
        practice = structured_data.get("practice", {})
        company_name = (
            practice.get("brand_name", {}).get("value") or
            practice.get("legal_name", {}).get("value") or
            "Healthcare Practice"
        )
        specialty = practice.get("specialty", {}).get("value", "Integrative Medicine")

        # Extract services
        services = [
            s.get("name", {}).get("value")
            for s in structured_data.get("services", [])
            if s.get("name", {}).get("value")
        ]

        # Extract conditions
        conditions = [
            c.get("name", {}).get("value")
            for c in structured_data.get("conditions", [])
            if c.get("name", {}).get("value")
        ]

        # Extract providers
        providers = []
        for p in structured_data.get("providers", []):
            provider = {
                "name": p.get("name", {}).get("value", ""),
                "credentials": p.get("credentials", {}).get("value", ""),
                "specialty": p.get("specialty", {}).get("value", "")
            }
            if provider["name"]:
                providers.append(provider)

        # Extract ideal patient info
        ideal_patient_data = structured_data.get("ideal_patient", {})
        ideal_patient = ideal_patient_data.get("who_they_serve", {}).get("value", "")
        exclusions = ideal_patient_data.get("exclusions", {}).get("value", "")

        # Extract clinical approach
        clinical_approach_data = structured_data.get("clinical_approach", {})
        clinical_approach = clinical_approach_data.get("differentiators", {}).get("value", "")

        # Extract patient journey
        patient_journey_data = structured_data.get("patient_journey", {})
        patient_journey = patient_journey_data.get("new_patient_steps", {}).get("value", "")

        # Brand colors (default to RESTORE Center colors as example)
        brand_colors = {
            "primary": "#667eea",
            "secondary": "#764ba2",
            "accent": "#f093fb",
            "text": "#1a202c",
            "background": "#ffffff"
        }

        return {
            "company_name": company_name,
            "specialty": specialty,
            "services": services,
            "conditions": conditions,
            "providers": providers,
            "ideal_patient": ideal_patient,
            "clinical_approach": clinical_approach,
            "patient_journey": patient_journey,
            "exclusions": exclusions,
            "brand_colors": brand_colors,
            "booking_url": booking_url
        }

    def _get_default_config(self, booking_url):
        """Get default configuration for automated builds"""
        return {
            "booking_objective": "New patient consultation",
            "location_constraints": "None",
            "social_proof": "No",
            "assessment_depth": "Standard (10-12 min, ~25 questions)",
            "required_fields": ["name", "email", "phone"],
            "redirect_method": "Copy-to-clipboard + redirect",
            "payload_fields": ["name", "email", "phone", "primary_concern"],
            "payload_char_limit": 500,
            "end_state_behavior": "All of the above",
            "booking_routing": "One link for all services",
            "legal_text": "Use standard healthcare disclaimer",
            "booking_url": booking_url
        }

    def _call_opus_4_6(self, context, config):
        """
        Call Claude Opus 4.6 via Anthropic API (or OpenRouter as fallback) to build the app
        """

        # Try Anthropic API first, fallback to OpenRouter
        if self.anthropic_key:
            return self._call_anthropic_api(context, config)
        elif self.openrouter_key:
            return self._call_openrouter_api(context, config)
        else:
            raise ValueError("No API key available for Claude Opus 4.6")

    def _build_prompt(self, context, config):
        """Build the detailed prompt for Claude Opus 4.6"""
        return f"""You are a senior product designer + conversion copywriter + front-end engineer + healthcare-compliance-minded UX writer.

PRIMARY OBJECTIVE
Using ONLY the context and content I provide (no assumptions, no inference), produce a "Dream 100" demo experience that combines:
1) A premium patient-acquisition landing page for {context['company_name']}, and
2) An extremely detailed, high-substance Health Assessment (intake + guided triage-style),

that culminates in a redirect to a booking link carrying a concise, safe summary of user responses suitable for scheduling staff.

This prompt is optimized for **accuracy, constraint-discipline, and repeatable output quality**.

---

NON-NEGOTIABLE RULES
- Use ONLY information explicitly provided in the pasted context and content.
- Do NOT infer demographics, conditions, compliance rules, tone, or logic.
- All code must be in ONE self-contained HTML file (embedded CSS + JS).
- No external libraries, assets, analytics, APIs, or network calls.
- Client-side only; in-memory data only (optional copy/print allowed).
- Medical responsibility enforced: no diagnosis, no guarantees, no treatment claims.
- USE BRAND COLORS: {json.dumps(context['brand_colors'])}
- ENSURE ALL MULTI-SELECT BUTTONS ACTUALLY ALLOW MULTIPLE SELECTABLE ITEMS (AND ALLOW USER TO DE-SELECT)

---

CONTEXT (FROM JSON):
{json.dumps({
    "company_name": context['company_name'],
    "specialty": context['specialty'],
    "services": context['services'],
    "conditions": context['conditions'],
    "providers": context['providers'],
    "ideal_patient": context['ideal_patient'],
    "clinical_approach": context['clinical_approach'],
    "patient_journey": context['patient_journey'],
    "exclusions": context['exclusions']
}, indent=2)}

USER CONFIGURATION:
{json.dumps({
    "booking_objective": config['booking_objective'],
    "location_constraints": config['location_constraints'],
    "social_proof": config['social_proof'],
    "assessment_depth": config['assessment_depth'],
    "required_fields": config['required_fields'],
    "redirect_method": config['redirect_method'],
    "payload_fields": config['payload_fields'],
    "payload_char_limit": config['payload_char_limit'],
    "end_state_behavior": config['end_state_behavior'],
    "booking_routing": config['booking_routing'],
    "legal_text": config['legal_text'],
    "booking_url": config['booking_url']
}, indent=2)}

---

OUTPUT DISCIPLINE
When building:
- Mobile-first, responsive, WCAG-aware accessibility.
- All selectable UI controls MUST show unmistakable selected + focus states
  (high-contrast, persistent, keyboard-accessible).
- Use fieldset/legend, labels, aria where appropriate.
- Clear disclaimers ("Not medical advice," emergency guidance, etc.).
- Red-flag logic ONLY if explicitly provided in content.

---

BUILD SPECIFICATION

1) Patient Acquisition Landing Page
- Clear value prop tied strictly to offerings content
- "How it works" flow
- Offerings cards (benefit-led, compliant)
- Trust & safety section
- Sticky mobile CTA

2) Extremely Detailed Health Assessment
- Multi-step flow with progress + time estimate
- Sections derived ONLY from provided content
- Inputs: chips/toggles, sliders, checklists, text, dates, long-form narrative
- Strong microcopy without medical claims
- Review & edit step

3) Results & Booking Transition
- Concise, human-readable Booking Summary
- Optional JSON view
- Copy Summary action
- Redirect to booking link with payload
- Safety disclaimers and emergency guidance

---

FINAL OUTPUT
Return ONLY: Complete single-file HTML/JS in ONE code block

No explanations. No filler. No assumptions."""

    def _call_anthropic_api(self, context, config):
        """Call Anthropic API directly with Claude Opus 4.6"""
        prompt = self._build_prompt(context, config)

        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-opus-4-6",
                    "max_tokens": 16000,
                    "temperature": 0.3,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                },
                timeout=300  # 5 minute timeout
            )

            if response.status_code != 200:
                raise ValueError(f"Anthropic API error: {response.status_code} - {response.text}")

            result = response.json()

            # Extract HTML from response
            html_content = result["content"][0]["text"]

            # Remove markdown code fences if present
            if "```html" in html_content:
                html_content = html_content.split("```html")[1].split("```")[0].strip()
            elif "```" in html_content:
                html_content = html_content.split("```")[1].split("```")[0].strip()

            return html_content

        except requests.exceptions.Timeout:
            raise ValueError("Anthropic API request timed out after 5 minutes")
        except Exception as e:
            # If Anthropic API fails and we have OpenRouter, try that
            if self.openrouter_key:
                print(f"⚠️  Anthropic API failed ({str(e)}), trying OpenRouter...")
                return self._call_openrouter_api(context, config)
            raise ValueError(f"Failed to call Anthropic API: {str(e)}")

    def _call_openrouter_api(self, context, config):
        """Call OpenRouter API with Claude Opus 4.6"""
        prompt = self._build_prompt(context, config)

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://aiaa-agentic-os.local",
                    "X-Title": "AIAA D100 App Builder"
                },
                json={
                    "model": "anthropic/claude-opus-4-6",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 32000  # Increased for full HTML output
                },
                timeout=300  # 5 minute timeout
            )

            if response.status_code != 200:
                raise ValueError(f"OpenRouter API error: {response.status_code} - {response.text}")

            result = response.json()

            # Extract HTML from response
            html_content = result["choices"][0]["message"]["content"]

            # Remove markdown code fences if present
            if "```html" in html_content:
                html_content = html_content.split("```html")[1].split("```")[0].strip()
            elif "```" in html_content:
                html_content = html_content.split("```")[1].split("```")[0].strip()

            return html_content

        except requests.exceptions.Timeout:
            raise ValueError("OpenRouter API request timed out after 5 minutes")
        except Exception as e:
            raise ValueError(f"Failed to call OpenRouter API: {str(e)}")

    def _validate_html(self, html_content):
        """Validate generated HTML"""
        checks = [
            "<!DOCTYPE html>" in html_content or "<!doctype html>" in html_content,
            "<html" in html_content.lower(),
            "</html>" in html_content.lower(),
            "<head" in html_content.lower(),
            "<body" in html_content.lower(),
            len(html_content) > 10000  # Should be substantial
        ]

        # Check for external dependencies (should have none)
        has_external_deps = (
            '<script src="http' in html_content or
            '<link href="http' in html_content or
            '<img src="http' in html_content
        )

        return all(checks) and not has_external_deps

    def _generate_readme(self, context, timestamp):
        """Generate README for app deployment"""
        return f"""# Health Assessment App - Deployment Guide

## File
`health-assessment.html`

## How to Deploy

### Option 1: Direct Hosting
1. Upload `health-assessment.html` to your web host
2. Access via: `https://yourdomain.com/health-assessment.html`

### Option 2: Embed on Existing Page
1. Copy the HTML content
2. Paste into your page builder (WordPress, Webflow, etc.)
3. Ensure no conflicting CSS/JS

### Option 3: Standalone App
1. Host on Vercel/Netlify for free:
   - Drag and drop file to Vercel
   - Get instant URL

## Testing
- Test on mobile (required)
- Test all multi-select buttons
- Test booking redirect with sample data
- Verify brand colors display correctly

## Customization
Edit these sections in the HTML:
- CSS variables: Brand colors
- Assessment questions
- Booking URL

## Details
- Company: {context['company_name']}
- Specialty: {context['specialty']}
- Services: {len(context['services'])} services
- Conditions: {len(context['conditions'])} conditions
- Providers: {len(context['providers'])} providers

## Support
Generated by AIAA Dream 100 Automation v1.0
{timestamp}
"""
