#!/usr/bin/env python3
"""
d100_v3_runner.py — D100 v3.2 Batch Runner
Processes a CSV of practices end-to-end: scrape → Claude Code native → GitHub Pages deploy → Slack

Usage:
  python3 d100_v3_runner.py --csv /path/to/practices.csv
  python3 d100_v3_runner.py --csv /path/to/practices.csv --dry-run
  python3 d100_v3_runner.py --csv /path/to/practices.csv --site-index 0  # run single row

CSV Format:
  website,context
  https://example.com,"Practice Name, City ST; Dr. Name MD; specialty; X practitioners; $XXXk MRR"
  (booking_url auto-detected from scraped homepage; semrush fetched via API)

Environment (.env at project root):
  ANTHROPIC_API_KEY=sk-ant-...
  SLACK_WEBHOOK_URL=https://hooks.slack.com/...
  SEMRUSH_API_KEY=...

Phase 3 deploys seo_report.html to GitHub Pages as a personalized deliverables page.
Repo slug format: Plug-and-play-AI-SEO-and-Ad-Strategy-for-{Company-Name}
Live URL: https://{GHUSER}.github.io/Plug-and-play-AI-SEO-and-Ad-Strategy-for-{Company-Name}/
"""

import argparse
import concurrent.futures
import csv
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path

# ── Project paths ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
TEMPLATE_PATH = PROJECT_ROOT / "skills" / "templates" / "health_assessment_template.html"
OUTPUT_ROOT = PROJECT_ROOT / "output" / "d100_runs"

# ── GitHub deploy config ────────────────────────────────────────────────────────
# Deliverables page slug format: Plug-and-play-AI-SEO-and-Ad-Strategy-for-{Company-Name}
# GitHub user is resolved at runtime via: gh api user --jq '.login'
DELIVERABLES_SLUG_PREFIX = "Plug-and-play-AI-SEO-and-Ad-Strategy-for-"

# ── Load .env ──────────────────────────────────────────────────────────────────
def load_env():
    env_path = PROJECT_ROOT / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    # Override with real environment (only if non-empty — Claude Code sets ANTHROPIC_API_KEY='' itself)
    for k in ("ANTHROPIC_API_KEY", "SLACK_WEBHOOK_URL", "SEMRUSH_API_KEY"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


# ── Phase 1: urllib scrape ─────────────────────────────────────────────────────
def scrape_page(url: str, timeout: int = 5) -> str:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", errors="ignore")
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3000]
    except Exception as e:
        return f"ERROR: {e}"


def scrape_site(website: str) -> str:
    base = website.rstrip("/")
    slugs = ["", "/about/", "/services/", "/team/", "/new-patients/",
             "/functional-medicine/", "/weight-loss/", "/hormone/", "/contact/"]
    urls = [base + slug for slug in slugs]
    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as ex:
        results = list(ex.map(scrape_page, urls))
    sections = [f"## PAGE: {url}\n\n{text}" for url, text in zip(urls, results)]
    return "\n\n---\n\n".join(sections)


# ── Phase 1: CSS brand color extraction ────────────────────────────────────────
def extract_brand_colors_css(website: str) -> dict:
    """Extract brand colors via urllib CSS parsing.
    Priority: Elementor CSS custom properties → frequency-count hex scan → fallback.
    """
    try:
        req = urllib.request.Request(website, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return {"note": f"CSS extraction failed: {e}", "background": "#FFFFFF",
                "source": "css_extraction_failed"}

    # 1. Elementor global CSS custom properties (~70% of functional medicine sites)
    elementor_map = {
        "--e-global-color-primary":   "primary",
        "--e-global-color-accent":    "accent",
        "--e-global-color-secondary": "secondary",
        "--e-global-color-text":      "text",
    }
    colors: dict = {}
    for var, key in elementor_map.items():
        m = re.search(rf"{re.escape(var)}\s*:\s*(#[0-9a-fA-F]{{3,8}})", html)
        if m:
            colors[key] = m.group(1).upper()

    if len(colors) >= 2:
        colors.setdefault("background", "#FFFFFF")
        colors["source"] = "css_extraction_elementor"
        return colors

    # 2. Frequency-count all 6-digit hex colors, exclude near-black/near-white
    all_hex = re.findall(r"#([0-9a-fA-F]{6})\b", html)
    freq: dict = {}
    for h in all_hex:
        normalized = "#" + h.upper()
        r_val = int(h[0:2], 16)
        g_val = int(h[2:4], 16)
        b_val = int(h[4:6], 16)
        brightness = (r_val * 299 + g_val * 587 + b_val * 114) / 1000
        if 20 < brightness < 235:
            freq[normalized] = freq.get(normalized, 0) + 1
    top = sorted(freq, key=lambda k: freq[k], reverse=True)[:3]
    if top:
        result: dict = {"primary": top[0], "background": "#FFFFFF",
                        "source": "css_extraction_frequency"}
        if len(top) > 1:
            result["accent"] = top[1]
        if len(top) > 2:
            result["secondary"] = top[2]
        return result

    return {"note": "No colors detected via CSS", "background": "#FFFFFF",
            "source": "css_extraction_fallback"}


# ── Phase 1: robots/llms/sitemap ───────────────────────────────────────────────
def check_crawlability(website: str) -> dict:
    domain = re.sub(r"https?://", "", website).rstrip("/")
    results: dict = {}

    def fetch_robots():
        try:
            with urllib.request.urlopen(f"https://{domain}/robots.txt", timeout=5) as r:
                robots = r.read().decode("utf-8", errors="ignore")
            crawlers = ["GPTBot", "ChatGPT-User", "ClaudeBot", "PerplexityBot", "Google-Extended"]
            blocked = [c for c in crawlers if re.search(rf"User-agent:\s*{c}", robots, re.I)
                       and "Disallow: /" in robots]
            results["ai_status"] = "BLOCKING AI" if blocked else "AI ACCESSIBLE"
            results["blocked_crawlers"] = blocked
        except Exception:
            results["ai_status"] = "UNKNOWN"
            results["blocked_crawlers"] = []

    def fetch_llms():
        try:
            with urllib.request.urlopen(f"https://{domain}/llms.txt", timeout=5) as r:
                content = r.read().decode("utf-8", errors="ignore")
                results["llms_txt"] = "PRESENT" if ("# " in content or "http" in content) and len(content) < 50000 else "HTML_REDIRECT"
        except Exception:
            results["llms_txt"] = "NOT FOUND"

    def fetch_sitemap():
        try:
            with urllib.request.urlopen(f"https://{domain}/sitemap.xml", timeout=5) as r:
                sitemap = r.read().decode("utf-8", errors="ignore")
                results["sitemap_urls"] = len(re.findall(r"<loc>", sitemap))
        except Exception:
            results["sitemap_urls"] = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(fetch_robots), ex.submit(fetch_llms), ex.submit(fetch_sitemap)]
        concurrent.futures.wait(futs)
    return results


