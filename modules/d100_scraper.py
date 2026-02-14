"""
Dream 100 Scraper Module
Handles website scraping and JSON conversion
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class D100Scraper:
    """Website scraper using Perplexity Sonar + Claude Sonnet"""

    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.scrape_dir = self.run_dir / "scrape_data"
        self.scrape_dir.mkdir(exist_ok=True)

        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not self.openrouter_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env")

    def scrape(self, website_url, context=""):
        """
        Scrape website using Perplexity Sonar

        Returns:
            dict: {
                "success": bool,
                "raw_markdown": str,
                "raw_path": Path,
                "pages_crawled": int,
                "error": str (if failed)
            }
        """
        prompt = self._build_scrape_prompt(website_url, context)

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://aiaa-agentic-os.local",
                    "X-Title": "AIAA Dream 100 Scraper"
                },
                json={
                    "model": "perplexity/sonar",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 8000
                },
                timeout=120
            )

            response.raise_for_status()
            data = response.json()

            raw_markdown = data["choices"][0]["message"]["content"]

            # Save raw markdown
            raw_path = self.scrape_dir / "raw_scrape.md"
            with open(raw_path, "w") as f:
                f.write(raw_markdown)

            # Estimate pages crawled (rough heuristic)
            pages_crawled = raw_markdown.count("Source URL:") or raw_markdown.count("URL:") or 10

            return {
                "success": True,
                "raw_markdown": raw_markdown,
                "raw_path": raw_path,
                "pages_crawled": pages_crawled
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def convert_to_json(self, raw_markdown):
        """
        Convert raw markdown to structured JSON using Claude Sonnet 3.7
        """
        prompt = self._build_json_conversion_prompt(raw_markdown)

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://aiaa-agentic-os.local",
                    "X-Title": "AIAA Dream 100 JSON Converter"
                },
                json={
                    "model": "anthropic/claude-3.5-sonnet",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 16000
                },
                timeout=180
            )

            response.raise_for_status()
            data = response.json()

            json_output = data["choices"][0]["message"]["content"]

            # Clean any markdown code fences if present
            json_output = json_output.strip()
            if json_output.startswith("```json"):
                json_output = json_output[7:]
            if json_output.startswith("```"):
                json_output = json_output[3:]
            if json_output.endswith("```"):
                json_output = json_output[:-3]
            json_output = json_output.strip()

            # Parse to validate JSON
            structured_data = json.loads(json_output)

            # Save structured JSON
            json_path = self.scrape_dir / "structured_data.json"
            with open(json_path, "w") as f:
                json.dump(structured_data, f, indent=2)

            return {
                "success": True,
                "json_path": json_path,
                "raw_path": self.scrape_dir / "raw_scrape.md",
                "services_count": len(structured_data.get("services", [])),
                "conditions_count": len(structured_data.get("conditions", []))
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _build_scrape_prompt(self, website_url, context):
        """Build the Perplexity scrape prompt"""
        return f"""You are a healthcare practice intelligence analyst specializing in extracting structured, source-grounded website data for marketing automation, Dream 100 outreach, ICP/RAG building, SEO, and paid media.

MISSION
Given a healthcare practice website, crawl it like a human would (live pages only) and extract ONLY what is explicitly stated on the site. Your output must be high-coverage, deeply sourced, and automation-ready.

NON-NEGOTIABLE RULES
1) Use the LIVE website (no cached snippets, no memory, no assumptions).
2) Extract ONLY what you can cite from the site. If missing/unclear: write "NOT FOUND ON SITE".
3) Go deep: don't stop at nav links. Follow in-page links, footer links, "Learn more" CTAs, and related service/condition/provider subpages.
4) Capture exact wording for claims that affect compliance (outcomes, guarantees, "best", "top", "cure", etc.).
5) Always include SOURCE URLs for each extracted item.
6) Visit AT LEAST these (if they exist): Homepage, Services, Conditions We Treat, Team/Providers, About.

INPUT
Website URL: {website_url}
Optional Context: {context}
Output Mode: STANDARD
Max pages to open: 50

OUTPUT FORMAT
Return Markdown in this structure with SOURCE URLs:

## 1. PRACTICE IDENTIFICATION
- Legal business name:
- Brand name:
- Tagline:
- Specialty:
- Primary location:
- Phone:
- Email:
- Booking URL:
SOURCES: [URLs]

## 2. SERVICES & TREATMENTS
List all services/treatments offered.
SOURCES: [URLs]

## 3. CONDITIONS TREATED
List all conditions/symptoms mentioned.
SOURCES: [URLs]

## 4. PROVIDERS
For each provider:
- Name:
- Credentials:
- Specialty:
SOURCES: [URLs]

## 5. CLINICAL APPROACH
- How they're different:
- Treatment philosophy:
SOURCES: [URLs]

## 6. PATIENT JOURNEY
- First step:
- New patient process:
SOURCES: [URLs]

## 7. PRICING & INSURANCE
- Pricing info:
- Insurance accepted:
SOURCES: [URLs]

