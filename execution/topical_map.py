#!/usr/bin/env python3
"""
Topical Map Generator — AIAA-Agentic-OS
Version: 1.0 | 2026-03-12

Generates a complete SEO topical authority map using DataForSEO (real keyword data)
+ Claude Opus (8-section map). Outputs: CSV, JSON, Markdown, static HTML mindmap.

Usage:
    python3 execution/topical_map.py --topic "Work-Life Balance" --audience "Remote workers" --goal "Newsletter signups"
    python3 execution/topical_map.py --topic "Functional Medicine" --audience "Health adults 35-55" --goal "Patient consults" --competitor functionalmedicine.org
    python3 execution/topical_map.py --from-json output/topical_maps/work-life-balance_20260312_150000/topical_map.json
    python3 execution/topical_map.py --enrich output/topical_maps/work-life-balance_20260312_150000/topical_map.json
"""

import argparse
import base64
import csv
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# ─── Project root & output dir ───────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_BASE = PROJECT_ROOT / "output" / "topical_maps"

CLAUDE_MODEL = "claude-opus-4-6"
MAX_TOKENS = 16000


# ─── .env loader (same pattern as d100_v3_runner.py) ─────────────────────────
def load_env() -> dict:
    env = {}
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip()
    for k in ("ANTHROPIC_API_KEY", "DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


# ─── DataForSEO client ────────────────────────────────────────────────────────
class DataForSEOClient:
    BASE_URL = "https://api.dataforseo.com"

    def __init__(self, login: str, password: str):
        creds = base64.b64encode(f"{login}:{password}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json",
        }

    def _post(self, endpoint: str, payload: list) -> dict:
        url = f"{self.BASE_URL}{endpoint}"
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            return {"_error": f"HTTP {e.code}: {body[:300]}"}
        except Exception as e:
            return {"_error": str(e)}

    def get_related_keywords(self, keyword: str, location: str = "United States", limit: int = 100) -> list:
        """Get related keywords with volume + KD for a seed keyword."""
        result = self._post("/v3/dataforseo_labs/google/related_keywords/live", [{
            "keyword": keyword,
            "language_name": "English",
            "location_name": location,
            "limit": limit,
            "include_seed_keyword": True,
        }])
        if "_error" in result:
            print(f"  [DataForSEO] Related keywords error: {result['_error']}")
            return []

        keywords = []
        try:
            items = result["tasks"][0]["result"][0]["items"]
            for item in items:
                kw_data = item.get("keyword_data", {})
                kw_info = kw_data.get("keyword_info", {})
                kw_props = kw_data.get("keyword_properties", {})
                intent_info = kw_data.get("search_intent_info", {})
                keywords.append({
                    "keyword": kw_data.get("keyword", ""),
                    "volume": kw_info.get("search_volume") or 0,
                    "kd": kw_props.get("keyword_difficulty") or 0,
                    "cpc": kw_info.get("cpc") or 0,
                    "intent": intent_info.get("main_intent", "informational"),
                })
        except (KeyError, IndexError, TypeError) as e:
            print(f"  [DataForSEO] Parse warning (related_keywords): {e}")
        return keywords

    def get_competitor_keywords(self, domain: str, location: str = "United States", limit: int = 100) -> list:
        """Get top ranking keywords for a competitor domain."""
        result = self._post("/v3/dataforseo_labs/google/ranked_keywords/live", [{
            "target": domain,
            "language_name": "English",
            "location_name": location,
            "limit": limit,
            "order_by": ["ranked_serp_element.serp_item.rank_absolute,asc"],
        }])
        if "_error" in result:
            print(f"  [DataForSEO] Competitor keywords error: {result['_error']}")
            return []

        keywords = []
        try:
            items = result["tasks"][0]["result"][0]["items"]
            for item in items:
                kw_data = item.get("keyword_data", {})
                kw_info = kw_data.get("keyword_info", {})
                serp_item = item.get("ranked_serp_element", {}).get("serp_item", {})
                keywords.append({
                    "keyword": kw_data.get("keyword", ""),
                    "volume": kw_info.get("search_volume") or 0,
                    "rank": serp_item.get("rank_absolute") or 0,
                    "url": serp_item.get("url", ""),
                })
        except (KeyError, IndexError, TypeError) as e:
            print(f"  [DataForSEO] Parse warning (competitor_keywords): {e}")
        return keywords

    def enrich_keywords(self, keywords: list, location: str = "United States") -> list:
        """Refresh search volume + KD for a list of keyword strings."""
        kw_strings = [k["keyword"] if isinstance(k, dict) else k for k in keywords[:700]]
        # DataForSEO bulk search volume supports up to 700 per call
        result = self._post("/v3/keywords_data/google_ads/search_volume/live", [{
            "keywords": kw_strings,
            "language_name": "English",
            "location_name": location,
        }])
        if "_error" in result:
            print(f"  [DataForSEO] Enrich error: {result['_error']}")
            return keywords

        enriched_map = {}
        try:
            items = result["tasks"][0]["result"]
            for item in items:
                enriched_map[item.get("keyword", "").lower()] = {
                    "volume": item.get("search_volume") or 0,
                    "cpc": item.get("cpc") or 0,
                }
        except (KeyError, IndexError, TypeError) as e:
            print(f"  [DataForSEO] Parse warning (enrich): {e}")

        enriched = []
        for kw in keywords:
            if isinstance(kw, dict):
                lookup = kw.get("keyword", "").lower()
                if lookup in enriched_map:
                    kw["volume"] = enriched_map[lookup]["volume"]
                    kw["cpc"] = enriched_map[lookup]["cpc"]
                    kw.pop("estimated", None)
                enriched.append(kw)
        return enriched


# ─── Claude client ─────────────────────────────────────────────────────────────
def call_claude(api_key: str, prompt: str, system_prompt: str = "") -> str:
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        payload["system"] = system_prompt
    data = json.dumps(payload).encode()
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            result = json.loads(resp.read())
            return result["content"][0]["text"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Claude API error {e.code}: {e.read().decode()[:500]}")


# ─── Prompt builder ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a world-class SEO strategist and content architect with 10+ years building
7-figure content sites. You create comprehensive topical authority maps that rank and convert.
Core principles you always apply:
- Topic drives the keyword — never keyword drives the topic
- Every piece of content must have a conversion path
- Internal linking is the primary ranking mechanism, not backlinks
- Funnel awareness: map every cluster to ToFu / MoFu / BoFu
- Compete with depth, not breadth — own fewer topics completely
- The Prague strategy: commercial pages first, then destination content, then editorial"""


def build_prompt(topic: str, audience: str, goal: str, keyword_data: list,
                 competitor_keywords: list, existing_urls: list, competitor_domain: str) -> str:

    # Format keyword data for prompt injection
    if keyword_data:
        kw_sorted = sorted(keyword_data, key=lambda x: x.get("volume", 0), reverse=True)[:50]
        kw_lines = "\n".join(
            f"  - {kw['keyword']}: vol={kw.get('volume', '?'):,}, KD={kw.get('kd', '?')}, intent={kw.get('intent', '?')}"
            for kw in kw_sorted if kw.get("keyword")
        )
        keyword_section = f"\n**Real DataForSEO Keyword Data (top 50 by volume):**\n{kw_lines}\n"
    else:
        keyword_section = "\n**Keyword Data:** Not available — use realistic estimates for the niche.\n"

    competitor_section = ""
    if competitor_keywords and competitor_domain:
        comp_top = sorted(competitor_keywords, key=lambda x: x.get("volume", 0), reverse=True)[:30]
        comp_lines = "\n".join(
            f"  - {kw['keyword']} (vol={kw.get('volume', '?'):,}, rank=#{kw.get('rank', '?')})"
            for kw in comp_top if kw.get("keyword")
        )
        competitor_section = f"\n**Competitor Domain:** {competitor_domain}\n**Their Top Keywords:**\n{comp_lines}\nInclude `competitor_gaps` analysis — opportunities they own + blue ocean topics they miss.\n"

    urls_section = ""
    if existing_urls:
        urls_display = "\n".join(f"  - {u}" for u in existing_urls[:50])
        urls_section = f"\n**Existing URLs to Restructure:**\n{urls_display}\nMap these existing URLs to pillars/clusters. Flag any orphan content.\n"

    prompt = f"""Build a complete SEO topical authority map.

## INPUTS
- **Topic:** {topic}
- **Target Audience:** {audience}
- **Business Goal / Conversion:** {goal}
{keyword_section}{competitor_section}{urls_section}

## OUTPUT REQUIREMENTS
Return ONLY valid JSON. No markdown fences. No explanation text. No comments.

Use this exact schema:

{{
  "meta": {{
    "topic": "{topic}",
    "audience": "{audience}",
    "goal": "{goal}",
    "generated_at": "ISO timestamp",
    "total_pillars": 0,
    "total_clusters": 0,
    "total_articles": 0,
    "estimated_total_monthly_volume": 0
  }},
  "pillars": [
    {{
      "title": "Pillar Page Title",
      "type": "informational",
      "funnel_stage": "tofu",
      "intent": "informational",
      "intention": "Core problem this pillar solves",
      "url_slug": "pillar-keyword",
      "target_keyword": "main keyword",
      "estimated_volume": 5000,
      "estimated_kd": 45,
      "clusters": [
        {{
          "title": "Cluster Title",
          "intention": "What user problem this cluster solves",
          "target_keyword": "cluster keyword",
          "estimated_volume": 1200,
          "estimated_kd": 35,
          "funnel_stage": "tofu",
          "content_format": "guide",
          "articles": [
            {{
              "title": "Article Title",
              "target_keyword": "article keyword",
              "estimated_volume": 400,
              "estimated_kd": 28,
              "content_format": "listicle"
            }}
          ]
        }}
      ]
    }}
  ],
  "tools_resources": [
    {{
      "name": "Tool Name",
      "type": "Calculator",
      "intention": "What problem it solves for the user",
      "conversion_potential": "high",
      "implementation": "How to build it",
      "complexity": "low"
    }}
  ],
  "editorial_content": [
    {{
      "title": "Article Title",
      "angle": "Unique perspective",
      "target_persona": "Who this is for",
      "value": "Why this gets shared/linked",
      "social_hook": "The angle that makes it viral",
      "content_format": "data study"
    }}
  ],
  "programmatic_seo": [
    {{
      "pattern": "[Variable A] + [Variable B]",
      "variables": ["Variable A options", "Variable B options"],
      "example_pages": ["Example page 1", "Example page 2"],
      "estimated_page_count": 500,
      "user_scenarios": "Who searches this and why",
      "implementation": "How to build these pages",
      "difficulty": "low"
    }}
  ],
  "internal_links": [
    {{
      "source_page": "Source page title",
      "target_page": "Target page title",
      "anchor_text": "Suggested anchor text",
      "context": "Where in source page to place this link",
      "priority": "critical"
    }}
  ],
  "publishing_calendar": {{
    "phase_1_quick_wins": [
      {{
        "title": "Article title",
        "keyword": "target keyword",
        "volume": 800,
        "kd": 22,
        "reason": "Why this is a quick win",
        "type": "cluster"
      }}
    ],
    "phase_2_authority_builders": [
      {{
        "title": "Pillar page title",
        "keyword": "target keyword",
        "volume": 5000,
        "kd": 55,
        "reason": "Why this builds authority",
        "type": "pillar"
      }}
    ],
    "phase_3_programmatic_scale": [
      {{
        "pattern": "Programmatic pattern",
        "estimated_pages": 200,
        "reason": "Why this scales"
      }}
    ],
    "phase_4_editorial_leadership": [
      {{
        "title": "Editorial piece title",
        "angle": "Unique angle",
        "backlink_potential": "Why this earns links",
        "reason": "Strategic value"
      }}
    ]
  }},
  "conversion_paths": [
    {{
      "pillar": "Pillar page title",
      "cluster": "Cluster title (or 'all clusters')",
      "cta_text": "Button/link text",
      "destination": "Where the CTA goes",
      "funnel_stage": "mofu"
    }}
  ],
  "competitor_gaps": {{
    "opportunities": [
      {{
        "topic": "Topic they rank for",
        "competitor_keywords": ["kw1", "kw2"],
        "why_you_can_win": "Your competitive advantage here"
      }}
    ],
    "blue_ocean": [
      {{
        "topic": "Topic they miss",
        "angle": "How to own it",
        "why_untapped": "Why competitor ignores this"
      }}
    ]
  }},
  "post_generation_action_plan": {{
    "immediate_actions": [
      "Action 1 — specific and actionable",
      "Action 2"
    ],
    "validation_steps": [
      "Validation step 1",
      "Validation step 2"
    ],
    "phase_1_launch": [
      "Launch step 1",
      "Launch step 2"
    ],
    "ongoing_maintenance": [
      "Monthly: check GSC for impressions on pillar keywords",
      "Quarterly: run --enrich to refresh keyword data"
    ],
    "update_triggers": [
      "When to expand or update the map"
    ]
  }}
}}

## REQUIREMENTS (non-negotiable):
- **7-12 PILLARS**: 4-5 informational (ToFu-heavy), 3-4 commercial/transactional (BoFu-heavy)
- **4-7 CLUSTERS per pillar**: Each solving a distinct sub-problem. No overlap.
- **3-5 ARTICLES per cluster**
- **3-5 TOOLS**: High conversion potential. Practical to build.
- **4-6 EDITORIAL pieces**: Thought leadership. Backlink bait. Shareable angles.
- **8-12 PROGRAMMATIC patterns**: Data-driven. Scalable. Low per-page effort.
- **15-25 INTERNAL LINKS**: Contextual, within body copy. Not sidebar widgets. Mark critical ones.
- **All 4 PUBLISHING PHASES** must be populated
- **CONVERSION PATHS** for every commercial pillar and cluster
- **POST_GENERATION_ACTION_PLAN** must be specific — no generic advice
- Use REAL keyword volumes from the DataForSEO data above where keywords match your pillars
- For keywords not in the data, generate realistic estimates based on niche patterns
- content_format options: guide, listicle, comparison, faq, tool, programmatic, case_study, data_study, interview
- funnel_stage options: tofu, mofu, bofu
- type options: informational, commercial
- intent options: informational, commercial, transactional, navigational
- difficulty options: low, medium, high
- conversion_potential options: low, medium, high
- priority options: critical, high, medium
"""
    return prompt


# ─── Output formatters ────────────────────────────────────────────────────────

def format_json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_csv(data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    def row(*cells):
        writer.writerow(list(cells))

    def blank():
        writer.writerow([])

    meta = data.get("meta", {})
    row("TOPICAL MAP:", meta.get("topic", ""), f"Generated: {meta.get('generated_at', '')}")
    row("Audience:", meta.get("audience", ""))
    row("Goal:", meta.get("goal", ""))
    row(f"Pillars: {meta.get('total_pillars', 0)}", f"Clusters: {meta.get('total_clusters', 0)}",
        f"Articles: {meta.get('total_articles', 0)}", f"Est. Monthly Volume: {meta.get('estimated_total_monthly_volume', 0):,}")
    blank()

    # ── Section 1: Main Pillar Structure ──────────────────────────────────────
    row("SECTION 1: MAIN PILLAR STRUCTURE")
    row("Pillar Title", "Pillar Type", "Funnel Stage", "Intent", "Pillar Intention",
        "URL Slug", "Target Keyword", "Est. Volume", "Est. KD",
        "Cluster Title", "Cluster Intention", "Cluster Keyword", "Cluster Volume", "Cluster KD",
        "Cluster Format", "Article Title", "Article Keyword", "Article Volume", "Article KD")
    for pillar in data.get("pillars", []):
        clusters = pillar.get("clusters", [])
        if not clusters:
            row(pillar.get("title"), pillar.get("type"), pillar.get("funnel_stage"),
                pillar.get("intent"), pillar.get("intention"), pillar.get("url_slug"),
                pillar.get("target_keyword"), pillar.get("estimated_volume", ""),
                pillar.get("estimated_kd", ""))
            continue
        for ci, cluster in enumerate(clusters):
            articles = cluster.get("articles", [])
            if not articles:
                row(pillar.get("title") if ci == 0 else "",
                    pillar.get("type") if ci == 0 else "",
                    pillar.get("funnel_stage") if ci == 0 else "",
                    pillar.get("intent") if ci == 0 else "",
                    pillar.get("intention") if ci == 0 else "",
                    pillar.get("url_slug") if ci == 0 else "",
                    pillar.get("target_keyword") if ci == 0 else "",
                    pillar.get("estimated_volume", "") if ci == 0 else "",
                    pillar.get("estimated_kd", "") if ci == 0 else "",
                    cluster.get("title"), cluster.get("intention"),
                    cluster.get("target_keyword"), cluster.get("estimated_volume", ""),
                    cluster.get("estimated_kd", ""), cluster.get("content_format", ""))
                continue
            for ai, article in enumerate(articles):
                row(pillar.get("title") if ci == 0 and ai == 0 else "",
                    pillar.get("type") if ci == 0 and ai == 0 else "",
                    pillar.get("funnel_stage") if ci == 0 and ai == 0 else "",
                    pillar.get("intent") if ci == 0 and ai == 0 else "",
                    pillar.get("intention") if ci == 0 and ai == 0 else "",
                    pillar.get("url_slug") if ci == 0 and ai == 0 else "",
                    pillar.get("target_keyword") if ci == 0 and ai == 0 else "",
                    pillar.get("estimated_volume", "") if ci == 0 and ai == 0 else "",
                    pillar.get("estimated_kd", "") if ci == 0 and ai == 0 else "",
                    cluster.get("title") if ai == 0 else "",
                    cluster.get("intention") if ai == 0 else "",
                    cluster.get("target_keyword") if ai == 0 else "",
                    cluster.get("estimated_volume", "") if ai == 0 else "",
                    cluster.get("estimated_kd", "") if ai == 0 else "",
                    cluster.get("content_format", "") if ai == 0 else "",
                    article.get("title"), article.get("target_keyword"),
                    article.get("estimated_volume", ""), article.get("estimated_kd", ""))
    blank()

    # ── Section 2: Tools & Resources ─────────────────────────────────────────
    row("SECTION 2: TOOLS & FREE RESOURCES")
    row("Tool Name", "Type", "Conversion Potential", "Tool Intention", "Implementation", "Complexity")
    for tool in data.get("tools_resources", []):
        row(tool.get("name"), tool.get("type"), tool.get("conversion_potential"),
            tool.get("intention"), tool.get("implementation"), tool.get("complexity"))
    blank()

    # ── Section 3: Editorial Content ──────────────────────────────────────────
    row("SECTION 3: EDITORIAL CONTENT")
    row("Article Title", "Angle", "Target Persona", "Value Proposition", "Social Hook", "Format")
    for ed in data.get("editorial_content", []):
        row(ed.get("title"), ed.get("angle"), ed.get("target_persona"),
            ed.get("value"), ed.get("social_hook"), ed.get("content_format"))
    blank()

    # ── Section 4: Programmatic SEO ───────────────────────────────────────────
    row("SECTION 4: PROGRAMMATIC SEO OPPORTUNITIES")
    row("Pattern", "Variables", "Example Pages", "Est. Page Count", "User Scenarios", "Implementation", "Difficulty")
    for prog in data.get("programmatic_seo", []):
        row(prog.get("pattern"),
            " | ".join(prog.get("variables", [])),
            " | ".join(prog.get("example_pages", [])[:3]),
            prog.get("estimated_page_count"),
            prog.get("user_scenarios"),
            prog.get("implementation"),
            prog.get("difficulty"))
    blank()

    # ── Section 5: Internal Linking Blueprint ─────────────────────────────────
    row("SECTION 5: INTERNAL LINKING BLUEPRINT")
    row("Source Page", "Target Page", "Anchor Text", "Context (Where to Place)", "Priority")
    for link in data.get("internal_links", []):
        row(link.get("source_page"), link.get("target_page"),
            link.get("anchor_text"), link.get("context"), link.get("priority"))
    blank()

    # ── Section 6: Publishing Calendar ───────────────────────────────────────
    row("SECTION 6: PUBLISHING CALENDAR")

    row("PHASE 1 — QUICK WINS (Publish First: High Volume, Low KD, Bottom Funnel)")
    row("Title", "Keyword", "Volume", "KD", "Reason", "Type")
    for item in data.get("publishing_calendar", {}).get("phase_1_quick_wins", []):
        row(item.get("title"), item.get("keyword"), item.get("volume", ""),
            item.get("kd", ""), item.get("reason"), item.get("type"))
    blank()

    row("PHASE 2 — AUTHORITY BUILDERS (Pillar Pages + High-Value Clusters)")
    row("Title", "Keyword", "Volume", "KD", "Reason", "Type")
    for item in data.get("publishing_calendar", {}).get("phase_2_authority_builders", []):
        row(item.get("title"), item.get("keyword"), item.get("volume", ""),
            item.get("kd", ""), item.get("reason"), item.get("type"))
    blank()

    row("PHASE 3 — PROGRAMMATIC SCALE (High Page Count, Low Per-Page Effort)")
    row("Pattern", "Estimated Pages", "Reason")
    for item in data.get("publishing_calendar", {}).get("phase_3_programmatic_scale", []):
        row(item.get("pattern"), item.get("estimated_pages", ""), item.get("reason"))
    blank()

    row("PHASE 4 — EDITORIAL LEADERSHIP (Thought Leadership + Backlink Bait)")
    row("Title", "Angle", "Backlink Potential", "Reason")
    for item in data.get("publishing_calendar", {}).get("phase_4_editorial_leadership", []):
        row(item.get("title"), item.get("angle"),
            item.get("backlink_potential"), item.get("reason"))
    blank()

    # ── Section 7: Conversion Paths ───────────────────────────────────────────
    row("SECTION 7: CONVERSION PATHS")
    row("Pillar", "Cluster", "CTA Text", "Destination", "Funnel Stage")
    for cp in data.get("conversion_paths", []):
        row(cp.get("pillar"), cp.get("cluster"), cp.get("cta_text"),
            cp.get("destination"), cp.get("funnel_stage"))
    blank()

    # ── Section 8: Competitor Gaps (if present) ───────────────────────────────
    comp_gaps = data.get("competitor_gaps", {})
    opps = comp_gaps.get("opportunities", [])
    blue = comp_gaps.get("blue_ocean", [])
    if opps or blue:
        row("SECTION 8: COMPETITOR GAP ANALYSIS")
        if opps:
            row("OPPORTUNITIES (Topics competitor ranks for — you can compete)")
            row("Topic", "Competitor Keywords", "Why You Can Win")
            for opp in opps:
                row(opp.get("topic"),
                    " | ".join(opp.get("competitor_keywords", [])),
                    opp.get("why_you_can_win"))
            blank()
        if blue:
            row("BLUE OCEAN (Topics competitor ignores — you can own)")
            row("Topic", "Angle", "Why Untapped")
            for b in blue:
                row(b.get("topic"), b.get("angle"), b.get("why_untapped"))
            blank()

    # ── Section 9: Post-Generation Action Plan ────────────────────────────────
    plan = data.get("post_generation_action_plan", {})
    if plan:
        row("SECTION 9: POST-GENERATION ACTION PLAN")
        for section_key, section_label in [
            ("immediate_actions", "IMMEDIATE ACTIONS (Today)"),
            ("validation_steps", "VALIDATION STEPS (Before Writing)"),
            ("phase_1_launch", "PHASE 1 LAUNCH CHECKLIST"),
            ("ongoing_maintenance", "ONGOING MAINTENANCE"),
            ("update_triggers", "UPDATE TRIGGERS"),
        ]:
            items = plan.get(section_key, [])
            if items:
                row(section_label)
                for item in items:
                    row("", item)
                blank()

    return output.getvalue()


def format_markdown(data: dict) -> str:
    lines = []
    meta = data.get("meta", {})
    now = meta.get("generated_at", datetime.now().isoformat())

    lines.append(f"# Topical Authority Map: {meta.get('topic', 'Unknown Topic')}")
    lines.append(f"\n**Generated:** {now}  ")
    lines.append(f"**Audience:** {meta.get('audience', '')}  ")
    lines.append(f"**Goal:** {meta.get('goal', '')}  ")
    lines.append(f"**Pillars:** {meta.get('total_pillars', 0)} | **Clusters:** {meta.get('total_clusters', 0)} | **Articles:** {meta.get('total_articles', 0)} | **Est. Monthly Volume:** {meta.get('estimated_total_monthly_volume', 0):,}")

    lines.append("\n---\n")
    lines.append("## How to Use This Document\n")
    lines.append("1. **Review pillars** — do they match your business goals?")
    lines.append("2. **Validate keywords** — spot-check 10 keywords in DataForSEO/SEMrush")
    lines.append("3. **Start with Phase 1** from the Publishing Calendar — quick wins first")
    lines.append("4. **Assign writers** — use each pillar section below as a writer brief")
    lines.append("5. **Build conversion paths** before publishing editorial content")
    lines.append("6. **Add internal links** using the blueprint at the bottom\n")

    # ── Pillars (writer briefs) ───────────────────────────────────────────────
    lines.append("---\n")
    lines.append("## Content Pillars\n")

    for i, pillar in enumerate(data.get("pillars", []), 1):
        lines.append(f"### Pillar {i}: {pillar.get('title', '')}")
        lines.append(f"\n| Field | Value |")
        lines.append("| --- | --- |")
        lines.append(f"| **Type** | {pillar.get('type', '').title()} |")
        lines.append(f"| **Funnel Stage** | {pillar.get('funnel_stage', '').upper()} |")
        lines.append(f"| **Intent** | {pillar.get('intent', '').title()} |")
        lines.append(f"| **URL Slug** | `/{pillar.get('url_slug', '')}` |")
        lines.append(f"| **Target Keyword** | {pillar.get('target_keyword', '')} |")
        lines.append(f"| **Est. Volume** | {pillar.get('estimated_volume', 0):,}/mo |")
        lines.append(f"| **Est. KD** | {pillar.get('estimated_kd', 0)}/100 |")
        lines.append(f"| **Intention** | {pillar.get('intention', '')} |\n")

        # Meta title suggestions (3 variations)
        title = pillar.get("title", "")
        kw = pillar.get("target_keyword", "")
        lines.append("**Meta Title Suggestions:**")
        lines.append(f"1. {title}: The Complete Guide")
        lines.append(f"2. {kw.title()}: Everything You Need to Know ({datetime.now().year})")
        lines.append(f"3. The Ultimate {title} — Expert Guide\n")

        lines.append("**Content Clusters:**\n")
        for ci, cluster in enumerate(pillar.get("clusters", []), 1):
            kd = cluster.get("estimated_kd", 0)
            kd_indicator = "🟢" if kd <= 30 else "🟡" if kd <= 60 else "🔴"
            lines.append(f"#### Cluster {ci}: {cluster.get('title', '')}")
            lines.append(f"- **Keyword:** {cluster.get('target_keyword', '')} | **Volume:** {cluster.get('estimated_volume', 0):,}/mo | **KD:** {kd} {kd_indicator}")
            lines.append(f"- **Format:** {cluster.get('content_format', '').title()} | **Funnel:** {cluster.get('funnel_stage', '').upper()}")
            lines.append(f"- **Intention:** {cluster.get('intention', '')}")
            lines.append(f"\n  **Supporting Articles:**")
            for article in cluster.get("articles", []):
                lines.append(f"  - {article.get('title', '')} *(kw: {article.get('target_keyword', '')}, vol: {article.get('estimated_volume', 0):,}, KD: {article.get('estimated_kd', 0)})*")
            lines.append("")

        lines.append("---\n")

    # ── Tools & Resources ─────────────────────────────────────────────────────
    lines.append("## Tools & Free Resources\n")
    for tool in data.get("tools_resources", []):
        lines.append(f"### {tool.get('name', '')}")
        lines.append(f"- **Type:** {tool.get('type', '')} | **Conversion Potential:** {tool.get('conversion_potential', '').upper()} | **Complexity:** {tool.get('complexity', '').title()}")
        lines.append(f"- **Intention:** {tool.get('intention', '')}")
        lines.append(f"- **Implementation:** {tool.get('implementation', '')}\n")

    # ── Editorial Content ─────────────────────────────────────────────────────
    lines.append("## Editorial Content (Thought Leadership)\n")
    for ed in data.get("editorial_content", []):
        lines.append(f"### {ed.get('title', '')}")
        lines.append(f"- **Angle:** {ed.get('angle', '')}")
        lines.append(f"- **Persona:** {ed.get('target_persona', '')}")
        lines.append(f"- **Value:** {ed.get('value', '')}")
        lines.append(f"- **Social Hook:** {ed.get('social_hook', '')}\n")

    # ── Programmatic SEO ──────────────────────────────────────────────────────
    lines.append("## Programmatic SEO Patterns\n")
    for prog in data.get("programmatic_seo", []):
        lines.append(f"### `{prog.get('pattern', '')}`")
        lines.append(f"- **Est. Pages:** {prog.get('estimated_page_count', 0):,} | **Difficulty:** {prog.get('difficulty', '').title()}")
        lines.append(f"- **Variables:** {', '.join(prog.get('variables', []))}")
        lines.append(f"- **User Scenarios:** {prog.get('user_scenarios', '')}")
        lines.append(f"- **Example Pages:** {', '.join(prog.get('example_pages', [])[:3])}")
        lines.append(f"- **Implementation:** {prog.get('implementation', '')}\n")

    # ── Internal Linking Blueprint ────────────────────────────────────────────
    lines.append("## Internal Linking Blueprint\n")
    lines.append("*The secret sauce. These are contextual links within body copy — not sidebars.*\n")
    lines.append("| Priority | Source Page | → Target Page | Anchor Text | Where to Place |")
    lines.append("| --- | --- | --- | --- | --- |")

    priority_order = {"critical": 0, "high": 1, "medium": 2}
    sorted_links = sorted(data.get("internal_links", []),
                          key=lambda x: priority_order.get(x.get("priority", "medium"), 2))
    for link in sorted_links:
        p = link.get("priority", "medium")
        p_icon = "🔴" if p == "critical" else "🟡" if p == "high" else "⚪"
        lines.append(f"| {p_icon} {p.title()} | {link.get('source_page', '')} | {link.get('target_page', '')} | *{link.get('anchor_text', '')}* | {link.get('context', '')} |")
    lines.append("")

    # ── Publishing Calendar ───────────────────────────────────────────────────
    lines.append("## Publishing Calendar\n")
    calendar = data.get("publishing_calendar", {})

    lines.append("### Phase 1 — Quick Wins 🎯")
    lines.append("*Start here. High volume, low KD, bottom-funnel. Revenue before authority.*\n")
    lines.append("| Title | Keyword | Volume | KD | Why |")
    lines.append("| --- | --- | --- | --- | --- |")
    for item in calendar.get("phase_1_quick_wins", []):
        kd = item.get("kd", 0)
        kd_tag = "🟢" if kd <= 30 else "🟡" if kd <= 60 else "🔴"
        lines.append(f"| {item.get('title', '')} | {item.get('keyword', '')} | {item.get('volume', ''):,} | {kd} {kd_tag} | {item.get('reason', '')} |")
    lines.append("")

    lines.append("### Phase 2 — Authority Builders 🏛️")
    lines.append("*Pillar pages + high-value clusters. Build the topical authority foundation.*\n")
    lines.append("| Title | Keyword | Volume | KD | Why |")
    lines.append("| --- | --- | --- | --- | --- |")
    for item in calendar.get("phase_2_authority_builders", []):
        kd = item.get("kd", 0)
        kd_tag = "🟢" if kd <= 30 else "🟡" if kd <= 60 else "🔴"
        lines.append(f"| {item.get('title', '')} | {item.get('keyword', '')} | {item.get('volume', ''):,} | {kd} {kd_tag} | {item.get('reason', '')} |")
    lines.append("")

    lines.append("### Phase 3 — Programmatic Scale 🏭")
    lines.append("*High page count, low per-page effort. Dominate the long tail.*\n")
    lines.append("| Pattern | Est. Pages | Why |")
    lines.append("| --- | --- | --- |")
    for item in calendar.get("phase_3_programmatic_scale", []):
        lines.append(f"| `{item.get('pattern', '')}` | {item.get('estimated_pages', ''):,} | {item.get('reason', '')} |")
    lines.append("")

    lines.append("### Phase 4 — Editorial Leadership ✍️")
    lines.append("*Thought leadership + backlink bait. Become the reference in your niche.*\n")
    lines.append("| Title | Angle | Backlink Potential | Why |")
    lines.append("| --- | --- | --- | --- |")
    for item in calendar.get("phase_4_editorial_leadership", []):
        lines.append(f"| {item.get('title', '')} | {item.get('angle', '')} | {item.get('backlink_potential', '')} | {item.get('reason', '')} |")
    lines.append("")

    # ── Conversion Paths ──────────────────────────────────────────────────────
    lines.append("## Conversion Paths\n")
    lines.append("| Pillar | Cluster | CTA | Destination | Stage |")
    lines.append("| --- | --- | --- | --- | --- |")
    for cp in data.get("conversion_paths", []):
        lines.append(f"| {cp.get('pillar', '')} | {cp.get('cluster', '')} | {cp.get('cta_text', '')} | {cp.get('destination', '')} | {cp.get('funnel_stage', '').upper()} |")
    lines.append("")

    # ── Competitor Gaps ───────────────────────────────────────────────────────
    comp_gaps = data.get("competitor_gaps", {})
    opps = comp_gaps.get("opportunities", [])
    blue = comp_gaps.get("blue_ocean", [])
    if opps or blue:
        lines.append("## Competitor Gap Analysis\n")
        if opps:
            lines.append("### Opportunities (They Rank — You Can Compete)\n")
            for opp in opps:
                lines.append(f"**{opp.get('topic', '')}**")
                lines.append(f"- Keywords: {', '.join(opp.get('competitor_keywords', []))}")
                lines.append(f"- Your angle: {opp.get('why_you_can_win', '')}\n")
        if blue:
            lines.append("### Blue Ocean (They Miss — You Can Own)\n")
            for b in blue:
                lines.append(f"**{b.get('topic', '')}**")
                lines.append(f"- Angle: {b.get('angle', '')}")
                lines.append(f"- Why untapped: {b.get('why_untapped', '')}\n")

    # ── Post-Generation Action Plan ────────────────────────────────────────────
    plan = data.get("post_generation_action_plan", {})
    if plan:
        lines.append("---\n")
        lines.append("## Post-Generation Action Plan\n")
        for section_key, section_label, icon in [
            ("immediate_actions", "Immediate Actions (Today)", "⚡"),
            ("validation_steps", "Validation Steps (Before Writing)", "✅"),
            ("phase_1_launch", "Phase 1 Launch Checklist", "🚀"),
            ("ongoing_maintenance", "Ongoing Maintenance", "🔄"),
            ("update_triggers", "Update Triggers", "🔔"),
        ]:
            items = plan.get(section_key, [])
            if items:
                lines.append(f"### {icon} {section_label}\n")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")

    lines.append("\n---")
    lines.append("*Generated by AIAA-Agentic-OS Topical Map Generator v1.0*")
    lines.append("*To update this map: `python3 execution/topical_map.py --from-json topical_map.json`*")
    lines.append("*To refresh keyword data: `python3 execution/topical_map.py --enrich topical_map.json`*")

    return "\n".join(lines)


def format_html(data: dict) -> str:
    meta = data.get("meta", {})
    topic = meta.get("topic", "Topical Map")
    pillars = data.get("pillars", [])
    total_articles = meta.get("total_articles", 0)
    total_volume = meta.get("estimated_total_monthly_volume", 0)
    now = meta.get("generated_at", datetime.now().isoformat())

    # Embed JSON for download
    json_escaped = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    # Build pillar cards HTML
    pillar_cards = []
    for pillar in pillars:
        ptype = pillar.get("type", "informational")
        funnel = pillar.get("funnel_stage", "tofu").upper()
        kd = pillar.get("estimated_kd", 0)
        vol = pillar.get("estimated_volume", 0)
        kd_class = "kd-low" if kd <= 30 else "kd-mid" if kd <= 60 else "kd-high"

        cluster_html = []
        for cluster in pillar.get("clusters", []):
            ckd = cluster.get("estimated_kd", 0)
            ckd_class = "kd-low" if ckd <= 30 else "kd-mid" if ckd <= 60 else "kd-high"
            articles_html = "".join(
                f'<li class="article-item">'
                f'<span class="article-title">{a.get("title", "")}</span>'
                f'<span class="article-meta">{a.get("target_keyword", "")} · {a.get("estimated_volume", 0):,}/mo</span>'
                f'</li>'
                for a in cluster.get("articles", [])
            )
            cluster_html.append(f"""
        <div class="cluster">
          <div class="cluster-header" onclick="toggleCluster(this)">
            <span class="cluster-toggle">▶</span>
            <span class="cluster-title">{cluster.get("title", "")}</span>
            <span class="cluster-stats">
              <span class="vol-badge">{cluster.get("estimated_volume", 0):,}/mo</span>
              <span class="kd-badge {ckd_class}">KD {ckd}</span>
              <span class="format-badge">{cluster.get("content_format", "").title()}</span>
            </span>
          </div>
          <div class="cluster-body hidden">
            <div class="cluster-intent">{cluster.get("intention", "")}</div>
            <ul class="articles-list">{articles_html}</ul>
          </div>
        </div>""")

        pillar_cards.append(f"""
    <div class="pillar pillar-{ptype}">
      <div class="pillar-header" onclick="togglePillar(this)">
        <div class="pillar-title-row">
          <span class="pillar-toggle">▼</span>
          <span class="pillar-title">{pillar.get("title", "")}</span>
        </div>
        <div class="pillar-badges">
          <span class="type-badge type-{ptype}">{ptype.title()}</span>
          <span class="funnel-badge funnel-{pillar.get('funnel_stage', 'tofu')}">{funnel}</span>
          <span class="vol-badge">{vol:,}/mo</span>
          <span class="kd-badge {kd_class}">KD {kd}</span>
        </div>
      </div>
      <div class="pillar-intention">{pillar.get("intention", "")}</div>
      <div class="pillar-meta">
        <code>/{pillar.get("url_slug", "")}</code>
        · Keyword: <em>{pillar.get("target_keyword", "")}</em>
        · {len(pillar.get("clusters", []))} clusters
      </div>
      <div class="clusters-container">{"".join(cluster_html)}</div>
    </div>""")

    # Build quick wins table
    qw_rows = "".join(
        f'<tr><td>{item.get("title", "")}</td><td><code>{item.get("keyword", "")}</code></td>'
        f'<td>{item.get("volume", 0):,}</td>'
        f'<td class="{"kd-cell-low" if item.get("kd", 0) <= 30 else "kd-cell-mid" if item.get("kd", 0) <= 60 else "kd-cell-high"}">{item.get("kd", 0)}</td>'
        f'<td>{item.get("reason", "")}</td></tr>'
        for item in data.get("publishing_calendar", {}).get("phase_1_quick_wins", [])
    )

    # Build internal links table
    il_rows = "".join(
        f'<tr class="link-{link.get("priority", "medium")}">'
        f'<td><span class="priority-dot priority-{link.get("priority", "medium")}"></span>{link.get("priority", "").title()}</td>'
        f'<td>{link.get("source_page", "")}</td><td>→</td>'
        f'<td>{link.get("target_page", "")}</td>'
        f'<td><em>{link.get("anchor_text", "")}</em></td>'
        f'<td>{link.get("context", "")}</td></tr>'
        for link in sorted(data.get("internal_links", []),
                           key=lambda x: {"critical": 0, "high": 1, "medium": 2}.get(x.get("priority", "medium"), 2))
    )

    # Build action plan
    plan = data.get("post_generation_action_plan", {})
    action_html = ""
    for key, label, icon in [
        ("immediate_actions", "Immediate Actions (Today)", "⚡"),
        ("validation_steps", "Validation Steps", "✅"),
        ("phase_1_launch", "Phase 1 Launch Checklist", "🚀"),
        ("ongoing_maintenance", "Ongoing Maintenance", "🔄"),
        ("update_triggers", "Update Triggers", "🔔"),
    ]:
        items = plan.get(key, [])
        if items:
            items_html = "".join(f'<li>{item}</li>' for item in items)
            action_html += f'<div class="action-section"><h4>{icon} {label}</h4><ul>{items_html}</ul></div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Topical Map: {topic}</title>
<style>
  :root {{
    --blue: #3b82f6; --blue-light: #1e3a6e; --blue-dark: #93c5fd;
    --green: #22c55e; --green-light: #1a3a28; --green-dark: #86efac;
    --purple: #a78bfa; --orange: #fb923c;
    --bg: #0d0f1a; --card: #151828; --card-alt: #1a1e30;
    --border: #252a42; --border-light: #1e2338;
    --text: #e2e8f5; --text-muted: #8b9cc7; --text-dim: #4a5580;
    --kd-low: #4ade80; --kd-mid: #fbbf24; --kd-high: #f87171;
    --radius: 8px; --shadow: 0 2px 8px rgba(0,0,0,0.4);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.5; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}

  /* Header */
  .header {{ background: linear-gradient(135deg, #1a1e30 0%, #0f1422 100%); color: white; padding: 24px; border-radius: var(--radius); margin-bottom: 20px; border: 1px solid var(--border); }}
  .header h1 {{ font-size: 1.6rem; font-weight: 700; margin-bottom: 8px; }}
  .header-meta {{ font-size: 0.85rem; color: var(--text-muted); }}
  .header-meta span {{ margin-right: 20px; }}

  /* Stats bar */
  .stats-bar {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }}
  .stat-card {{ background: var(--card); border-radius: var(--radius); padding: 16px; border: 1px solid var(--border); text-align: center; }}
  .stat-number {{ font-size: 1.8rem; font-weight: 700; color: var(--blue); }}
  .stat-label {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}

  /* Tabs */
  .tabs {{ display: flex; gap: 4px; margin-bottom: 20px; background: var(--card); padding: 6px; border-radius: var(--radius); border: 1px solid var(--border); }}
  .tab {{ padding: 8px 18px; border-radius: 6px; cursor: pointer; font-size: 0.875rem; font-weight: 500; color: var(--text-muted); transition: all 0.15s; border: none; background: none; }}
  .tab:hover {{ background: var(--card-alt); color: var(--text); }}
  .tab.active {{ background: var(--blue); color: white; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}

  /* Controls */
  .controls {{ display: flex; gap: 10px; margin-bottom: 16px; align-items: center; }}
  .btn {{ padding: 7px 16px; border-radius: 6px; border: 1px solid var(--border); background: var(--card); cursor: pointer; font-size: 0.85rem; font-weight: 500; color: var(--text-muted); transition: all 0.15s; }}
  .btn:hover {{ background: var(--card-alt); color: var(--text); }}
  .btn-primary {{ background: var(--blue); color: white; border-color: var(--blue); }}
  .btn-primary:hover {{ background: #2563eb; }}
  .filter-label {{ font-size: 0.8rem; color: var(--text-muted); }}
  .filter-btn {{ padding: 5px 10px; border-radius: 20px; border: 1px solid var(--border); background: var(--card); cursor: pointer; font-size: 0.75rem; color: var(--text-muted); }}
  .filter-btn.active {{ background: var(--blue); color: white; border-color: var(--blue); }}

  /* Pillars */
  .pillar {{ background: var(--card); border-radius: var(--radius); margin-bottom: 12px; border: 1px solid var(--border); box-shadow: var(--shadow); overflow: hidden; }}
  .pillar-informational {{ border-left: 4px solid var(--blue); }}
  .pillar-commercial {{ border-left: 4px solid var(--green); }}
  .pillar-header {{ padding: 16px; cursor: pointer; display: flex; justify-content: space-between; align-items: flex-start; }}
  .pillar-header:hover {{ background: var(--card-alt); }}
  .pillar-title-row {{ display: flex; align-items: center; gap: 10px; }}
  .pillar-toggle {{ color: var(--text-dim); font-size: 0.75rem; transition: transform 0.2s; min-width: 16px; }}
  .pillar-title {{ font-size: 1rem; font-weight: 600; color: var(--text); }}
  .pillar-badges {{ display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }}
  .pillar-intention {{ font-size: 0.8rem; color: var(--text-muted); padding: 0 16px 6px; }}
  .pillar-meta {{ font-size: 0.75rem; color: var(--text-dim); padding: 0 16px 12px; }}
  .pillar-meta code {{ background: var(--card-alt); padding: 1px 5px; border-radius: 3px; color: var(--blue-dark); }}

  /* Clusters */
  .clusters-container {{ padding: 0 16px 16px; }}
  .cluster {{ border: 1px solid var(--border); border-radius: 6px; margin-bottom: 8px; background: var(--bg); }}
  .cluster-header {{ display: flex; align-items: center; gap: 10px; padding: 10px 12px; cursor: pointer; }}
  .cluster-header:hover {{ background: var(--card-alt); border-radius: 6px; }}
  .cluster-toggle {{ color: var(--text-dim); font-size: 0.7rem; transition: transform 0.2s; }}
  .cluster-title {{ font-size: 0.875rem; font-weight: 500; flex: 1; color: var(--text); }}
  .cluster-stats {{ display: flex; gap: 5px; }}
  .cluster-body {{ padding: 10px 12px; border-top: 1px solid var(--border-light); }}
  .cluster-body.hidden {{ display: none; }}
  .cluster-intent {{ font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px; }}
  .articles-list {{ list-style: none; padding: 0; }}
  .article-item {{ display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid var(--border-light); font-size: 0.8rem; }}
  .article-item:last-child {{ border-bottom: none; }}
  .article-title {{ color: var(--text); flex: 1; }}
  .article-meta {{ color: var(--text-dim); font-size: 0.75rem; }}

  /* Badges */
  .vol-badge {{ background: var(--blue-light); color: var(--blue-dark); padding: 2px 7px; border-radius: 20px; font-size: 0.7rem; font-weight: 500; white-space: nowrap; }}
  .kd-badge {{ padding: 2px 7px; border-radius: 20px; font-size: 0.7rem; font-weight: 600; white-space: nowrap; }}
  .kd-low {{ background: #1a3a28; color: var(--kd-low); }}
  .kd-mid {{ background: #3a2a0a; color: var(--kd-mid); }}
  .kd-high {{ background: #3a1010; color: var(--kd-high); }}
  .type-badge {{ padding: 2px 8px; border-radius: 20px; font-size: 0.7rem; font-weight: 500; }}
  .type-informational {{ background: var(--blue-light); color: var(--blue-dark); }}
  .type-commercial {{ background: var(--green-light); color: var(--green-dark); }}
  .funnel-badge {{ padding: 2px 8px; border-radius: 20px; font-size: 0.7rem; font-weight: 600; }}
  .funnel-tofu {{ background: #1a3040; color: #38bdf8; }}
  .funnel-mofu {{ background: #332a0a; color: #fcd34d; }}
  .funnel-bofu {{ background: #2a1640; color: #c084fc; }}
  .format-badge {{ background: var(--card-alt); color: var(--text-muted); padding: 2px 7px; border-radius: 20px; font-size: 0.7rem; }}

  /* Tables */
  .section {{ background: var(--card); border-radius: var(--radius); border: 1px solid var(--border); overflow: hidden; margin-bottom: 16px; }}
  .section-header {{ padding: 14px 18px; background: var(--card-alt); border-bottom: 1px solid var(--border); font-weight: 600; font-size: 0.9rem; color: var(--text); }}
  .section-body {{ padding: 0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  th {{ background: var(--card-alt); padding: 9px 14px; text-align: left; font-weight: 600; color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.03em; border-bottom: 1px solid var(--border); }}
  td {{ padding: 9px 14px; border-bottom: 1px solid var(--border-light); vertical-align: top; color: var(--text); }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: var(--card-alt); }}
  .kd-cell-low {{ color: var(--kd-low); font-weight: 600; }}
  .kd-cell-mid {{ color: var(--kd-mid); font-weight: 600; }}
  .kd-cell-high {{ color: var(--kd-high); font-weight: 600; }}
  code {{ background: var(--card-alt); color: var(--blue-dark); padding: 1px 5px; border-radius: 3px; font-size: 0.8rem; }}

  /* Internal links */
  .priority-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 5px; }}
  .priority-critical {{ background: #f87171; }}
  .priority-high {{ background: #fbbf24; }}
  .priority-medium {{ background: var(--text-dim); }}

  /* Action plan */
  .action-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
  .action-section {{ background: var(--card); border-radius: var(--radius); border: 1px solid var(--border); padding: 16px; }}
  .action-section h4 {{ font-size: 0.875rem; font-weight: 600; margin-bottom: 10px; color: var(--text); }}
  .action-section ul {{ list-style: none; padding: 0; }}
  .action-section li {{ font-size: 0.82rem; color: var(--text-muted); padding: 4px 0; border-bottom: 1px solid var(--border-light); }}
  .action-section li:last-child {{ border-bottom: none; }}
  .action-section li::before {{ content: "→ "; color: var(--blue); font-weight: 600; }}

  /* Legend */
  .legend {{ display: flex; gap: 16px; flex-wrap: wrap; padding: 10px 0; font-size: 0.75rem; color: var(--text-muted); }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 2px; }}

  @media (max-width: 768px) {{
    .stats-bar {{ grid-template-columns: repeat(2, 1fr); }}
    .action-grid {{ grid-template-columns: 1fr; }}
    .pillar-badges {{ display: none; }}
    .cluster-stats {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="header">
    <h1>📊 Topical Authority Map: {topic}</h1>
    <div class="header-meta">
      <span>👥 {meta.get("audience", "")}</span>
      <span>🎯 {meta.get("goal", "")}</span>
      <span>📅 {now[:10]}</span>
    </div>
  </div>

  <!-- Stats -->
  <div class="stats-bar">
    <div class="stat-card"><div class="stat-number">{meta.get("total_pillars", len(pillars))}</div><div class="stat-label">Pillars</div></div>
    <div class="stat-card"><div class="stat-number">{meta.get("total_clusters", 0)}</div><div class="stat-label">Clusters</div></div>
    <div class="stat-card"><div class="stat-number">{total_articles}</div><div class="stat-label">Articles</div></div>
    <div class="stat-card"><div class="stat-number">{total_volume:,}</div><div class="stat-label">Est. Monthly Volume</div></div>
  </div>

  <!-- Legend -->
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#3b82f6"></div> Informational Pillar</div>
    <div class="legend-item"><div class="legend-dot" style="background:#22c55e"></div> Commercial Pillar</div>
    <div class="legend-item"><div class="legend-dot" style="background:#1a3a28;border:1px solid #4ade80"></div> KD ≤30 (Low)</div>
    <div class="legend-item"><div class="legend-dot" style="background:#3a2a0a;border:1px solid #fbbf24"></div> KD 31-60 (Med)</div>
    <div class="legend-item"><div class="legend-dot" style="background:#3a1010;border:1px solid #f87171"></div> KD &gt;60 (High)</div>
    <button class="btn btn-primary" onclick="downloadJSON()" style="margin-left:auto">⬇ Download JSON</button>
  </div>

  <!-- Tabs -->
  <div class="tabs">
    <button class="tab active" onclick="showTab('pillars', this)">🗺️ Pillars & Clusters</button>
    <button class="tab" onclick="showTab('calendar', this)">📅 Publishing Calendar</button>
    <button class="tab" onclick="showTab('links', this)">🔗 Internal Links</button>
    <button class="tab" onclick="showTab('tools', this)">🛠️ Tools & Editorial</button>
    <button class="tab" onclick="showTab('action', this)">⚡ Action Plan</button>
  </div>

  <!-- Tab: Pillars -->
  <div id="tab-pillars" class="tab-panel active">
    <div class="controls">
      <button class="btn" onclick="expandAll()">Expand All</button>
      <button class="btn" onclick="collapseAll()">Collapse All</button>
      <span class="filter-label">Filter:</span>
      <button class="filter-btn active" onclick="filterPillars('all', this)">All</button>
      <button class="filter-btn" onclick="filterPillars('informational', this)">Informational</button>
      <button class="filter-btn" onclick="filterPillars('commercial', this)">Commercial</button>
    </div>
    {"".join(pillar_cards)}
  </div>

  <!-- Tab: Publishing Calendar -->
  <div id="tab-calendar" class="tab-panel">
    <div class="section">
      <div class="section-header">🎯 Phase 1 — Quick Wins (Publish First)</div>
      <div class="section-body">
        <table><thead><tr><th>Title</th><th>Keyword</th><th>Volume</th><th>KD</th><th>Why This First</th></tr></thead>
        <tbody>{qw_rows}</tbody></table>
      </div>
    </div>
    <div class="section">
      <div class="section-header">🏛️ Phase 2 — Authority Builders</div>
      <div class="section-body">
        <table><thead><tr><th>Title</th><th>Keyword</th><th>Volume</th><th>KD</th><th>Why</th></tr></thead>
        <tbody>{"".join(
            f'<tr><td>{item.get("title","")}</td><td><code>{item.get("keyword","")}</code></td>'
            f'<td>{item.get("volume",0):,}</td>'
            f'<td class="{"kd-cell-low" if item.get("kd",0)<=30 else "kd-cell-mid" if item.get("kd",0)<=60 else "kd-cell-high"}">{item.get("kd",0)}</td>'
            f'<td>{item.get("reason","")}</td></tr>'
            for item in data.get("publishing_calendar",{}).get("phase_2_authority_builders",[])
        )}</tbody></table>
      </div>
    </div>
    <div class="section">
      <div class="section-header">🏭 Phase 3 — Programmatic Scale</div>
      <div class="section-body">
        <table><thead><tr><th>Pattern</th><th>Est. Pages</th><th>Why</th></tr></thead>
        <tbody>{"".join(
            f'<tr><td><code>{item.get("pattern","")}</code></td>'
            f'<td>{item.get("estimated_pages",0):,}</td>'
            f'<td>{item.get("reason","")}</td></tr>'
            for item in data.get("publishing_calendar",{}).get("phase_3_programmatic_scale",[])
        )}</tbody></table>
      </div>
    </div>
    <div class="section">
      <div class="section-header">✍️ Phase 4 — Editorial Leadership</div>
      <div class="section-body">
        <table><thead><tr><th>Title</th><th>Angle</th><th>Backlink Potential</th><th>Why</th></tr></thead>
        <tbody>{"".join(
            f'<tr><td>{item.get("title","")}</td><td>{item.get("angle","")}</td>'
            f'<td>{item.get("backlink_potential","")}</td>'
            f'<td>{item.get("reason","")}</td></tr>'
            for item in data.get("publishing_calendar",{}).get("phase_4_editorial_leadership",[])
        )}</tbody></table>
      </div>
    </div>
  </div>

  <!-- Tab: Internal Links -->
  <div id="tab-links" class="tab-panel">
    <div class="section">
      <div class="section-header">🔗 Internal Linking Blueprint — The Secret Sauce</div>
      <div class="section-body">
        <table><thead><tr><th>Priority</th><th>Source Page</th><th></th><th>Target Page</th><th>Anchor Text</th><th>Where to Place</th></tr></thead>
        <tbody>{il_rows}</tbody></table>
      </div>
    </div>
  </div>

  <!-- Tab: Tools & Editorial -->
  <div id="tab-tools" class="tab-panel">
    <div class="section">
      <div class="section-header">🛠️ Tools & Free Resources</div>
      <div class="section-body">
        <table><thead><tr><th>Tool Name</th><th>Type</th><th>Conversion</th><th>Intention</th><th>Complexity</th></tr></thead>
        <tbody>{"".join(
            f'<tr><td><strong>{t.get("name","")}</strong></td><td>{t.get("type","")}</td>'
            f'<td><span class="type-badge type-{"informational" if t.get("conversion_potential","")=="low" else "commercial"}">{t.get("conversion_potential","").upper()}</span></td>'
            f'<td>{t.get("intention","")}</td><td>{t.get("complexity","").title()}</td></tr>'
            for t in data.get("tools_resources",[])
        )}</tbody></table>
      </div>
    </div>
    <div class="section">
      <div class="section-header">✍️ Editorial Content</div>
      <div class="section-body">
        <table><thead><tr><th>Title</th><th>Angle</th><th>Persona</th><th>Social Hook</th></tr></thead>
        <tbody>{"".join(
            f'<tr><td><strong>{e.get("title","")}</strong></td><td>{e.get("angle","")}</td>'
            f'<td>{e.get("target_persona","")}</td><td>{e.get("social_hook","")}</td></tr>'
            for e in data.get("editorial_content",[])
        )}</tbody></table>
      </div>
    </div>
    <div class="section">
      <div class="section-header">📈 Programmatic SEO Patterns</div>
      <div class="section-body">
        <table><thead><tr><th>Pattern</th><th>Est. Pages</th><th>Difficulty</th><th>User Scenarios</th></tr></thead>
        <tbody>{"".join(
            f'<tr><td><code>{p.get("pattern","")}</code></td>'
            f'<td>{p.get("estimated_page_count",0):,}</td>'
            f'<td>{p.get("difficulty","").title()}</td>'
            f'<td>{p.get("user_scenarios","")}</td></tr>'
            for p in data.get("programmatic_seo",[])
        )}</tbody></table>
      </div>
    </div>
  </div>

  <!-- Tab: Action Plan -->
  <div id="tab-action" class="tab-panel">
    <div class="action-grid">{action_html}</div>
  </div>

</div>

<script>
const MAP_DATA = {json_escaped};

function showTab(id, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  btn.classList.add('active');
}}

function togglePillar(header) {{
  const pillar = header.closest('.pillar');
  const container = pillar.querySelector('.clusters-container');
  const toggle = header.querySelector('.pillar-toggle');
  const isOpen = !container.style.display || container.style.display === 'block';
  container.style.display = isOpen ? 'none' : 'block';
  toggle.style.transform = isOpen ? 'rotate(-90deg)' : '';
}}

function toggleCluster(header) {{
  const body = header.nextElementSibling;
  const toggle = header.querySelector('.cluster-toggle');
  const isHidden = body.classList.contains('hidden');
  body.classList.toggle('hidden', !isHidden);
  toggle.style.transform = isHidden ? 'rotate(90deg)' : '';
}}

function expandAll() {{
  document.querySelectorAll('.clusters-container').forEach(c => c.style.display = 'block');
  document.querySelectorAll('.pillar-toggle').forEach(t => t.style.transform = '');
  document.querySelectorAll('.cluster-body').forEach(b => b.classList.remove('hidden'));
  document.querySelectorAll('.cluster-toggle').forEach(t => t.style.transform = 'rotate(90deg)');
}}

function collapseAll() {{
  document.querySelectorAll('.clusters-container').forEach(c => c.style.display = 'none');
  document.querySelectorAll('.pillar-toggle').forEach(t => t.style.transform = 'rotate(-90deg)');
  document.querySelectorAll('.cluster-body').forEach(b => b.classList.add('hidden'));
  document.querySelectorAll('.cluster-toggle').forEach(t => t.style.transform = '');
}}

function filterPillars(type, btn) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.pillar').forEach(p => {{
    if (type === 'all') {{ p.style.display = ''; return; }}
    p.style.display = p.classList.contains('pillar-' + type) ? '' : 'none';
  }});
}}

function downloadJSON() {{
  const blob = new Blob([JSON.stringify(MAP_DATA, null, 2)], {{type: 'application/json'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'topical_map.json';
  a.click();
  URL.revokeObjectURL(url);
}}
</script>
</body>
</html>"""


# ─── JSON → calculate totals ─────────────────────────────────────────────────
def calculate_totals(data: dict) -> dict:
    """Fill in meta totals from pillar/cluster/article counts."""
    pillars = data.get("pillars", [])
    total_pillars = len(pillars)
    total_clusters = sum(len(p.get("clusters", [])) for p in pillars)
    total_articles = sum(
        len(c.get("articles", []))
        for p in pillars
        for c in p.get("clusters", [])
    )
    total_volume = sum(p.get("estimated_volume", 0) for p in pillars)
    data.setdefault("meta", {})
    data["meta"]["total_pillars"] = total_pillars
    data["meta"]["total_clusters"] = total_clusters
    data["meta"]["total_articles"] = total_articles
    data["meta"]["estimated_total_monthly_volume"] = total_volume
    if "generated_at" not in data["meta"]:
        data["meta"]["generated_at"] = datetime.now().isoformat()
    return data


# ─── Slug generator ───────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")[:50]


# ─── Output writer ────────────────────────────────────────────────────────────
def write_outputs(data: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "topical_map.json").write_text(format_json(data), encoding="utf-8")
    print(f"  ✓ JSON    → {output_dir}/topical_map.json")

    (output_dir / "topical_map.csv").write_text(format_csv(data), encoding="utf-8")
    print(f"  ✓ CSV     → {output_dir}/topical_map.csv")

    (output_dir / "topical_map.md").write_text(format_markdown(data), encoding="utf-8")
    print(f"  ✓ Markdown → {output_dir}/topical_map.md")

    (output_dir / "topical_map.html").write_text(format_html(data), encoding="utf-8")
    print(f"  ✓ HTML    → {output_dir}/topical_map.html")


# ─── Parse / extract JSON from Claude response ────────────────────────────────
def extract_json(text: str) -> dict:
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)

    # Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Find first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from Claude response (first 500 chars):\n{text[:500]}")


# ─── Print summary ────────────────────────────────────────────────────────────
def print_summary(data: dict, output_dir: Path) -> None:
    meta = data.get("meta", {})
    cal = data.get("publishing_calendar", {})
    print("\n" + "═" * 60)
    print(f"  TOPICAL MAP COMPLETE: {meta.get('topic', '')}")
    print("═" * 60)
    print(f"  Pillars:       {meta.get('total_pillars', 0)}")
    print(f"  Clusters:      {meta.get('total_clusters', 0)}")
    print(f"  Articles:      {meta.get('total_articles', 0)}")
    print(f"  Est. Volume:   {meta.get('estimated_total_monthly_volume', 0):,}/mo")
    print(f"  Phase 1 wins:  {len(cal.get('phase_1_quick_wins', []))} articles")
    print(f"  Internal links: {len(data.get('internal_links', []))}")
    print(f"\n  Output dir: {output_dir}")
    print("\n  NEXT STEPS:")
    plan = data.get("post_generation_action_plan", {})
    for action in plan.get("immediate_actions", [])[:3]:
        print(f"  → {action}")
    print("\n  Full action plan in topical_map.md and topical_map.html")
    print("═" * 60 + "\n")


# ─── Enrich mode: refresh keyword data on existing JSON ───────────────────────
def run_enrich(json_path: Path, dfs: DataForSEOClient, location: str) -> None:
    print(f"\n[Enrich] Loading: {json_path}")
    data = json.loads(json_path.read_text(encoding="utf-8"))

    # Collect all keywords from the map
    all_keywords = []
    for pillar in data.get("pillars", []):
        if pillar.get("target_keyword"):
            all_keywords.append({"keyword": pillar["target_keyword"]})
        for cluster in pillar.get("clusters", []):
            if cluster.get("target_keyword"):
                all_keywords.append({"keyword": cluster["target_keyword"]})
            for article in cluster.get("articles", []):
                if article.get("target_keyword"):
                    all_keywords.append({"keyword": article["target_keyword"]})

    print(f"[Enrich] Refreshing {len(all_keywords)} keywords via DataForSEO...")
    enriched = dfs.enrich_keywords(all_keywords, location)
    enriched_map = {k.get("keyword", "").lower(): k for k in enriched}

    def _enrich_item(item: dict) -> dict:
        kw = item.get("target_keyword", "").lower()
        if kw in enriched_map:
            item["estimated_volume"] = enriched_map[kw].get("volume", item.get("estimated_volume", 0))
        return item

    for pillar in data.get("pillars", []):
        _enrich_item(pillar)
        for cluster in pillar.get("clusters", []):
            _enrich_item(cluster)
            for article in cluster.get("articles", []):
                _enrich_item(article)

    data = calculate_totals(data)
    data["meta"]["enriched_at"] = datetime.now().isoformat()

    # Write to new timestamped dir
    slug = slugify(data.get("meta", {}).get("topic", "topical-map"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = OUTPUT_BASE / f"{slug}_{ts}"
    write_outputs(data, output_dir)
    print_summary(data, output_dir)


# ─── From-JSON mode: regenerate outputs from existing JSON ────────────────────
def run_from_json(json_path: Path) -> None:
    print(f"\n[From JSON] Loading: {json_path}")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data = calculate_totals(data)
    # Write outputs to the same directory as the source JSON
    output_dir = json_path.parent
    print(f"[From JSON] Writing outputs to: {output_dir}")
    write_outputs(data, output_dir)
    print_summary(data, output_dir)


# ─── Main flow ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AIAA Topical Map Generator")
    parser.add_argument("--topic", help="Broad topic (e.g. 'Work-Life Balance')")
    parser.add_argument("--audience", help="Target audience description")
    parser.add_argument("--goal", help="Business goal / conversion target")
    parser.add_argument("--competitor", default="", help="Competitor domain (optional)")
    parser.add_argument("--urls", default="", help="Path to .txt file with existing URLs (one per line)")
    parser.add_argument("--location", default="United States", help="Target country for keyword data")
    parser.add_argument("--from-json", default="", help="Regenerate outputs from existing JSON (skip API calls)")
    parser.add_argument("--enrich", default="", help="Refresh keyword data on an existing topical_map.json")
    parser.add_argument("--output-dir", default="", help="Custom output directory")
    parser.add_argument("--phase1-only", action="store_true", help="Run DataForSEO research only, print prompt for Claude Code, then exit")
    args = parser.parse_args()

    env = load_env()

    # ── Validate API keys ─────────────────────────────────────────────────────
    anthropic_key = env.get("ANTHROPIC_API_KEY", "")
    dfs_login = env.get("DATAFORSEO_LOGIN", "")
    dfs_password = env.get("DATAFORSEO_PASSWORD", "")

    dfs = None
    if dfs_login and dfs_password:
        dfs = DataForSEOClient(dfs_login, dfs_password)
    else:
        print("⚠️  DataForSEO credentials not found in .env — will use AI-estimated volumes only")

    # ── Enrich mode ───────────────────────────────────────────────────────────
    if args.enrich:
        if not dfs:
            print("❌ --enrich requires DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD in .env")
            sys.exit(1)
        run_enrich(Path(args.enrich), dfs, args.location)
        return

    # ── From-JSON mode ─────────────────────────────────────────────────────────
    if args.from_json:
        run_from_json(Path(args.from_json))
        return

    # ── Validate required inputs for fresh run ─────────────────────────────────
    if not args.topic or not args.audience or not args.goal:
        print("❌ --topic, --audience, and --goal are required for a fresh run")
        print("   Or use --from-json <path> to regenerate from existing JSON")
        print("   Or use --enrich <path> to refresh keyword data")
        parser.print_help()
        sys.exit(1)

    if not anthropic_key and not getattr(args, "phase1_only", False):
        print("⚠️  ANTHROPIC_API_KEY not set — running in phase1-only mode (Claude Code will generate the map natively)")
        args.phase1_only = True

    slug = slugify(args.topic)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_BASE / f"{slug}_{ts}"

    print(f"\n{'═'*60}")
    print(f"  TOPICAL MAP GENERATOR — AIAA-Agentic-OS")
    print(f"  Topic: {args.topic}")
    print(f"  Audience: {args.audience}")
    print(f"  Goal: {args.goal}")
    if args.competitor:
        print(f"  Competitor: {args.competitor}")
    print(f"  Output: {output_dir}")
    print(f"{'═'*60}\n")

    # ── Phase 1: Keyword Research ──────────────────────────────────────────────
    keyword_data = []
    competitor_keywords = []

    if dfs:
        print("Phase 1: Keyword Research (DataForSEO)...")
        print(f"  → Fetching related keywords for '{args.topic}'...")
        keyword_data = dfs.get_related_keywords(args.topic, args.location, limit=100)
        print(f"  ✓ Got {len(keyword_data)} related keywords")

        if args.competitor:
            print(f"  → Fetching competitor keywords for {args.competitor}...")
            competitor_keywords = dfs.get_competitor_keywords(args.competitor, args.location, limit=100)
            print(f"  ✓ Got {len(competitor_keywords)} competitor keywords")
    else:
        print("Phase 1: Skipping keyword research (no DataForSEO credentials)")

    # Load existing URLs if provided
    existing_urls = []
    if args.urls:
        urls_path = Path(args.urls)
        if urls_path.exists():
            existing_urls = [line.strip() for line in urls_path.read_text().splitlines() if line.strip()]
            print(f"  ✓ Loaded {len(existing_urls)} existing URLs for restructuring")
        else:
            print(f"  ⚠️  URLs file not found: {args.urls} — skipping")

    # ── Phase 1-only mode: save keyword data + print prompt for Claude Code ──────
    if getattr(args, "phase1_only", False):
        # Save keyword data to output dir
        output_dir.mkdir(parents=True, exist_ok=True)
        kd_path = output_dir / "keyword_data.json"
        kd_payload = {
            "topic": args.topic,
            "audience": args.audience,
            "goal": args.goal,
            "competitor": args.competitor or "",
            "location": args.location,
            "keyword_data": keyword_data,
            "competitor_keywords": competitor_keywords,
            "existing_urls": existing_urls,
            "collected_at": datetime.now().isoformat(),
        }
        kd_path.write_text(json.dumps(kd_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  ✓ Keyword data saved: {kd_path}")

        # Build and print the prompt so Claude Code can use it natively
        prompt = build_prompt(
            topic=args.topic,
            audience=args.audience,
            goal=args.goal,
            keyword_data=keyword_data,
            competitor_keywords=competitor_keywords,
            existing_urls=existing_urls,
            competitor_domain=args.competitor,
        )
        print(f"\n{'═'*60}")
        print("SYSTEM PROMPT:")
        print("─" * 60)
        print(SYSTEM_PROMPT)
        print(f"\n{'═'*60}")
        print("USER PROMPT (generate the JSON from this):")
        print("─" * 60)
        print(prompt)
        print(f"\n{'═'*60}")
        print(f"Phase 1 complete.")
        print(f"Output dir: {output_dir}")
        print(f"Keyword data: {kd_path}")
        print(f"\nNext steps:")
        print(f"  1. Use the prompt above to generate topical_map.json")
        print(f"  2. Save JSON to: {output_dir}/topical_map.json")
        print(f"  3. Run: python3 execution/topical_map.py --from-json {output_dir}/topical_map.json")
        print(f"{'═'*60}\n")
        return

    # ── Phase 2: Generate Topical Map ─────────────────────────────────────────
    print("\nPhase 2: Generating Topical Map (Claude Opus)...")
    prompt = build_prompt(
        topic=args.topic,
        audience=args.audience,
        goal=args.goal,
        keyword_data=keyword_data,
        competitor_keywords=competitor_keywords,
        existing_urls=existing_urls,
        competitor_domain=args.competitor,
    )

    raw_response = call_claude(anthropic_key, prompt, SYSTEM_PROMPT)

    # Parse JSON — retry once with stricter instruction if needed
    try:
        data = extract_json(raw_response)
    except ValueError:
        print("  ⚠️  JSON parse failed — retrying with stricter prompt...")
        retry_prompt = prompt + "\n\nCRITICAL: Your previous response was not valid JSON. Return ONLY a valid JSON object. No other text. Start your response with { and end with }."
        raw_response2 = call_claude(anthropic_key, retry_prompt, SYSTEM_PROMPT)
        data = extract_json(raw_response2)

    print("  ✓ Topical map generated")

    # Merge meta + recalculate totals
    data.setdefault("meta", {})
    data["meta"]["topic"] = args.topic
    data["meta"]["audience"] = args.audience
    data["meta"]["goal"] = args.goal
    data["meta"]["generated_at"] = datetime.now().isoformat()
    if keyword_data:
        data["meta"]["keyword_data_source"] = "DataForSEO"
        data["meta"]["keywords_analyzed"] = len(keyword_data)
    data = calculate_totals(data)

    # ── Phase 3: Write Outputs ────────────────────────────────────────────────
    print("\nPhase 3: Writing Outputs...")
    write_outputs(data, output_dir)

    # ── Summary ───────────────────────────────────────────────────────────────
    print_summary(data, output_dir)


if __name__ == "__main__":
    main()