# ── Phase 1: SEMrush API fetch (live data, preferred) ──────────────────────────
# API unit cost per run: ~630 units
#   domain_rank          1 row  =   10 units  (+ free: Sh,St SERP Features traffic)
#   domain_organic      50 rows  =  500 units  (pos 1-20, nq_desc, + free: Fk,Fp AI Overview)
#   domain_organic_organic 3 rows = 120 units  (top competitors)
#   NOTE: Adding columns (Fk,Fp,Sh,St) is FREE — cost is per row only
def fetch_semrush_api(domain: str, api_key: str) -> dict:
    """Pull live SEMrush data. ~630 API units per call."""
    base = "https://api.semrush.com/"

    def api(params: dict) -> list[dict]:
        params["key"] = api_key
        qs = urllib.parse.urlencode(params)  # proper encoding of +, |, etc in filter strings
        req = urllib.request.Request(
            base + "?" + qs,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read().decode("utf-8")
            lines = raw.strip().split("\n")
            if len(lines) < 2:
                return []
            headers = [h.strip() for h in lines[0].split(";")]
            return [dict(zip(headers, l.split(";"))) for l in lines[1:] if l.strip()]
        except Exception:
            return []

    def safe_int(v):
        try: return int(str(v).replace(",", "").strip())
        except: return 0

    def safe_float(v):
        try: return float(str(v).replace(",", "").strip())
        except: return 0.0

    # Fire all 3 API calls in parallel — independent requests, no ordering constraint
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        fut_overview = ex.submit(api, {
            # Call 1: Domain overview — 10 units
            # Sh = SERP Features Traffic, St = SERP Features Traffic Cost
            "type": "domain_rank",
            "export_columns": "Dn,Rk,Or,Ot,Oc,Sh,St",
            "domain": domain,
            "database": "us",
        })
        fut_kw = ex.submit(api, {
            # Call 2: Top 50 keywords pos 1-20 sorted by volume — 500 units
            # Fk = SERP feature codes on SERP, Fp = codes held by this domain
            "type": "domain_organic",
            "export_columns": "Ph,Po,Nq,Kd,Fk,Fp",
            "domain": domain,
            "database": "us",
            "display_limit": "50",
            "display_sort": "nq_desc",
            "display_filter": "+|Po|Lt|21",   # positions 1-20 only
        })
        fut_comp = ex.submit(api, {
            # Call 3: Top 3 competitors — 120 units
            "type": "domain_organic_organic",
            "export_columns": "Dn,Cr,Or,Ot,Oc",
            "domain": domain,
            "database": "us",
            "display_limit": "3",
        })
        overview_rows = fut_overview.result()
        kw_rows       = fut_kw.result()
        comp_rows     = fut_comp.result()

    overview = overview_rows[0] if overview_rows else {}
    total_kws            = safe_int(overview.get("Organic Keywords",       "0"))
    traffic_est          = safe_int(overview.get("Organic Traffic",         "0"))
    traffic_val          = safe_int(overview.get("Organic Cost",            "0"))
    domain_rank          = safe_int(overview.get("Rank",                    "0"))
    serp_features_traffic = safe_int(overview.get("Sh",                     "0"))
    serp_features_value  = safe_int(overview.get("St",                      "0"))

    pos_dist = {1: 0, "2-3": 0, "4-10": 0, "11-20": 0}
    quick_wins, top3_sample = [], []
    ai_serp_count, ai_cited_count = 0, 0
    seen_kws = set()

    for r in kw_rows:
        kw  = r.get("Keyword", "").strip()
        pos = safe_int(r.get("Position", "999"))
        # SEMrush API returns full column names: Nq→"Search Volume", Kd→"Keyword Difficulty"
        # Fk→"SERP Features by Keyword", Fp→"SERP Features by Position"
        vol = safe_int(r.get("Search Volume", r.get("Nq", "0")))
        kd  = safe_float(r.get("Keyword Difficulty", r.get("Kd", "0")))

        # AI Overview tracking (code 20 = AI Overview block, 52 = AI Overview presence)
        fk_raw = r.get("SERP Features by Keyword", r.get("Fk", ""))
        fp_raw = r.get("SERP Features by Position", r.get("Fp", ""))
        # Values are comma-separated feature codes: e.g. "6,9,13,36,43,45,52"
        fk_codes = set(c.strip() for c in fk_raw.replace(";", ",").split(",") if c.strip())
        fp_codes = set(c.strip() for c in fp_raw.replace(";", ",").split(",") if c.strip())
        if "20" in fk_codes or "52" in fk_codes:
            ai_serp_count += 1
        if "20" in fp_codes or "52" in fp_codes:
            ai_cited_count += 1

        # Position distribution
        if pos == 1:       pos_dist[1] += 1
        elif pos <= 3:     pos_dist["2-3"] += 1
        elif pos <= 10:    pos_dist["4-10"] += 1
        elif pos <= 20:    pos_dist["11-20"] += 1

        if kw and kw not in seen_kws:
            seen_kws.add(kw)
            if 4 <= pos <= 10 and vol >= 100:
                quick_wins.append({"keyword": kw, "position": pos, "volume": vol, "kd": kd})
            if pos <= 3 and vol >= 50:
                top3_sample.append({"keyword": kw, "position": pos, "volume": vol})

    quick_wins.sort(key=lambda x: x["volume"], reverse=True)

    # Derive top_by_volume from Call 2 (already nq_desc sorted) — no extra call needed
    top_by_volume = [
        {"keyword": r.get("Keyword", ""), "position": safe_int(r.get("Position", "999")),
         "volume": safe_int(r.get("Search Volume", r.get("Nq", "0"))),
         "kd": safe_float(r.get("Keyword Difficulty", r.get("Kd", "0")))}
        for r in kw_rows
        if safe_int(r.get("Search Volume", r.get("Nq", "0"))) > 0
    ][:20]

    return {
        "source": "semrush_api",
        "units_used": 630,
        "domain_rank": domain_rank,
        "unique_keywords": total_kws,
        "estimated_traffic": traffic_est,
        "traffic_value": traffic_val,
        "serp_features_traffic": serp_features_traffic,
        "serp_features_value": serp_features_value,
        "ai_overview_serp_count": ai_serp_count,
        "ai_overview_cited_count": ai_cited_count,
        "pos1_count": pos_dist[1],
        "pos2_3_count": pos_dist["2-3"],
        "pos4_10_count": pos_dist["4-10"],
        "pos11_20_count": pos_dist["11-20"],
        "pos1_3_count": pos_dist[1] + pos_dist["2-3"],
        "quick_wins_count": len(quick_wins),
        "top_quick_wins": quick_wins[:15],
        "top3_sample": top3_sample[:10],
        "top_by_volume": top_by_volume,
        "competitors": [
            {"domain": r.get("Domain", ""), "relevance": r.get("Competitor Relevance", ""),
             "keywords": safe_int(r.get("Organic Keywords", "0")),
             "traffic": safe_int(r.get("Organic Traffic", "0")),
             "traffic_value": safe_int(r.get("Organic Cost", "0"))}
            for r in comp_rows
        ],
    }


# ── Phase 1: SEMrush CSV parse (fallback if no API key) ────────────────────────
def parse_semrush(csv_path: str) -> dict:
    if not csv_path or not os.path.exists(csv_path):
        return {"source": "none", "unique_keywords": 0, "quick_wins_count": 0,
                "estimated_traffic": 0, "traffic_value": 0,
                "top_quick_wins": [], "top3_sample": [], "top_by_volume": [],
                "competitors": [], "pos1_3_count": 0, "domain_rank": 0}

    def safe_int(v):
        try: return int(str(v).replace(",", "").strip())
        except: return 0

    def safe_float(v):
        try: return float(str(v).replace(",", "").strip())
        except: return 0.0

    rows = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    seen, unique = set(), []
    for r in rows:
        kw = r.get("Keyword", "").strip().lower()
        if kw and kw not in seen:
            seen.add(kw)
            unique.append(r)

    pos1_3 = [r for r in unique if safe_int(r.get("Position", 999)) <= 3]
    quick_wins = sorted(
        [r for r in unique if 4 <= safe_int(r.get("Position", 999)) <= 20
         and safe_int(r.get("Search Volume", 0)) >= 100],
        key=lambda r: safe_int(r.get("Search Volume", 0)), reverse=True
    )
    total_traffic = sum(safe_float(r.get("Traffic", 0)) for r in unique)

    return {
        "source": "csv",
        "unique_keywords": len(unique),
        "estimated_traffic": round(total_traffic),
        "traffic_value": 0,
        "domain_rank": 0,
        "pos1_3_count": len(pos1_3),
        "pos1_count": 0,
        "pos2_3_count": 0,
        "pos4_10_count": 0,
        "pos11_20_count": 0,
        "quick_wins_count": len(quick_wins),
        "top_quick_wins": [
            {"keyword": r.get("Keyword", ""), "position": r.get("Position", ""),
             "volume": r.get("Search Volume", ""), "url": r.get("URL", "")}
            for r in quick_wins[:15]
        ],
        "top3_sample": [{"keyword": r.get("Keyword", ""), "volume": r.get("Search Volume", "")}
                        for r in pos1_3[:10]],
        "top_by_volume": [],
        "competitors": [],
    }


# ── Phase 2: Merged Claude Sonnet 4.6 call ─────────────────────────────────────
CLAUDE_JSON_SCHEMA = """
{
  "keywords": ["string × 100 — local + national SEO keywords"],
  "ads": [
    {
      "campaign_name": "string",
      "target_audience": "string",
      "headlines": ["string × 5 (≤30 chars each)"],
      "descriptions": ["string (≤90 chars) × 2"],
      "keywords": ["[exact]", "\"phrase\"", "broad × 8-10 total"]
    }
  ],
  "ad_callouts": {
    "sitelinks": ["Label | /slug × 6"],
    "callout_extensions": ["string × 8"]
  },
  "emails": [
    {
      "email_number": 1,
      "type": "smart_practice_value_drop",
      "subject": "string",
      "preview": "string (≤45 chars)",
      "body": "string — 150-300 words, patient-facing, 2-3 short paragraphs",
      "cta_text": "string",
      "cta_url": "string (booking URL)"
    },
    {
      "email_number": 2,
      "type": "mechanism_story",
      "subject": "string",
      "preview": "string (≤45 chars)",
      "body": "string — 150-300 words, patient-facing, 2-3 short paragraphs",
      "cta_text": "string",
      "cta_url": "string (booking URL)"
    },
    {
      "email_number": 3,
      "type": "proof_and_results",
      "subject": "string",
      "preview": "string (≤45 chars)",
      "body": "string — 150-300 words, patient-facing, 2-3 short paragraphs",
      "cta_text": "string",
      "cta_url": "string (booking URL)"
    }
  ],
  "gamma_content": {
    "company": "string",
    "digital_health_report": "PASSTHROUGH — copy the PRE-BUILT DIGITAL HEALTH REPORT provided at the end of this prompt verbatim into this field. Do not modify, summarize, or regenerate it.",
    "ad_campaign1": "string (rich markdown)",
    "ad_campaign2": "string (rich markdown)",
    "ad_campaign3": "string (rich markdown)",
    "ad_callouts_slide": "string (rich markdown)",
    "email1": "string (rich markdown)",
    "email2": "string (rich markdown)",
    "email3": "string (rich markdown)",
    "assessment_url": "string"
  },
  "app_config": {
    "practiceName": "string",
    "practiceShortName": "string",
    "providerName": "string",
    "providerTitle": "string",
    "tagline": "string",
    "primaryColor": "#hex",
    "primaryDark": "#hex",
    "primaryLight": "#hex",
    "primaryXLight": "#hex",
    "backgroundColor": "#hex",
    "bookingUrl": "string",
    "phone": "string",
    "concerns": [{"label": "string", "emoji": "string"}],
    "symptoms": ["string × 20-24"],
    "careModels": [{"name": "string", "desc": "string", "price": "string"}]
  }
}
"""

def build_phase2_prompt(context: str, scrape: str, semrush: dict, crawl: dict,
                         brand_colors: dict, prebuilt_seo_report: str = "") -> str:
    color_summary = "\n".join([f"  - {k}: {v}" for k, v in brand_colors.items()])

    # Build SEMrush context block — provides data for keyword/ads/email generation
    qw_lines = "\n".join([
        f"  [pos {w['position']}] {w['keyword']} — {w['volume']:,}/mo  KD:{w.get('kd',0):.0f}"
        for w in semrush.get("top_quick_wins", [])[:10]
    ])
    top_vol_lines = "\n".join([
        f"  [pos {w['position']}] {w['keyword']} — {w['volume']:,}/mo  KD:{w.get('kd',0):.0f}"
        for w in semrush.get("top_by_volume", [])[:20]
    ])
    comp_lines = "\n".join([
        f"  {c['domain']}: {c['keywords']:,} KWs, {c['traffic']:,} traffic/mo, ${c['traffic_value']:,} value"
        for c in semrush.get("competitors", [])[:5]
    ])
    pos_dist = (
        f"  Pos #1:      {semrush.get('pos1_count', semrush.get('pos1_3_count',0))} keywords (branded)\n"
        f"  Pos #2-3:    {semrush.get('pos2_3_count', 0)} keywords\n"
        f"  Pos #4-10:   {semrush.get('pos4_10_count', 0)} keywords ← page 1, low CTR\n"
        f"  Pos #11-20:  {semrush.get('pos11_20_count', 0)} keywords ← page 2, near-zero CTR\n"
        f"  Pos #21+:    ~{max(0, semrush.get('unique_keywords',0) - semrush.get('pos4_10_count',0) - semrush.get('pos11_20_count',0) - semrush.get('pos1_3_count',0)):,} keywords"
    )

    # AI Overview coverage (free Fk/Fp columns from domain_organic)
    ai_serp  = semrush.get("ai_overview_serp_count", "N/A")
    ai_cited = semrush.get("ai_overview_cited_count", "N/A")
    sf_traffic = semrush.get("serp_features_traffic", 0)

    semrush_block = f"""SEMRUSH DATA (live API — 630 units):
Domain Snapshot:
  Global Rank:       #{semrush.get('domain_rank', 0):,}
  Keywords Ranked:   {semrush.get('unique_keywords', 0):,}
  Monthly Traffic:   ~{semrush.get('estimated_traffic', 0):,} visits
  Traffic Value:     ${semrush.get('traffic_value', 0):,}/mo
  Data Source:       {semrush.get('source', 'unknown')}

Position Distribution (pos 1-20 sample):
{pos_dist}

AI Overview Coverage (Google AI search):
  Keywords triggering AI Overview on SERP: {ai_serp}
  Keywords where this practice is cited:   {ai_cited}
  SERP Features Traffic:                  ~{sf_traffic:,} visits/mo

Top Keywords by Volume:
{top_vol_lines or '  (CSV mode — see quick wins)'}

Page-1 Quick Wins (pos 4-10, vol ≥100):
{qw_lines or '  (none identified)'}

Top Organic Competitors:
{comp_lines or '  (not available)'}"""

    seo_section = ""
    if prebuilt_seo_report.strip():
        seo_section = f"""
PRE-BUILT DIGITAL HEALTH REPORT — copy this VERBATIM into gamma_content.digital_health_report:
{prebuilt_seo_report}
"""

    return f"""You are a healthcare digital marketing expert building a Dream 100 sales presentation package.

PRACTICE CONTEXT (provided by sales team):
{context}

SCRAPED WEBSITE CONTENT:
{scrape[:6000]}

{semrush_block}

TECHNICAL INTEL:
- AI Crawlers: {crawl.get('ai_status', 'UNKNOWN')}
- Blocked crawlers: {', '.join(crawl.get('blocked_crawlers', [])) or 'None'}
- llms.txt: {crawl.get('llms_txt', 'UNKNOWN')}
- Sitemap URLs: {crawl.get('sitemap_urls', 0)}

BRAND COLORS (from live CSS):
{color_summary or '  (not extracted — use reasonable defaults)'}

Generate a complete JSON object with ALL fields below. Return ONLY valid JSON, no markdown, no explanation.

{CLAUDE_JSON_SCHEMA}

CRITICAL RULES:
- Return ONLY valid JSON. No markdown code fences. No explanation.
- Fill ALL fields with real content — no placeholder text
- Emails are PATIENT-FACING nurture emails sent BY the practice TO prospective patients after health assessment completion. NOT B2B outreach. NOT addressed to the doctor.
- Email 1 (smart_practice_value_drop): empathetic opening for [FIRST_NAME] referencing [PRIMARY_SYMPTOM], one high-value root-cause insight, why generic care often misses it, soft booking CTA
- Email 2 (mechanism_story): simple analogy explaining the biological mechanism behind symptoms, what standard care typically misses, position practice approach as different — no guarantees or claims
- Email 3 (proof_and_results): short anonymized patient story with similar symptom pattern, what changed when root cause was addressed, results-vary disclaimer, clear calm booking CTA
- Use personalization variables: [FIRST_NAME], [PRIMARY_SYMPTOM], [KEY_ASSESSMENT_INSIGHT], [RECOMMENDED_SERVICE_OR_FOCUS], [BOOKING_LINK]
- 150-300 words per email. Short paragraphs. No emojis. No aggressive urgency. Sign off as the practice name or care team.
- Keywords: exactly 100 unique strings
- gamma_content.digital_health_report: copy the PRE-BUILT REPORT below EXACTLY as-is — do not regenerate or modify it
- DO NOT include any YouTube or Calendly URLs anywhere in output
- JSON SAFETY: NEVER use double-quote characters (") inside string values. Ad headlines, email copy, and descriptions must use single quotes (') or rephrase without internal quotation marks. Unescaped double quotes break JSON parsing.
{seo_section}"""


def repair_json(text: str) -> str:
    """Best-effort JSON repair for common Claude output issues."""
    # 1. Strip trailing commas before } or ]
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    # 2. If JSON is truncated mid-string, try to close it cleanly
    #    Count open braces/brackets and append closers if needed
    try:
        json.loads(text)
        return text  # already valid
    except json.JSONDecodeError:
        pass
    # Close any open structures by finding the deepest valid prefix
    stack = []
    in_string = False
    escape_next = False
    last_valid_pos = 0
    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]":
                if stack and stack[-1] == ch:
                    stack.pop()
                    last_valid_pos = i + 1
    # Truncate to last valid position and close all open structures
    if last_valid_pos > 0 and stack:
        text = text[:last_valid_pos] + "".join(reversed(stack))
    return text