Extract as much detail as possible with source citations."""

    def _build_json_conversion_prompt(self, raw_markdown):
        """Build the Claude Sonnet JSON conversion prompt with strict schema"""
        return f"""You are a healthcare practice intelligence crawler designed for AUTOMATION-FIRST pipelines.

ABSOLUTE OUTPUT ENFORCEMENT (NON-NEGOTIABLE)
- You MUST output a SINGLE JSON object.
- You MUST output JSON ONLY (no Markdown, no prose, no explanations).
- Your JSON MUST EXACTLY match the schema below:
  - Same keys
  - Same nesting
  - Same casing
  - Same data types
  - Same arrays (present even if empty)
- You are NOT allowed to:
  - Rename fields
  - Add fields
  - Remove fields
  - Reorder fields
- If data is missing, unclear, inaccessible, or contradictory:
  - Set the field value(s) to null
  - Log the issue in the `missing[]` array
- Every extracted field MUST include:
  - value
  - verbatim (exact on-site text where available)
  - sources (array of live URLs)
  - confidence (high | medium | low)

FAILURE CONDITION
If you cannot comply with the schema exactly, you MUST still output the schema with nulls populated and log failures in `missing[]`. Do NOT refuse. Do NOT explain.

INPUT (RAW SCRAPE MARKDOWN):
{raw_markdown}

OUTPUT SCHEMA:
{{
  "run_metadata": {{
    "run_id": "string (UUID)",
    "website_url": "string",
    "started_at": "ISO-8601 timestamp",
    "finished_at": "ISO-8601 timestamp",
    "crawl_depth": "number",
    "pages_visited": ["array of URLs"]
  }},
  "practice": {{
    "legal_name": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "brand_name": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "tagline": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "specialty": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "practice_type": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "ownership": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }}
  }},
  "locations": [
    {{
      "type": "primary|additional",
      "address": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "phone": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "email": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "hours": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "accessibility": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }}
  ],
  "contact": {{
    "contact_form_url": {{
      "value": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "booking_url": {{
      "value": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "patient_portal_url": {{
      "value": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }}
  }},
  "providers": [
    {{
      "name": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "role": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "credentials": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "specialty": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "conditions_treated": {{
        "value": ["array or null"],
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "services_performed": {{
        "value": ["array or null"],
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "education": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "certifications": {{
        "value": ["array or null"],
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "languages": {{
        "value": ["array or null"],
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "years_experience": {{
        "value": "number or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "bio_summary": {{
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "headshot_url": {{
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }}
  ],
  "services": [
    {{
      "name": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "category": {{
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "target_audience": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "deliverables": {{
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "cta": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }}
  ],
  "conditions": [
    {{
      "name": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "category": {{
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }}
  ],
  "ideal_patient": {{
    "who_they_serve": {{
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "demographics": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "situations": {{
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "exclusions": {{
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "referral_requirements": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }}
  }},
  "clinical_approach": {{
    "differentiators": {{
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "philosophy": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "diagnostic_methods": {{
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "technology": {{
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "modalities": {{
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "claims": {{
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }}
  }},
  "patient_journey": {{
    "first_step_cta": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "new_patient_steps": {{
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "discovery_call": {{
      "offered": "boolean",
      "description": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }},
    "intake_forms": {{
      "available": "boolean",
      "links": {{
        "value": ["array or null"],
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }},
    "consult_expectations": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "follow_up": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "memberships": {{
      "available": "boolean",
      "details": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }}
  }},
  "pricing": {{
    "transparency": "TRANSPARENT|PARTIAL|NONE",
    "prices": {{
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "insurance_accepted": {{
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "medicare_medicaid": {{
      "value": "string or null",
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "self_pay": {{
      "available": "boolean",
      "details": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }},
    "superbills": {{
      "available": "boolean",
      "details": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }},
    "payment_plans": {{
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "hsa_fsa": {{
      "available": "boolean",
      "details": {{
        "value": "string or null",
        "verbatim": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }}
  }},
  "trust_signals": {{
    "testimonials": {{
      "present": "boolean",
      "location": {{
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }},
      "themes": {{
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }},
    "case_studies": {{
      "present": "boolean",
      "urls": {{
        "value": ["array or null"],
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }},
    "awards": {{
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "associations": {{
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "research_citations": {{
      "present": "boolean",
      "urls": {{
        "value": ["array or null"],
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }},
    "disclaimers": {{
      "present": "boolean",
      "verbatim": {{
        "value": "string or null",
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }}
  }},
  "seo_intel": {{
    "primary_keywords": {{
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "location_modifiers": {{
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "conversion_ctas": {{
      "value": ["array or null"],
      "verbatim": "string or null",
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "lead_magnets": {{
      "present": "boolean",
      "urls": {{
        "value": ["array or null"],
        "sources": ["array"],
        "confidence": "high|medium|low"
      }}
    }},
    "forms": {{
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    }},
    "tech_stack": {{
      "value": ["array or null"],
      "sources": ["array"],
      "confidence": "high|medium|low"
    }}
  }},
  "missing": [
    {{
      "field": "string (JSON path)",
      "reason": "string (why missing/unclear/contradictory)",
      "impact": "critical|moderate|minor"
    }}
  ]
}}

BEGIN CONVERSION. OUTPUT JSON ONLY."""