# call_claude() removed — all LLM generation is done natively by Claude Code (Claude Max, no API billing).
# Phase 2 writes phase1_data.json; Claude Code generates phase2_output.json natively.
# Phase 1.5 reads seo_report.md written by Claude Code natively.


# ── Phase 1.5: Inline SEO analysis via Claude Sonnet 4.6 ──────────────────────
def build_seo_analysis_prompt(semrush: dict, scrape: str, crawl: dict) -> str:
    """Build the SKILL_D100_seo_analysis prompt from live data."""
    qw_lines = "\n".join([
        f"[pos {w['position']}] {w['keyword']} — {w.get('volume', 0):,}/mo  KD:{w.get('kd', 0):.0f}"
        for w in semrush.get("top_quick_wins", [])[:6]
    ])
    top_vol_lines = "\n".join([
        f"[pos {w['position']}] {w['keyword']} — {w.get('volume', 0):,}/mo  KD:{w.get('kd', 0):.0f}"
        for w in semrush.get("top_by_volume", [])[:20]
    ])
    comp_lines = "\n".join([
        f"  {c['domain']}: {c['keywords']:,} KWs, {c['traffic']:,} traffic/mo, ${c['traffic_value']:,} value"
        for c in semrush.get("competitors", [])[:3]
    ])
    return f"""You are a senior healthcare SEO analyst reviewing a practice's digital footprint. Generate a Digital Health Report using ONLY the numbers provided below — never estimate or fabricate.

SEMRUSH DATA:
  Global Rank:           #{semrush.get('domain_rank', 0):,}
  Keywords Ranked:       {semrush.get('unique_keywords', 0):,}
  Monthly Traffic:       ~{semrush.get('estimated_traffic', 0):,} visits
  Traffic Value:         ${semrush.get('traffic_value', 0):,}/mo
  Pos #1:                {semrush.get('pos1_count', 0)} keywords
  Pos #2-3:              {semrush.get('pos2_3_count', 0)} keywords
  Pos #4-10:             {semrush.get('pos4_10_count', 0)} keywords
  Pos #11-20:            {semrush.get('pos11_20_count', 0)} keywords
  AI Overview SERPs:     {semrush.get('ai_overview_serp_count', 'N/A')}
  AI Overview Cited:     {semrush.get('ai_overview_cited_count', 'N/A')}
  SERP Features Traffic: ~{semrush.get('serp_features_traffic', 0):,} visits/mo

TOP KEYWORDS BY VOLUME:
{top_vol_lines or '  (not available)'}

PAGE-1 QUICK WINS (pos 4-10, vol ≥100):
{qw_lines or '  (none identified)'}

TOP COMPETITORS:
{comp_lines or '  (not available)'}

TECHNICAL:
  AI Crawlers:  {crawl.get('ai_status', 'UNKNOWN')}
  llms.txt:     {crawl.get('llms_txt', 'UNKNOWN')}
  Sitemap URLs: {crawl.get('sitemap_urls', 0)}

WEBSITE CONTEXT (skim for practice name, specialty, providers):
{scrape[:2000]}

Generate the 7-section Digital Health Report using this EXACT format (400-600 words total):

🔎 DIGITAL SEO HEALTH REPORT — [domain]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 DOMAIN SNAPSHOT
──────────────────
[markdown table with columns Metric | Value: Global Rank, Keywords Ranked, Monthly Traffic, Traffic Value, Keywords in Top 10, SERP Features Traffic]

🔑 THE CORE FINDING: [FINDING IN CAPS]
──────────────────────────────────────────────────────
[Lead with the most striking number. Show position breakdown bullets. One-sentence interpretation.]

🤖 AI SEARCH GAP
──────────────────
[ONLY include if ai_overview_serp_count > 0. Show gap between SERPs triggering AI Overview vs cited count.]

🎯 BIGGEST OPPORTUNITY: [CLUSTER NAME IN CAPS]
──────────────────────────────────────────────────────
[Highest-value non-branded keyword cluster from top_by_volume. List top 5-7 keywords in [pos X] format. One-sentence why.]

⚡ WITHIN STRIKING DISTANCE (pos 4-10)
──────────────────────────────────────
[Top 5-6 quick wins. → Highest priority: one sentence on best single win.]

🏆 VS YOUR TOP COMPETITOR
──────────────────────────
[ONLY include if competitors available. Head-to-head table. One punchy conclusion.]

🎯 3-PRIORITY ATTACK PLAN
──────────────────────────
[3 numbered priorities grounded in specific numbers from above. Each: name in caps, one-line tactic, target + timeframe.]

Rules: Verbatim numbers only. Doctor's report tone. No SEO jargon. No fluff. 400-600 words."""


# run_seo_analysis_inline() removed — SEO report is generated natively by Claude Code.
# Runner writes phase1_data.json; Claude Code reads build_seo_analysis_prompt() and writes seo_report.md.


# ── Phase 3: GitHub Pages deploy ───────────────────────────────────────────────

def make_deliverable_slug(practice_name: str) -> str:
    """Plug-and-play-AI-SEO-and-Ad-Strategy-for-{Company-Name-Slug}"""
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", practice_name).strip()
    return DELIVERABLES_SLUG_PREFIX + "-".join(clean.split())


def deploy_report_to_github(run_dir, practice_name: str, dry_run: bool = False) -> str:
    """Deploy seo_report.html to GitHub Pages. Returns live URL."""
    import subprocess, shutil, tempfile

    slug = make_deliverable_slug(practice_name)
    report_path = Path(run_dir) / "seo_report.html"

    if not report_path.exists():
        raise RuntimeError(f"seo_report.html not found in {run_dir}")
    if report_path.stat().st_size < 10_000:
        raise RuntimeError(f"seo_report.html too small ({report_path.stat().st_size} bytes) — build may have failed")

    if dry_run:
        print(f"  [DRY RUN] Would deploy {slug} to GitHub Pages")
        return f"https://DRY-RUN.github.io/{slug}/"

    def run(cmd, **kwargs):
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
        return result.stdout.strip()

    # Get GitHub username
    ghuser = run("gh api user --jq '.login'")
    if not ghuser:
        raise RuntimeError("Could not determine GitHub username via gh CLI")

    # Create repo (idempotent — ok if already exists)
    try:
        run(f"gh repo create {ghuser}/{slug} --public --confirm 2>/dev/null || true")
    except Exception:
        pass  # Repo may already exist

    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone (empty is fine — Pages just needs index.html on main)
        try:
            run(f"git clone https://github.com/{ghuser}/{slug}.git {tmpdir}/repo")
            repo_dir = f"{tmpdir}/repo"
        except Exception:
            # Fresh repo: init locally
            repo_dir = f"{tmpdir}/repo"
            os.makedirs(repo_dir, exist_ok=True)
            run(f"git -C {repo_dir} init")
            run(f"git -C {repo_dir} remote add origin https://github.com/{ghuser}/{slug}.git")

        # Copy seo_report.html as index.html
        shutil.copy(str(report_path), f"{repo_dir}/index.html")

        # Commit & push
        run(f"git -C {repo_dir} add index.html")
        run(f'git -C {repo_dir} -c user.email="d100@aiaa.app" -c user.name="D100 Runner" commit --allow-empty -m "D100 deliverables page — {practice_name}"')
        run(f"git -C {repo_dir} push --force origin HEAD:main")

    # Enable GitHub Pages on main branch
    try:
        run(f'gh api repos/{ghuser}/{slug}/pages --method POST -f source[branch]=main -f source[path]=/ 2>/dev/null || true')
    except Exception:
        pass  # Pages may already be enabled

    live_url = f"https://{ghuser}.github.io/{slug}/"
    print(f"  ✓ Deployed → {live_url}")
    return live_url


# ── Phase 3: Slack notifications ────────────────────────────────────────────────

def _slack_post(webhook: str, msg: dict) -> bool:
    req = urllib.request.Request(
        webhook,
        data=json.dumps(msg).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status == 200


def notify_slack_report_live(webhook: str, practice: str, report_url: str,
                              website: str, semrush: dict, run_id: str) -> bool:
    ai_serp  = semrush.get("ai_overview_serp_count", "N/A")
    ai_cited = semrush.get("ai_overview_cited_count", "N/A")
    msg = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text",
                "text": f"📊 D100 Report Live — {practice}"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Website:*\n{website}"},
                {"type": "mrkdwn", "text": f"*Run ID:*\n`{run_id}`"},
                {"type": "mrkdwn", "text": f"*Keywords Ranked:*\n{semrush.get('unique_keywords', 0):,}"},
                {"type": "mrkdwn", "text": f"*Quick Wins:*\n{semrush.get('quick_wins_count', 0)}"},
                {"type": "mrkdwn", "text": f"*Traffic Value:*\n${semrush.get('traffic_value', 0):,}/mo"},
                {"type": "mrkdwn", "text": f"*AI Overview Gap:*\n{ai_serp} SERPs, cited in {ai_cited}"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn",
                "text": f"*Deliverables Page:*\n<{report_url}|{report_url}>"}},
        ],
    }
    return _slack_post(webhook, msg)


def notify_slack_error(webhook: str, name: str, website: str, failure_type: str,
                       error: str, run_id: str) -> bool:
    """Send error alert to Slack. failure_type: SCRAPE_FAILED | SEMRUSH_FAILED | BUILD_FAILED"""
    msg = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text",
                "text": f"🔴 D100 Error — {name}"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Website:*\n{website}"},
                {"type": "mrkdwn", "text": f"*Failure Type:*\n`{failure_type}`"},
                {"type": "mrkdwn", "text": f"*Run Dir:*\n`output/d100_runs/{run_id}/`"},
                {"type": "mrkdwn", "text": f"*Error:*\n{error[:300]}"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn",
                "text": "Next: skipping to next URL"}},
        ],
    }
    try:
        return _slack_post(webhook, msg)
    except Exception:
        return False


def notify_slack_critical(webhook: str, message: str) -> bool:
    """Send circuit-breaker critical alert."""
    msg = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "🛑 D100 HALTED"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": message}},
        ],
    }
    try:
        return _slack_post(webhook, msg)
    except Exception:
        return False


# Legacy shim — kept so old Gamma function references don't crash if called
def build_gamma_prompt(gamma_content: dict) -> str:
    gc = gamma_content
    return f"""[COMPANY]
{gc['company']}

[DIGITAL_HEALTH_REPORT]
{gc['digital_health_report']}

[AD_CAMPAIGN1]
{gc['ad_campaign1']}

[AD_CAMPAIGN2]
{gc['ad_campaign2']}

[AD_CAMPAIGN3]
{gc['ad_campaign3']}

[AD_CALLOUTS]
{gc['ad_callouts_slide']}

[EMAIL1]
{gc['email1']}

[EMAIL2]
{gc['email2']}

[EMAIL3]
{gc['email3']}

[ASSESSMENT_URL]
{gc['assessment_url']}"""


def extract_booking_url(markdown: str, base_url: str) -> str:
    """Scan scraped markdown for booking/scheduling links. Returns absolute URL or empty string."""
    import re as _re
    base = base_url.rstrip("/")
    # Patterns that signal a booking link (text or URL fragment)
    text_kw = _re.compile(
        r"book|schedul|appointment|new.patient|portal|consult|intake|request.appoint",
        _re.I
    )
    url_kw = _re.compile(
        r"/book|/schedul|/appointment|/new.patient|/portal|/consult|/intake",
        _re.I
    )
    # Extract all markdown links: [text](url)
    for text, url in _re.findall(r"\[([^\]]+)\]\(([^)]+)\)", markdown):
        if text_kw.search(text) or url_kw.search(url):
            url = url.strip()
            if url.startswith("http"):
                return url
            if url.startswith("/"):
                return base + url
    # Fallback: bare URLs in text
    for url in _re.findall(r"https?://\S+", markdown):
        if url_kw.search(url):
            return url.rstrip(")")
    return ""


def submit_gamma(prompt: str, api_key: str) -> str:
    payload = json.dumps({
        "gammaId": GAMMA_TEMPLATE_ID,
        "prompt": prompt,
        # "additionalInstructions" removed — no longer accepted by Gamma API as of 2026-02
    }).encode()
    headers = {**GAMMA_HEADERS_BASE, "X-API-KEY": api_key}
    req = urllib.request.Request(
        f"{GAMMA_API}/generations/from-template",
        data=payload,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return data.get("generationId", "")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"Gamma API HTTP {e.code}: {error_body}") from e



# ── Phase 3b: Native app builder via Claude Sonnet 4.6 ────────────────────────
APP_BUILDER_PROMPT = """You are a senior product designer + conversion copywriter + front-end engineer + healthcare-compliance-minded UX writer.

PRIMARY OBJECTIVE
Using ONLY the context and content I provide (no assumptions, no inference), produce a "Dream 100" demo experience that combines:
1) A premium patient-acquisition landing page for {company_name}, and
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
- USE BRAND COLORS: {brand_colors}
- ENSURE ALL MULTI-SELECT BUTTONS ACTUALLY ALLOW MULTIPLE SELECTABLE ITEMS (AND ALLOW USER TO DE-SELECT)

---

CONTEXT (FROM WEBSITE + STRUCTURED CONFIG):
{context_block}

USER CONFIGURATION:
{{
  "booking_objective": "New patient consultation",
  "location_constraints": "Single location",
  "social_proof": "Yes",
  "assessment_depth": "Standard",
  "required_fields": ["name", "email", "phone"],
  "redirect_method": "Copy-to-clipboard + redirect",
  "payload_fields": ["name", "email", "phone", "primary_concern", "symptoms", "duration", "severity"],
  "payload_char_limit": 500,
  "end_state_behavior": "Review + recommendations + next steps",
  "booking_routing": "One link for all services",
  "legal_text": "Use standard healthcare disclaimer",
  "booking_url": "{booking_url}"
}}

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


# NOTE: App building is done natively by Claude Code (covered by Claude Max).
# See APP_BUILDER_PROMPT above for the prompt — Claude Code reads it directly.
# Runner writes app_build_pending.json; user triggers "build the apps" in Claude Code.


# notify_slack_submit kept as shim for any direct callers
def notify_slack_submit(webhook, practice, gen_id, website, semrush, run_id):
    return notify_slack_report_live(webhook, practice, f"PENDING:{gen_id}", website, semrush, run_id)


# ── Main run logic (single site) ───────────────────────────────────────────────
def run_single(row: dict, env: dict, dry_run: bool = False,
               phase1_only: bool = False,
               existing_run_dir: str = None) -> dict:
    website = row.get("website", "").rstrip("/")
    context = row.get("context", "")
    # booking_url and semrush_csv are auto-resolved — not required in CSV
    semrush_csv = row.get("semrush_csv", "")

    # Support resuming from an existing run_dir (for --phase1-only → SEO step → phase2-4 flow)
    if existing_run_dir:
        run_dir = Path(existing_run_dir)
        run_id = run_dir.name
    else:
        slug = re.sub(r"https?://", "", website).replace("/", "").replace(".", "-")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{slug}_{ts}"
        run_dir = OUTPUT_ROOT / run_id

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "scrape_data").mkdir(exist_ok=True)
    (run_dir / "seo_data").mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"🚀 D100 v3.2 — {website}")
    print(f"   Run ID: {run_id}")
    if phase1_only:
        print(f"   Mode: Phase 1 only (data collection → phase1_data.json)")
    elif existing_run_dir:
        print(f"   Mode: Phase 3 only (using existing phase2_output.json)")
    print(f"{'='*60}")

    # ── PHASE 1 ────────────────────────────────────────────────────────────────
    scrape_path = run_dir / "scrape_data" / "raw_scrape.md"
    semrush_data_path = run_dir / "semrush_data.json"

    # Skip Phase 1 data collection if resuming (files already exist)
    seo_report_path = run_dir / "seo_report.md"
    if semrush_data_path.exists() and scrape_path.exists() and seo_report_path.exists():
        print("\n📡 Phase 1: Loading cached data...")
        raw_scrape = scrape_path.read_text(encoding="utf-8")
        semrush = json.loads(semrush_data_path.read_text(encoding="utf-8"))
        crawl_path = run_dir / "crawl_data.json"
        crawl = json.loads(crawl_path.read_text(encoding="utf-8")) if crawl_path.exists() else {}
        print(f"  ✓ Loaded from cache: {semrush['unique_keywords']:,} KWs | {semrush['quick_wins_count']} quick wins")
    else:
        print("\n📡 Phase 1: Collecting data...")
        t0 = time.time()

        print("  Scraping website...")
        raw_scrape = scrape_site(website)
        scrape_path.write_text(raw_scrape, encoding="utf-8")
        print(f"  ✓ Scraped {len(raw_scrape):,} chars")

        # Auto-detect booking URL and inject into context
        booking_url = extract_booking_url(raw_scrape, website)
        if booking_url:
            context = f"{context}\nBooking URL: {booking_url}" if context else f"Booking URL: {booking_url}"
            print(f"  ✓ Booking URL detected: {booking_url}")
        else:
            print(f"  ⚠️  Booking URL not detected — Claude will infer from scraped content")

        print("  Checking robots.txt / llms.txt...")
        crawl = check_crawlability(website)
        (run_dir / "crawl_data.json").write_text(
            json.dumps(crawl, indent=2), encoding="utf-8"
        )
        print(f"  ✓ AI: {crawl['ai_status']} | llms.txt: {crawl['llms_txt']} | Sitemap: {crawl['sitemap_urls']} URLs")

        semrush_key = env.get("SEMRUSH_API_KEY", "").strip()
        domain = re.sub(r"https?://", "", website).rstrip("/")
        if semrush_key:
            print("  Fetching SEMrush API (~630 units)...")
            try:
                semrush = fetch_semrush_api(domain, semrush_key)
                ai_serp  = semrush.get("ai_overview_serp_count", "N/A")
                ai_cited = semrush.get("ai_overview_cited_count", "N/A")
                print(f"  ✓ API: {semrush['unique_keywords']:,} KWs | #{semrush['domain_rank']:,} rank | "
                      f"{semrush['quick_wins_count']} quick wins | ${semrush['traffic_value']:,}/mo | "
                      f"AI Overview SERPs: {ai_serp} (cited: {ai_cited})")
            except Exception as e:
                print(f"  ⚠️  SEMrush API failed ({e}), falling back to CSV...")
                semrush = parse_semrush(semrush_csv)
        else:
            print("  Parsing SEMrush CSV (no API key — add SEMRUSH_API_KEY to .env for live data)...")
            semrush = parse_semrush(semrush_csv)
        print(f"  ✓ {semrush['unique_keywords']:,} keywords | {semrush['quick_wins_count']} quick wins | ~{semrush['estimated_traffic']:,} traffic/mo")

        # Save SEMrush data for Claude Code SEO analysis step
        semrush_data_path.write_text(
            json.dumps(semrush, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        print(f"  Phase 1 complete ({time.time()-t0:.1f}s)")

    # Brand colors: Puppeteer-extracted file takes priority; otherwise auto-extract via CSS
    brand_colors_path = run_dir / "brand_colors.json"
    if brand_colors_path.exists():
        brand_colors = json.loads(brand_colors_path.read_text(encoding="utf-8"))
        print(f"  ✓ Brand colors loaded from brand_colors.json (pre-extracted)")
    else:
        print(f"  Extracting brand colors via CSS ({website})...")
        brand_colors = extract_brand_colors_css(website)
        brand_colors_path.write_text(json.dumps(brand_colors, indent=2, ensure_ascii=False), encoding="utf-8")
        n_colors = len([v for v in brand_colors.values() if str(v).startswith("#")])
        print(f"  ✓ Brand colors extracted ({n_colors} colors, method: {brand_colors.get('source', 'unknown')})")

    # ── PHASE 1-ONLY EXIT ──────────────────────────────────────────────────────
    if phase1_only or dry_run:
        if phase1_only:
            print(f"\n⏸  Phase 1 complete. Data saved to: {run_dir}")
            print(f"   Next step: Claude Code SEO analysis skill → writes seo_report.md")
            print(f"   Then run: python3 d100_v3_runner.py --csv <file> --run-dir {run_dir} --seo-report {run_dir}/seo_report.md")
        else:
            print("\n⚠️  DRY RUN — skipping LLM calls and API submissions")
        return {
            "run_id": run_id,
            "status": "phase1_complete" if phase1_only else "dry_run",
            "website": website,
            "run_dir": str(run_dir),
            "keywords": semrush.get("unique_keywords", 0),
            "quick_wins": semrush.get("quick_wins_count", 0),
        }

    # ── PHASE 1.5: SEO report (written natively by Claude Code) ────────────────
    seo_report_file = run_dir / "seo_report.md"
    if seo_report_file.exists():
        # Claude Code already generated it — load it
        prebuilt_seo_report = seo_report_file.read_text(encoding="utf-8")
        print(f"\n📊 Phase 1.5: SEO report loaded ({len(prebuilt_seo_report):,} chars)")
    else:
        # Not yet generated — runner writes phase1_data.json; Claude Code generates natively
        prebuilt_seo_report = ""
        print(f"\n📊 Phase 1.5: SEO report pending — Claude Code will generate natively")

    # ── PHASE 2 ────────────────────────────────────────────────────────────────
    phase2_output_path = run_dir / "phase2_output.json"
    if phase2_output_path.exists():
        # Pre-generated by Claude Code natively — skip API call
        phase2_data = json.loads(phase2_output_path.read_text(encoding="utf-8"))
        print(f"\n🤖 Phase 2: Loaded from existing phase2_output.json ({len(phase2_data)} keys)")
    else:
        # Write phase1_data.json so Claude Code can generate phase2_output.json natively (Claude Max — zero API cost)
        phase1_data = {
            "context": context,
            "raw_scrape": raw_scrape[:6000] if raw_scrape else "",
            "semrush": semrush,
            "crawl": crawl,
            "brand_colors": brand_colors,
            "prebuilt_seo_report": prebuilt_seo_report,
            "run_id": run_id,
            "website": website,
        }
        (run_dir / "phase1_data.json").write_text(
            json.dumps(phase1_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\n🤖 Phase 2: Pending — Claude Code will generate natively (see phase1_data.json)")
        # Return early — Phase 3 (Gamma) requires phase2_output.json
        return {
            "run_id": run_id,
            "status": "phase2_pending",
            "website": website,
            "gamma_url": "",
            "keywords_count": 0,
            "quick_wins": semrush.get("quick_wins_count", 0),
            "traffic_value": semrush.get("traffic_value", 0),
            "ai_overview_serp_count": semrush.get("ai_overview_serp_count", "N/A"),
        }

    print(f"  Quick wins: {semrush.get('quick_wins_count', 0)}")

    # ── PHASE 3: Deploy deliverables page to GitHub Pages ───────────────────────
    print("\n🚀 Phase 3: Deploying deliverables page to GitHub Pages...")
    t3 = time.time()

    # Extract practice name from phase2 app_config (fallback: gamma_content or website)
    practice_name = (
        phase2_data.get("app_config", {}).get("practiceName")
        or phase2_data.get("gamma_content", {}).get("company")
        or re.sub(r"https?://", "", website).rstrip("/")
    )
    slack_webhook = env.get("SLACK_WEBHOOK_URL", "")

    # Verify seo_report.html exists and is large enough
    report_path = run_dir / "seo_report.html"
    if not report_path.exists():
        raise RuntimeError(
            f"BUILD_FAILED: seo_report.html not found in {run_dir}. "
            "Claude Code must build it first (run SKILL_D100_report_builder)."
        )
    if report_path.stat().st_size < 10_000:
        raise RuntimeError(
            f"BUILD_FAILED: seo_report.html too small ({report_path.stat().st_size} bytes). "
            "Build likely failed or was incomplete."
        )
    print(f"  ✓ seo_report.html ready — {report_path.stat().st_size // 1024}KB")

    # Deploy to GitHub Pages
    report_url = deploy_report_to_github(run_dir, practice_name, dry_run=dry_run)
    print(f"  ✓ Live URL: {report_url}")
    print(f"  Phase 3 complete ({time.time()-t3:.1f}s)")

    # Write report_url to phase2_output.json
    try:
        p2 = json.loads((run_dir / "phase2_output.json").read_text(encoding="utf-8"))
        p2["report_url"] = report_url
        (run_dir / "phase2_output.json").write_text(
            json.dumps(p2, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass

    # Shim: write gamma_response.json so downstream scripts don't break
    (run_dir / "gamma_response.json").write_text(
        json.dumps({"report_url": report_url, "practice": practice_name, "run_id": run_id}, indent=2),
        encoding="utf-8",
    )

    # Slack success
    if slack_webhook:
        try:
            notify_slack_report_live(slack_webhook, practice_name, report_url, website, semrush, run_id)
            print("  ✓ Slack notified")
        except Exception as e:
            print(f"  ⚠️  Slack failed: {e}")

    # ── Summary ────────────────────────────────────────────────────────────────
    files = list(run_dir.rglob("*"))
    file_list = [str(f.relative_to(run_dir)) for f in files if f.is_file()]
    print(f"\n✅ COMPLETE — {run_id}")
    print(f"   Report: {report_url}")
    print(f"   Files: {', '.join(file_list)}")

    return {
        "run_id": run_id,
        "status": "completed",
        "website": website,
        "report_url": report_url,
        "gamma_url": report_url,   # shim — CSV column kept for backward compat
        "keywords_count": len(phase2_data.get("keywords", [])),
        "quick_wins": semrush.get("quick_wins_count", 0),
        "traffic_value": semrush.get("traffic_value", 0),
        "ai_overview_serp_count": semrush.get("ai_overview_serp_count", "N/A"),
    }


# ── Main ───────────────────────────────────────────────────────────────────────
def find_run_dir_for_site(website: str):
    """Find the most recent run dir for a website that has phase2_output.json ready."""
    slug = re.sub(r"https?://", "", website.rstrip("/")).replace("/", "").replace(".", "-")
    candidates = sorted(
        [d for d in OUTPUT_ROOT.iterdir()
         if d.is_dir() and d.name.startswith(slug) and (d / "phase2_output.json").exists()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return str(candidates[0]) if candidates else None


def main():
    parser = argparse.ArgumentParser(description="D100 v3.2 Batch Runner")
    parser.add_argument("--csv", required=True, help="Path to practices CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Skip all API calls")
    parser.add_argument("--site-index", type=int, default=None, help="Run only this row index (0-based)")
    parser.add_argument("--phase1-only", action="store_true",
                        help="Run Phase 1 only (scrape + SEMrush + crawl). Writes phase1_data.json. "
                             "Claude Code then generates seo_report.md + phase2_output.json natively.")
    parser.add_argument("--phase3-only", action="store_true",
                        help="Skip Phase 1+2. Find existing run dirs with phase2_output.json and "
                             "run Phase 3 (Gamma submit + Slack) only.")
    parser.add_argument("--run-dir", type=str, default=None,
                        help="Existing run directory to use (single-site override for --phase3-only).")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        sys.exit(1)

    env = load_env()
    semrush_status = "✓ (API)" if env.get("SEMRUSH_API_KEY") else "✗ (CSV fallback)"
    print(f"✓ Env loaded: SEMrush={semrush_status} | "
          f"Slack={'✓' if env.get('SLACK_WEBHOOK_URL') else '✗'}")
    print(f"  Note: All LLM generation is Claude Code native (Claude Max — zero API cost)")
    print(f"  Note: Phase 3 deploys to GitHub Pages (Gamma replaced)")

    with open(args.csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("ERROR: CSV is empty")
        sys.exit(1)

    if args.site_index is not None:
        rows = [rows[args.site_index]]
        print(f"Running single site: index {args.site_index}")
    else:
        print(f"Running {len(rows)} site(s) from CSV")

    # ── Run all sites ────────────────────────────────────────────────────────────
    n = len(rows)
    results = []
    consecutive_failures = 0
    FAILURE_LIMIT = 3
    slack_webhook = env.get("SLACK_WEBHOOK_URL", "")

    for i, row in enumerate(rows):
        label = f"[{i+1}/{n}]"
        website = row.get("website", "?")
        context = row.get("context", "")
        # Best-effort practice name from context (before run_single parses it)
        practice_name_hint = context.split(";")[0].strip() if context else website
        print(f"\n{label} {website}")

        # --phase3-only: resolve existing run dir automatically per site
        existing_run_dir = args.run_dir
        if args.phase3_only and not existing_run_dir:
            existing_run_dir = find_run_dir_for_site(website)
            if not existing_run_dir:
                print(f"  ⚠️  No run dir with phase2_output.json found for {website} — skipping")
                results.append({"website": website, "status": "skipped_no_phase2", "report_url": ""})
                continue
            print(f"  📁 Using run dir: {existing_run_dir}")

        run_id_hint = Path(existing_run_dir).name if existing_run_dir else "unknown"

        try:
            result = run_single(
                row, env,
                dry_run=args.dry_run,
                phase1_only=args.phase1_only,
                existing_run_dir=existing_run_dir,
            )
            results.append(result)
            # Reset circuit breaker on any success (even phase2_pending counts)
            if result.get("status") not in ("failed", "scrape_failed", "semrush_failed", "build_failed"):
                consecutive_failures = 0

        except Exception as e:
            err_str = str(e)
            print(f"  ❌ FAILED: {err_str}")

            # Classify failure type from error message
            if "SCRAPE_FAILED" in err_str or "scrape" in err_str.lower():
                failure_type = "SCRAPE_FAILED"
            elif "SEMRUSH_FAILED" in err_str or "semrush" in err_str.lower():
                failure_type = "SEMRUSH_FAILED"
            elif "BUILD_FAILED" in err_str or "seo_report" in err_str.lower():
                failure_type = "BUILD_FAILED"
            else:
                failure_type = "BUILD_FAILED"  # default for phase 3 errors

            result = {
                "website": website,
                "status": failure_type.lower(),
                "error": err_str[:500],
                "report_url": "",
                "gamma_url": "",
            }
            results.append(result)

            # Slack error alert
            if slack_webhook:
                notify_slack_error(slack_webhook, practice_name_hint, website,
                                   failure_type, err_str, run_id_hint)

            # Circuit breaker
            consecutive_failures += 1
            print(f"  ⚠️  Consecutive failures: {consecutive_failures}/{FAILURE_LIMIT}")
            if consecutive_failures >= FAILURE_LIMIT:
                msg = f"🛑 D100 halted — {FAILURE_LIMIT} consecutive failures. Last error on {website}: {err_str[:200]}"
                print(f"\n{msg}")
                if slack_webhook:
                    notify_slack_critical(slack_webhook, msg)
                sys.exit(1)

    # Write results summary CSV — union of all keys so failed + success rows coexist
    results_path = OUTPUT_ROOT / f"d100_v3_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if results:
        # Build ordered fieldnames: preferred columns first, then any extras
        preferred = ["run_id", "website", "status", "report_url", "gamma_url",
                     "keywords_count", "quick_wins", "traffic_value",
                     "ai_overview_serp_count", "error"]
        all_keys: list = list(preferred)
        for r in results:
            for k in r:
                if k not in all_keys:
                    all_keys.append(k)
        with open(results_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore", restval="")
            writer.writeheader()
            writer.writerows(results)
        print(f"\n📊 Results written: {results_path}")

    success = sum(1 for r in results if r.get("status") in ("completed", "submitted", "phase2_pending"))
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {success}/{len(results)} succeeded")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
