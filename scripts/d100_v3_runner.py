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
  (booking_url auto-detected from scraped homepage; SEO data fetched via DataForSEO API)

Environment (.env at project root):
  ANTHROPIC_API_KEY=sk-ant-...
  SLACK_WEBHOOK_URL=https://hooks.slack.com/...
  DATAFORSEO_LOGIN=...       # Primary SEO data (~$0.04/domain, 15-20x cheaper than SEMrush)
  DATAFORSEO_PASSWORD=...
  SEMRUSH_API_KEY=...        # Fallback if DataForSEO unavailable (~$0.63/domain, ~630 units)

Phase 3 deploys seo_report.html to GitHub Pages as a personalized deliverables page.
Repo slug format: Plug-and-play-AI-SEO-and-Ad-Strategy-for-{Company-Name}
Live URL: https://{GHUSER}.github.io/Plug-and-play-AI-SEO-and-Ad-Strategy-for-{Company-Name}/
"""

import argparse
import base64
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
    for k in ("ANTHROPIC_API_KEY", "SLACK_WEBHOOK_URL", "SLACK_D100_OPENS_WEBHOOK", "SMARTLEAD_API_KEY",
              "SEMRUSH_API_KEY", "VERCEL_TOKEN",
              "DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD", "GOOGLE_SHEETS_ID"):
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


# ── Third-party colors to exclude from brand extraction ────────────────────────
_THIRD_PARTY_COLORS = {
    # Google
    "#4285F4", "#34A853", "#FBBC05", "#EA4335",
    # Facebook / Meta
    "#1877F2", "#0866FF",
    # Twitter / X
    "#1DA1F2",
    # LinkedIn
    "#0077B5", "#0A66C2",
    # Stripe
    "#635BFF",
    # Hotjar
    "#FF3C00",
    # HubSpot
    "#FF7A59",
    # Calendly
    "#006BFF",
    # Webflow
    "#4353FF",
    # Wix
    "#0C6EFC",
    # Generic blue (Bootstrap default)
    "#007BFF", "#0D6EFD",
}


# ── Phase 1: CSS brand color extraction ────────────────────────────────────────
def _fetch_homepage_html(website: str, timeout: int = 10) -> str:
    """Fetch homepage HTML. Returns empty string on failure."""
    try:
        req = urllib.request.Request(website, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extract_brand_colors_css(website: str) -> dict:
    """Extract brand colors via urllib CSS parsing.
    Priority: Elementor CSS custom properties → frequency-count hex scan → fallback.
    Excludes known third-party service colors (Google, Facebook, etc.)
    """
    html = _fetch_homepage_html(website)
    if not html:
        return {"note": "CSS extraction failed: could not fetch page", "background": "#FFFFFF",
                "source": "css_extraction_failed"}

    # Strip scripts and iframes before color extraction (removes third-party color noise)
    html_clean = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html_clean = re.sub(r"<iframe[^>]*>.*?</iframe>", "", html_clean, flags=re.DOTALL | re.IGNORECASE)
    html_clean = re.sub(r"<noscript[^>]*>.*?</noscript>", "", html_clean, flags=re.DOTALL | re.IGNORECASE)

    # 1. Elementor global CSS custom properties (~70% of functional medicine sites)
    elementor_map = {
        "--e-global-color-primary":   "primary",
        "--e-global-color-accent":    "accent",
        "--e-global-color-secondary": "secondary",
        "--e-global-color-text":      "text",
    }
    colors: dict = {}
    for var, key in elementor_map.items():
        m = re.search(rf"{re.escape(var)}\s*:\s*(#[0-9a-fA-F]{{3,8}})", html_clean)
        if m:
            c = m.group(1).upper()
            if c not in _THIRD_PARTY_COLORS:
                colors[key] = c

    if len(colors) >= 2:
        colors.setdefault("background", "#FFFFFF")
        colors["source"] = "css_extraction_elementor"
        return colors

    # 2. Broader CSS custom property scan (non-Elementor sites)
    css_var_matches = re.findall(r"--[\w-]+\s*:\s*(#[0-9a-fA-F]{6})\b", html_clean)
    if css_var_matches:
        css_freq: dict = {}
        for h in css_var_matches:
            c = h.upper()
            if c not in _THIRD_PARTY_COLORS:
                css_freq[c] = css_freq.get(c, 0) + 1
        css_top = sorted(css_freq, key=lambda k: css_freq[k], reverse=True)[:3]
        if css_top:
            r_val = int(css_top[0][1:3], 16)
            g_val = int(css_top[0][3:5], 16)
            b_val = int(css_top[0][5:7], 16)
            brightness = (r_val * 299 + g_val * 587 + b_val * 114) / 1000
            if 20 < brightness < 230:
                result: dict = {"primary": css_top[0], "background": "#FFFFFF",
                                "source": "css_extraction_custom_props"}
                if len(css_top) > 1:
                    result["accent"] = css_top[1]
                return result

    # 3. Frequency-count all 6-digit hex colors, exclude near-black/near-white/third-party
    all_hex = re.findall(r"#([0-9a-fA-F]{6})\b", html_clean)
    freq: dict = {}
    for h in all_hex:
        normalized = "#" + h.upper()
        if normalized in _THIRD_PARTY_COLORS:
            continue
        r_val = int(h[0:2], 16)
        g_val = int(h[2:4], 16)
        b_val = int(h[4:6], 16)
        brightness = (r_val * 299 + g_val * 587 + b_val * 114) / 1000
        if 20 < brightness < 235:
            freq[normalized] = freq.get(normalized, 0) + 1
    top = sorted(freq, key=lambda k: freq[k], reverse=True)[:3]
    if top:
        result = {"primary": top[0], "background": "#FFFFFF",
                  "source": "css_extraction_frequency"}
        if len(top) > 1:
            result["accent"] = top[1]
        if len(top) > 2:
            result["secondary"] = top[2]
        return result

    return {"note": "No colors detected via CSS", "background": "#FFFFFF",
            "source": "css_extraction_fallback"}


# ── Phase 1: Logo + favicon extraction from HTML ────────────────────────────────
def extract_page_assets(website: str) -> dict:
    """
    Extract logo URL and favicon URL from homepage HTML.
    Returns {"logo_url": str, "favicon_url": str, "hero_url": "", "headshot_url": ""}.
    """
    html = _fetch_homepage_html(website)
    if not html:
        return {"logo_url": "", "favicon_url": website.rstrip("/") + "/favicon.ico",
                "hero_url": "", "headshot_url": ""}

    base = website.rstrip("/")

    def make_absolute(href: str) -> str:
        if not href:
            return ""
        href = href.strip()
        if href.startswith("//"):
            return "https:" + href
        if href.startswith("/"):
            return base + href
        if href.startswith("http"):
            return href
        return base + "/" + href

    # ── Favicon ───────────────────────────────────────────────────────────────
    favicon_url = ""
    favicon_patterns = [
        r'<link[^>]+rel=["\'](?:shortcut )?icon["\'][^>]+href=["\']([^"\']+)["\']',
        r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\'](?:shortcut )?icon["\']',
        r'<link[^>]+rel=["\']apple-touch-icon["\'][^>]+href=["\']([^"\']+)["\']',
    ]
    for pat in favicon_patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            favicon_url = make_absolute(m.group(1))
            break
    if not favicon_url:
        favicon_url = base + "/favicon.ico"

    # ── Logo: look in <header>, <nav>, or elements with logo-related attributes ──
    logo_url = ""

    def _is_valid_logo(url: str) -> bool:
        if not url or url.startswith("data:"):
            return False
        # Skip common non-logo image patterns
        skip = ["pixel", "tracker", "analytics", "1x1", "spacer", "clear.gif",
                "badge", "certified", "award", "seal", "rating",
                "wellness-services", "-services", "-staff", "-team", "-hero",
                "-banner", "-slide", "background", "bg-image", "stock-photo"]
        lower = url.lower()
        return not any(s in lower for s in skip)

    # Strategy 0: Platform-specific logo class detection (most precise)
    platform_logo_patterns = [
        # WordPress: custom-logo (appears on ALL WordPress sites with logo set)
        r'<img[^>]+class=["\'][^"\']*custom-logo[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]+class=["\'][^"\']*custom-logo[^"\']*["\']',
        # WordPress: site-logo
        r'<img[^>]+class=["\'][^"\']*site-logo[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]+class=["\'][^"\']*site-logo[^"\']*["\']',
        # WordPress: custom-logo-link wrapper
        r'<a[^>]+class=["\'][^"\']*custom-logo-link[^"\']*["\'][^>]*>\s*<img[^>]+src=["\']([^"\']+)["\']',
        # Squarespace: header-title-logo
        r'<div[^>]+class=["\'][^"\']*header-title-logo[^"\']*["\'][^>]*>\s*<img[^>]+src=["\']([^"\']+)["\']',
        # Webflow: navbar-logo
        r'<img[^>]+class=["\'][^"\']*navbar-logo[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]+class=["\'][^"\']*navbar-logo[^"\']*["\']',
        # Generic: site-branding wrapper
        r'<div[^>]+class=["\'][^"\']*site-branding[^"\']*["\'][^>]*>.*?<img[^>]+src=["\']([^"\']+)["\']',
        r'<div[^>]+class=["\'][^"\']*brand[^"\']*["\'][^>]*>\s*<(?:a[^>]*>\s*)?<img[^>]+src=["\']([^"\']+)["\']',
    ]
    for pat in platform_logo_patterns:
        m = re.search(pat, html, re.DOTALL | re.IGNORECASE)
        if m:
            candidate = make_absolute(m.group(1))
            if _is_valid_logo(candidate):
                logo_url = candidate
                break

    # Strategy 1: First <img> inside <header> or <nav> (most reliable — always the logo)
    # Try <nav> first (tighter context), then <header>
    for tag in ["nav", "header"]:
        header_match = re.search(
            rf'<{tag}[^>]*>(.*?)</{tag}>',
            html, re.DOTALL | re.IGNORECASE
        )
        if header_match:
            nav_html = header_match.group(1)
            # Look for img with logo-related class/id/alt first
            logo_in_nav_patterns = [
                r'<img[^>]+(?:class|id)=["\'][^"\']*logo[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
                r'<img[^>]+src=["\']([^"\']+)["\'][^>]+(?:class|id)=["\'][^"\']*logo[^"\']*["\']',
                r'<img[^>]+alt=["\'][^"\']*logo[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
                r'<img[^>]+src=["\']([^"\']+)["\'][^>]+alt=["\'][^"\']*logo[^"\']*["\']',
            ]
            for pat in logo_in_nav_patterns:
                m = re.search(pat, nav_html, re.IGNORECASE)
                if m:
                    candidate = make_absolute(m.group(1))
                    if _is_valid_logo(candidate):
                        logo_url = candidate
                        break
            if logo_url:
                break
            # Fallback: first img in nav/header
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', nav_html, re.IGNORECASE)
            if img_match:
                candidate = make_absolute(img_match.group(1))
                if _is_valid_logo(candidate):
                    logo_url = candidate
                    break

    # Strategy 2: Global img search with logo-related attributes (fallback)
    if not logo_url:
        logo_img_patterns = [
            r'<img[^>]+(?:class|id)=["\'][^"\']*logo[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]+(?:class|id)=["\'][^"\']*logo[^"\']*["\']',
            r'<img[^>]+alt=["\'][^"\']*logo[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]+alt=["\'][^"\']*logo[^"\']*["\']',
            # Retina logo assets (e.g. practice-name@2x.png) — almost always the logo
            r'<img[^>]+src=["\']([^"\']+@2x\.[a-z]+)["\']',
            r'<img[^>]+src=["\']([^"\']*logo[^"\']*\.(?:png|svg|jpg|webp|gif))["\']',
            r'<img[^>]+src=["\']([^"\']*(?:brand|wordmark)[^"\']*\.(?:png|svg|jpg|webp|gif))["\']',
        ]
        for pat in logo_img_patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                candidate = make_absolute(m.group(1))
                if _is_valid_logo(candidate):
                    logo_url = candidate
                    break

    # Strategy 3: First <img> overall (last resort — logo is almost always first image on page)
    if not logo_url:
        first_img = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if first_img:
            candidate = make_absolute(first_img.group(1))
            if _is_valid_logo(candidate):
                logo_url = candidate

    return {
        "logo_url":    logo_url,
        "favicon_url": favicon_url,
        "hero_url":    "",
        "headshot_url": "",
    }


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
        "clinical_traffic_value": 0,
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


# ── City-level DataForSEO location codes (city-specific SERP results) ──────────
# Used for "near me" searches from the practice's actual city perspective.
# Source: DataForSEO /v3/serp/google/locations (verified March 2026)
CITY_LOCATION_CODES = {
    ("Albuquerque", "NM"): 1022494, ("Anaheim", "CA"): 1013542,
    ("Anchorage", "AK"): 1012873, ("Arlington", "TX"): 1026194,
    ("Atlanta", "GA"): 1015254, ("Aurora", "CO"): 1014437,
    ("Austin", "TX"): 1026201, ("Bakersfield", "CA"): 1013570,
    ("Baltimore", "MD"): 1018511, ("Birmingham", "AL"): 1012954,
    ("Boise", "ID"): 1016131, ("Boston", "MA"): 1018127,
    ("Buffalo", "NY"): 1022764, ("Cary", "NC"): 1021041,
    ("Chandler", "AZ"): 1013387, ("Chapel Hill", "NC"): 1021047,
    ("Charlotte", "NC"): 1021048, ("Chicago", "IL"): 1016367,
    ("Chula Vista", "CA"): 1013677, ("Cincinnati", "OH"): 1023626,
    ("Cleveland", "OH"): 1023631, ("Colorado Springs", "CO"): 1014471,
    ("Columbus", "OH"): 1023640, ("Corpus Christi", "TX"): 1026319,
    ("Dallas", "TX"): 1026339, ("Denver", "CO"): 1014485,
    ("Des Moines", "IA"): 1015746, ("Detroit", "MI"): 1019250,
    ("Durham", "NC"): 1021085, ("El Paso", "TX"): 1026376,
    ("Evanston", "IL"): 1016453, ("Fayetteville", "NC"): 1021108,
    ("Fort Wayne", "IN"): 1017108, ("Fort Worth", "TX"): 1026411,
    ("Fremont", "CA"): 1013802, ("Fresno", "CA"): 1013804,
    ("Garland", "TX"): 1026419, ("Gilbert", "AZ"): 1013416,
    ("Glendale", "AZ"): 1013417, ("Grand Rapids", "MI"): 1019316,
    ("Greensboro", "NC"): 1021129, ("Henderson", "NV"): 1022635,
    ("Honolulu", "HI"): 1015579, ("Houston", "TX"): 1026481,
    ("Huntsville", "AL"): 1013042, ("Indianapolis", "IN"): 1017146,
    ("Irving", "TX"): 1026497, ("Jacksonville", "FL"): 1015067,
    ("Jersey City", "NJ"): 1022194, ("Kansas City", "MO"): 1020414,
    ("Las Vegas", "NV"): 1022639, ("Lexington", "KY"): 1017818,
    ("Lincoln", "NE"): 1021696, ("Little Rock", "AR"): 1013268,
    ("Long Beach", "CA"): 1013958, ("Los Angeles", "CA"): 1013962,
    ("Louisville", "KY"): 1017825, ("Madison", "WI"): 1028057,
    ("Memphis", "TN"): 1026069, ("Mesa", "AZ"): 1013445,
    ("Miami", "FL"): 1015116, ("Milwaukee", "WI"): 1028087,
    ("Minneapolis", "MN"): 1019973, ("Naperville", "IL"): 1016710,
    ("Nashville", "TN"): 1026083, ("New Orleans", "LA"): 1018036,
    ("New York", "NY"): 1023191, ("Newark", "NJ"): 1022300,
    ("Oak Park", "IL"): 1016734, ("Oklahoma City", "OK"): 1024290,
    ("Omaha", "NE"): 1021721, ("Orlando", "FL"): 1015150,
    ("Pasadena", "CA"): 1014118, ("Peoria", "AZ"): 1013461,
    ("Philadelphia", "PA"): 1025197, ("Phoenix", "AZ"): 1013462,
    ("Pittsburgh", "PA"): 1025202, ("Plano", "TX"): 1026695,
    ("Portland", "OR"): 1024543, ("Raleigh", "NC"): 1021278,
    ("Richmond", "VA"): 1027270, ("Riverside", "CA"): 1014197,
    ("Rochester", "NY"): 1023315, ("Sacramento", "CA"): 1014208,
    ("Salt Lake City", "UT"): 1026990, ("San Antonio", "TX"): 1026759,
    ("San Bernardino", "CA"): 1014214, ("San Diego", "CA"): 1014218,
    ("San Francisco", "CA"): 1014221, ("San Jose", "CA"): 1014226,
    ("Santa Ana", "CA"): 1014247, ("Schaumburg", "IL"): 1016834,
    ("Scottsdale", "AZ"): 1013482, ("Seattle", "WA"): 1027744,
    ("Spokane", "WA"): 1027760, ("St. Louis", "MO"): 1020618,
    ("Tacoma", "WA"): 1027773, ("Tampa", "FL"): 1015214,
    ("Tempe", "AZ"): 1013487, ("Tucson", "AZ"): 1013509,
    ("Virginia Beach", "VA"): 1027320, ("Washington", "DC"): 1014895,
}

# Metro adjacents: primary city → list of suburb/adjacent (city, state) tuples
# Used to build a fuller picture of the local competitive market
METRO_ADJACENTS = {
    ("Chicago", "IL"):        [("Evanston", "IL"), ("Oak Park", "IL"), ("Naperville", "IL"), ("Schaumburg", "IL")],
    ("New York", "NY"):       [("Newark", "NJ"), ("Jersey City", "NJ")],
    ("Los Angeles", "CA"):    [("Pasadena", "CA"), ("Long Beach", "CA"), ("Anaheim", "CA"), ("Santa Ana", "CA")],
    ("Dallas", "TX"):         [("Plano", "TX"), ("Irving", "TX"), ("Garland", "TX"), ("Arlington", "TX")],
    ("Houston", "TX"):        [("Corpus Christi", "TX")],
    ("Phoenix", "AZ"):        [("Scottsdale", "AZ"), ("Mesa", "AZ"), ("Chandler", "AZ"), ("Gilbert", "AZ"), ("Tempe", "AZ"), ("Glendale", "AZ"), ("Peoria", "AZ")],
    ("San Francisco", "CA"):  [("San Jose", "CA"), ("Fremont", "CA")],
    ("Seattle", "WA"):        [("Tacoma", "WA"), ("Spokane", "WA")],
    ("Denver", "CO"):         [("Aurora", "CO"), ("Colorado Springs", "CO")],
    ("Atlanta", "GA"):        [],
    ("Boston", "MA"):         [],
    ("Miami", "FL"):          [("Orlando", "FL"), ("Jacksonville", "FL"), ("Tampa", "FL")],
    ("Charlotte", "NC"):      [("Raleigh", "NC"), ("Durham", "NC"), ("Cary", "NC"), ("Chapel Hill", "NC"), ("Greensboro", "NC"), ("Fayetteville", "NC")],
    ("Raleigh", "NC"):        [("Durham", "NC"), ("Cary", "NC"), ("Chapel Hill", "NC")],
    ("Austin", "TX"):         [("San Antonio", "TX")],
    ("Minneapolis", "MN"):    [],
    ("San Diego", "CA"):      [("Chula Vista", "CA")],
    ("Portland", "OR"):       [],
    ("Las Vegas", "NV"):      [("Henderson", "NV")],
    ("San Antonio", "TX"):    [("Austin", "TX")],
    ("Kansas City", "MO"):    [],
    ("Columbus", "OH"):       [],
    ("Indianapolis", "IN"):   [("Fort Wayne", "IN")],
    ("Nashville", "TN"):      [("Memphis", "TN")],
    ("Detroit", "MI"):        [("Grand Rapids", "MI")],
    ("Milwaukee", "WI"):      [("Madison", "WI")],
    ("Baltimore", "MD"):      [("Washington", "DC")],
    ("Washington", "DC"):     [("Baltimore", "MD"), ("Richmond", "VA")],
}

# Area code → (city, state) for phone-based location fallback
# Covers the most common US metro area codes
AREA_CODE_CITY = {
    "212": ("New York", "NY"), "718": ("New York", "NY"), "646": ("New York", "NY"), "917": ("New York", "NY"),
    "213": ("Los Angeles", "CA"), "310": ("Los Angeles", "CA"), "323": ("Los Angeles", "CA"), "424": ("Los Angeles", "CA"),
    "312": ("Chicago", "IL"), "773": ("Chicago", "IL"), "872": ("Chicago", "IL"),
    "713": ("Houston", "TX"), "281": ("Houston", "TX"), "832": ("Houston", "TX"),
    "602": ("Phoenix", "AZ"), "480": ("Phoenix", "AZ"), "623": ("Phoenix", "AZ"),
    "215": ("Philadelphia", "PA"), "267": ("Philadelphia", "PA"),
    "210": ("San Antonio", "TX"), "726": ("San Antonio", "TX"),
    "858": ("San Diego", "CA"), "619": ("San Diego", "CA"),
    "214": ("Dallas", "TX"), "469": ("Dallas", "TX"), "972": ("Dallas", "TX"),
    "408": ("San Jose", "CA"), "669": ("San Jose", "CA"),
    "512": ("Austin", "TX"), "737": ("Austin", "TX"),
    "904": ("Jacksonville", "FL"),
    "817": ("Fort Worth", "TX"),
    "614": ("Columbus", "OH"),
    "704": ("Charlotte", "NC"), "980": ("Charlotte", "NC"),
    "317": ("Indianapolis", "IN"),
    "415": ("San Francisco", "CA"), "628": ("San Francisco", "CA"),
    "206": ("Seattle", "WA"), "253": ("Seattle", "WA"), "425": ("Seattle", "WA"),
    "303": ("Denver", "CO"), "720": ("Denver", "CO"),
    "615": ("Nashville", "TN"),
    "405": ("Oklahoma City", "OK"),
    "915": ("El Paso", "TX"),
    "702": ("Las Vegas", "NV"),
    "901": ("Memphis", "TN"),
    "502": ("Louisville", "KY"),
    "503": ("Portland", "OR"), "971": ("Portland", "OR"),
    "443": ("Baltimore", "MD"), "410": ("Baltimore", "MD"),
    "414": ("Milwaukee", "WI"),
    "505": ("Albuquerque", "NM"),
    "520": ("Tucson", "AZ"),
    "559": ("Fresno", "CA"),
    "916": ("Sacramento", "CA"),
    "316": ("Wichita", "KS"),
    "816": ("Kansas City", "MO"),
    "402": ("Omaha", "NE"),
    "919": ("Raleigh", "NC"), "984": ("Raleigh", "NC"),
    "251": ("Birmingham", "AL"),
    "907": ("Anchorage", "AK"),
    "804": ("Richmond", "VA"),
    "612": ("Minneapolis", "MN"), "763": ("Minneapolis", "MN"), "952": ("Minneapolis", "MN"),
    "813": ("Tampa", "FL"), "727": ("Tampa", "FL"),
    "918": ("Tulsa", "OK"),
    "407": ("Orlando", "FL"), "321": ("Orlando", "FL"),
    "216": ("Cleveland", "OH"),
    "606": ("Lexington", "KY"), "859": ("Lexington", "KY"),
    "716": ("Buffalo", "NY"),
    "701": ("Fargo", "ND"),
    "208": ("Boise", "ID"),
    "801": ("Salt Lake City", "UT"), "385": ("Salt Lake City", "UT"),
    "314": ("St. Louis", "MO"), "636": ("St. Louis", "MO"),
    "336": ("Greensboro", "NC"),
    "515": ("Des Moines", "IA"),
    "202": ("Washington", "DC"),
    "617": ("Boston", "MA"), "857": ("Boston", "MA"),
    "404": ("Atlanta", "GA"), "678": ("Atlanta", "GA"), "770": ("Atlanta", "GA"),
    "305": ("Miami", "FL"), "786": ("Miami", "FL"),
    "509": ("Spokane", "WA"),
    "253": ("Tacoma", "WA"),
    "605": ("Sioux Falls", "SD"),
    "603": ("Manchester", "NH"),
    "860": ("Hartford", "CT"),
    "843": ("Charleston", "SC"),
    "903": ("Tyler", "TX"),
    "806": ("Lubbock", "TX"),
    "361": ("Corpus Christi", "TX"),
    "847": ("Evanston", "IL"),
    "630": ("Naperville", "IL"),
    "219": ("Gary", "IN"),
    "708": ("Oak Park", "IL"),
}


def fetch_practice_location(domain: str, brand_name: str, raw_scrape: str,
                             dfs_login: str, dfs_password: str) -> dict:
    """
    4-layer pipeline to determine a practice's primary city/state.
    Returns dict with: primary_city, primary_state, location_code, all_locations, is_multi_location.

    Layer 1: Brand SERP → Google Local Pack (GMB-verified, most accurate)
    Layer 2: Phone area code in scraped homepage (zero cost)
    Layer 3: Address regex in scraped homepage
    Layer 4: DataForSEO location lookup fallback (US-wide)
    """
    import base64

    clean_domain = re.sub(r"https?://", "", domain).rstrip("/").split("/")[0]
    auth = base64.b64encode(f"{dfs_login}:{dfs_password}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    def post(endpoint, payload):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"https://api.dataforseo.com{endpoint}",
            data=data, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def location_code_for(city, state):
        """Look up DataForSEO city location_code; return None if not in dict."""
        return CITY_LOCATION_CODES.get((city, state)) or CITY_LOCATION_CODES.get((city.title(), state))

    def parse_city_state_from_local_pack(description: str):
        """Extract 'City, ST' from local_pack description like 'Chicago, IL · (773) 555-1234'."""
        m = re.match(r"^([A-Za-z\s]+),\s*([A-Z]{2})\s*[·•]", description.strip())
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return None, None

    result = {
        "primary_city": "", "primary_state": "", "location_code": 2840,
        "all_locations": [], "is_multi_location": False, "location_source": "fallback",
    }

    # ── Layer 1: Brand SERP → local_pack ────────────────────────────────────
    try:
        serp_resp = post("/v3/serp/google/organic/live/advanced", [{
            "keyword": brand_name or clean_domain,
            "language_code": "en", "location_code": 2840,
            "device": "desktop", "depth": 5,
        }])
        items = serp_resp["tasks"][0]["result"][0].get("items", []) or []
        lp_items = [i for i in items if i.get("type") == "local_pack"]
        if lp_items:
            cities_seen = {}
            all_locs = []
            for lp in lp_items:
                desc = lp.get("description", "")
                city, state = parse_city_state_from_local_pack(desc)
                if city and state:
                    key = f"{city}, {state}"
                    cities_seen[key] = cities_seen.get(key, 0) + 1
                    if key not in all_locs:
                        all_locs.append(key)
            if cities_seen:
                # Primary city = most common in local pack results
                primary_loc = max(cities_seen, key=cities_seen.get)
                parts = primary_loc.split(", ")
                city, state = parts[0], parts[1]
                lc = location_code_for(city, state)
                result.update({
                    "primary_city": city,
                    "primary_state": state,
                    "location_code": lc or 2840,
                    "all_locations": all_locs,
                    "is_multi_location": len(all_locs) > 1,
                    "location_source": "brand_serp_local_pack",
                })
                return result
    except Exception:
        pass

    # ── Layer 2: Phone area code ─────────────────────────────────────────────
    try:
        phones = re.findall(r'\(?\b(\d{3})\)?[-.\s]\d{3}[-.\s]\d{4}', raw_scrape)
        for area in phones:
            if area in AREA_CODE_CITY:
                city, state = AREA_CODE_CITY[area]
                lc = location_code_for(city, state)
                result.update({
                    "primary_city": city, "primary_state": state,
                    "location_code": lc or 2840,
                    "all_locations": [f"{city}, {state}"],
                    "is_multi_location": False,
                    "location_source": "area_code",
                })
                return result
    except Exception:
        pass

    # ── Layer 3: Address regex in homepage ───────────────────────────────────
    try:
        addr_re = re.compile(r'\b([A-Z][a-zA-Z\s]{2,20}),\s*([A-Z]{2})\s+\d{5}\b')
        matches = addr_re.findall(raw_scrape)
        if matches:
            city, state = matches[0]
            city = city.strip()
            lc = location_code_for(city, state)
            result.update({
                "primary_city": city, "primary_state": state,
                "location_code": lc or 2840,
                "all_locations": [f"{city}, {state}"],
                "is_multi_location": False,
                "location_source": "address_regex",
            })
            return result
    except Exception:
        pass

    # ── Layer 4: Fallback — US-wide (location_code 2840) ─────────────────────
    result["location_source"] = "fallback_us_wide"
    return result


# ── Competitor type classification ──────────────────────────────────────────────
# Known health system domain patterns — these are never "winnable" direct competitors
_HEALTH_SYSTEM_PATTERNS = [
    "nm.org", "northwestern", "dukehealth", "ucsf", "mayo", "cleveland",
    "endeavorhealth", "advocatehealth", "ascension", "mercy", "sutter",
    "henryford", "dignity", "providence", "banner", "hca", "tenet",
    "commonspirit", "trinity", "christus", "geisinger", "intermountain",
    "ohiohealth", "prisma", "wellstar", "atrium", "hackensack", "northwell",
    "piedmont", "memorial", "baptist", "presbyterian", "methodist",
    "catholic", "franciscan", "bon secours", "adventist", "kaiser",
]


def _classify_competitor(domain: str) -> str:
    d = domain.lower()
    for pattern in _HEALTH_SYSTEM_PATTERNS:
        if pattern in d:
            return "health_system"
    # edu domains are typically academic medical centers
    if d.endswith(".edu") or ".edu." in d:
        return "health_system"
    return "practice"


# ── Phase 1: DataForSEO API fetch (primary, preferred over SEMrush) ────────────
# Cost per run: ~$0.041/domain (4 calls)
#   domain_rank_overview      ~$0.010  → domain rank, position distribution, traffic value
#   ranked_keywords (organic) ~$0.010  → keyword details, AI Overview SERP presence
#   ranked_keywords (ai_ref)  ~$0.010  → AI Overview citation count
#   competitors_domain        ~$0.010  → top organic competitors
def fetch_dataforseo(domain: str, login: str, password: str,
                     city: str = "", state: str = "", location_code: int = 2840) -> dict:
    """
    Pull live SEO data from DataForSEO Labs API. ~$0.041 per domain.
    Returns same dict shape as fetch_semrush_api() for drop-in compatibility.
    """
    import base64

    clean_domain = re.sub(r"https?://", "", domain).rstrip("/").split("/")[0]
    _serp_city          = city
    _serp_state         = state
    _serp_location_code = location_code
    base_url = "https://api.dataforseo.com"
    auth = base64.b64encode(f"{login}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    def post(endpoint, payload):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{base_url}{endpoint}",
            data=data, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())

    def safe_int(v):
        try:
            return int(v) if v is not None else 0
        except (TypeError, ValueError):
            return 0

    # CTR estimates by position (industry standard approximations)
    CTR_MAP = {1: 0.31, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.06,
               6: 0.05, 7: 0.04, 8: 0.04, 9: 0.03, 10: 0.03}

    # Fire 5 API calls in parallel — independent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        fut_overview = ex.submit(post,
            "/v3/dataforseo_labs/google/domain_rank_overview/live",
            [{"target": clean_domain, "language_code": "en", "location_code": 2840}]
        )
        fut_kw = ex.submit(post,
            "/v3/dataforseo_labs/google/ranked_keywords/live",
            [{
                "target": clean_domain,
                "language_code": "en",
                "location_code": 2840,
                "item_types": ["organic"],
                "limit": 1000,
                "order_by": ["keyword_data.keyword_info.search_volume,desc"],
            }]
        )
        fut_ai = ex.submit(post,
            "/v3/dataforseo_labs/google/ranked_keywords/live",
            [{
                "target": clean_domain,
                "language_code": "en",
                "location_code": 2840,
                "item_types": ["ai_overview_reference"],
                "limit": 100,
            }]
        )
        fut_comp = ex.submit(post,
            "/v3/dataforseo_labs/google/competitors_domain/live",
            [{
                "target": clean_domain,
                "language_code": "en",
                "location_code": 2840,
                "limit": 30,  # More results so blocklist has more to work with
            }]
        )
        overview_resp = fut_overview.result()
        kw_resp       = fut_kw.result()
        ai_resp       = fut_ai.result()
        comp_resp     = fut_comp.result()

    # ── Parse domain_rank_overview ──────────────────────────────────────────────
    # API response: result[0] is metadata wrapper; domain data lives in result[0].items[0]
    domain_rank = 0
    traffic_value = 0
    ov_pos1 = ov_pos2_3 = ov_pos4_10 = ov_pos11_20 = ov_count = 0
    ov_referring_domains = 0  # linking sites count (from Labs overview)
    try:
        ov_result = overview_resp["tasks"][0]["result"][0]
        ov_items  = ov_result.get("items", []) or []
        ov        = ov_items[0] if ov_items else {}
        domain_rank = safe_int(ov.get("rank", 0))
        ov_referring_domains = safe_int(ov.get("referring_domains", 0))
        m = ov.get("metrics", {}).get("organic", {})
        ov_pos1     = safe_int(m.get("pos_1", 0))
        ov_pos2_3   = safe_int(m.get("pos_2_3", 0))
        ov_pos4_10  = safe_int(m.get("pos_4_10", 0))
        ov_pos11_20 = safe_int(m.get("pos_11_20", 0))
        ov_count    = safe_int(m.get("count", 0))
        traffic_value = safe_int(m.get("etv", 0))   # ETV = estimated traffic value (USD)
    except (KeyError, IndexError, TypeError):
        pass

    referring_domains = ov_referring_domains  # from Labs domain_rank_overview (may be 0 for small sites)

    # ── Parse ranked_keywords (organic) ────────────────────────────────────────
    kw_items = []
    kw_total = 0
    kw_pos1 = kw_pos2_3 = kw_pos4_10 = kw_pos11_20 = 0
    try:
        kw_result = kw_resp["tasks"][0]["result"][0]
        kw_total  = safe_int(kw_result.get("total_count", 0))
        kw_items  = kw_result.get("items", []) or []
        km = kw_result.get("metrics", {}).get("organic", {})
        kw_pos1     = safe_int(km.get("pos_1", 0))
        kw_pos2_3   = safe_int(km.get("pos_2_3", 0))
        kw_pos4_10  = safe_int(km.get("pos_4_10", 0))
        kw_pos11_20 = safe_int(km.get("pos_11_20", 0))
        # Use ETV from ranked_keywords if overview ETV is 0
        if not traffic_value:
            traffic_value = safe_int(km.get("etv", 0))
    except (KeyError, IndexError, TypeError):
        pass

    # Use domain_rank_overview position counts (full dataset) as primary source
    # Fall back to ranked_keywords metrics if overview failed
    pos1    = ov_pos1     or kw_pos1
    pos2_3  = ov_pos2_3   or kw_pos2_3
    pos4_10 = ov_pos4_10  or kw_pos4_10
    pos11_20= ov_pos11_20 or kw_pos11_20
    total_kws = (ov_count or kw_total)

    # Build keyword detail lists from items
    ai_overview_serp_count = 0
    estimated_traffic = 0
    clinical_traffic_value = 0
    quick_wins = []
    top3_sample = []
    all_kw_data = []

    for item in kw_items:
        kd_obj = item.get("keyword_data", {}) or {}
        se_obj = (item.get("ranked_serp_element", {}) or {}).get("serp_item", {}) or {}
        # Nested sub-objects within keyword_data
        ki_obj = kd_obj.get("keyword_info", {}) or {}        # search_volume, cpc
        kp_obj = kd_obj.get("keyword_properties", {}) or {}  # keyword_difficulty
        si_obj = kd_obj.get("serp_info", {}) or {}           # serp_item_types

        keyword    = kd_obj.get("keyword", "")
        volume     = safe_int(ki_obj.get("search_volume", 0))
        kw_diff    = kp_obj.get("keyword_difficulty", 0) or 0
        try:
            kw_diff = float(kw_diff)
        except (TypeError, ValueError):
            kw_diff = 0.0
        cpc        = ki_obj.get("cpc", 0) or 0
        try:
            cpc = float(cpc)
        except (TypeError, ValueError):
            cpc = 0.0
        serp_types = si_obj.get("serp_item_types", []) or []
        position   = safe_int(se_obj.get("rank_group", 100)) or 100

        # AI Overview presence: SERP includes an AI Overview block
        if "ai_overview" in serp_types:
            ai_overview_serp_count += 1

        # Estimated traffic visits from CTR × volume
        ctr = CTR_MAP.get(min(position, 10), 0.02)
        estimated_traffic += int(volume * ctr)

        # Clinical traffic value: only keywords with CPC > $1.00 (high patient-intent)
        if cpc >= 1.0:
            clinical_traffic_value += int(volume * ctr * cpc)

        entry = {"keyword": keyword, "position": position, "volume": volume,
                 "kd": kw_diff, "cpc": cpc}
        all_kw_data.append(entry)

        # Quick wins: pos 4-10, KD < 40, volume > 50
        if 4 <= position <= 10 and kw_diff < 40 and volume > 50:
            quick_wins.append(entry)
        # Top 3 sample: pos 1-3, decent volume
        if position <= 3 and volume >= 50:
            top3_sample.append(entry)

    # Sort lists
    quick_wins.sort(key=lambda x: x["volume"], reverse=True)
    top_by_volume = sorted(all_kw_data, key=lambda x: x["volume"], reverse=True)[:20]

    # ── Parse AI Overview citations ─────────────────────────────────────────────
    ai_cited_count = 0
    try:
        ai_result = ai_resp["tasks"][0]["result"][0]
        ai_cited_count = safe_int(ai_result.get("total_count", 0))
        if not ai_cited_count:
            ai_cited_count = len(ai_result.get("items", []) or [])
    except (KeyError, IndexError, TypeError):
        ai_cited_count = 0

    # ── Parse competitors ───────────────────────────────────────────────────────
    # Primary: competitors_domain (keyword overlap — returns 30 results so blocklist has more to filter)
    competitors_raw = []
    try:
        comp_items = comp_resp["tasks"][0]["result"][0].get("items", []) or []
        for ci in comp_items:
            cm = (ci.get("metrics", {}) or {}).get("organic", {}) or {}
            _comp_domain = ci.get("domain", "")
            competitors_raw.append({
                "domain":           _comp_domain,
                "avg_position":     round(float(ci.get("avg_pos", 0) or 0), 1),
                "intersections":    safe_int(ci.get("intersections", 0)),
                "keywords":         safe_int(cm.get("count", ci.get("intersections", 0))),
                "traffic":          safe_int(cm.get("etv", 0)),
                "traffic_value":    safe_int(cm.get("etv", 0)),
                "source":           "keyword_overlap",
                "competitor_type":  _classify_competitor(_comp_domain),
            })
    except (KeyError, IndexError, TypeError):
        competitors_raw = []

    # Secondary: SERP scraping using city-specific location codes.
    # This finds who's ACTUALLY ranking when a patient searches from the practice's city.
    # Uses location data stored in p1 (set by fetch_practice_location before this call).
    serp_competitors = []
    own_serp_position = {}
    try:
        # Build SERP queries: "near me" from practice city + geo-modified city query
        city_loc_code   = _serp_location_code  # passed in via closure / caller
        city_name       = _serp_city
        state_abbr      = _serp_state

        # Detect practice specialty from top keywords
        SPECIALTY_TERMS = [
            "functional medicine", "integrative medicine", "hormone health", "acupuncture",
            "chiropractic", "physical therapy", "naturopath", "holistic", "wellness",
            "weight loss", "primary care", "family medicine", "internal medicine",
        ]
        all_text = " ".join(kd.get("keyword", "") for kd in all_kw_data[:50]).lower()
        specialty = "functional medicine"  # default
        best_count = 0
        for term in SPECIALTY_TERMS:
            cnt = all_text.count(term)
            if cnt > best_count:
                best_count, specialty = cnt, term

        # Build query list
        serp_queries = []
        if city_loc_code and city_loc_code != 2840:
            # City-specific "near me" — true local perspective
            serp_queries.append({"keyword": f"{specialty} near me",
                                  "location_code": city_loc_code, "label": "near_me_local"})
        # Geo-modified query (US-wide but city-qualified) — always add as fallback/supplement
        if city_name and state_abbr:
            serp_queries.append({"keyword": f"{specialty} {city_name} {state_abbr}",
                                  "location_code": 2840, "label": "geo_modified"})
        # If no city detected, use best practice-specific keyword we have
        if not serp_queries:
            best_kw = next((kd["keyword"] for kd in sorted(all_kw_data,
                key=lambda x: x.get("volume", 0), reverse=True)
                if len(kd.get("keyword","").split()) >= 2), specialty)
            serp_queries.append({"keyword": best_kw, "location_code": 2840, "label": "fallback"})

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(serp_queries)) as serp_ex:
            serp_futs = {
                serp_ex.submit(post,
                    "/v3/serp/google/organic/live/advanced",
                    [{
                        "keyword": q["keyword"],
                        "language_code": "en",
                        "location_code": q["location_code"],
                        "device": "desktop",
                        "depth": 10,
                    }]
                ): q
                for q in serp_queries
            }
            for fut, q in serp_futs.items():
                try:
                    serp_resp = fut.result(timeout=30)
                    items = serp_resp["tasks"][0]["result"][0].get("items", []) or []
                    for item in items:
                        if item.get("type") != "organic":
                            continue
                        domain_result = (item.get("domain", "") or "").lower().strip()
                        pos = safe_int(item.get("rank_absolute", 0))
                        url = item.get("url", "")
                        title = item.get("title", "")
                        if domain_result == clean_domain:
                            own_serp_position[q["keyword"]] = pos
                            continue  # own domain: record position but don't add as competitor
                        if domain_result:
                            serp_competitors.append({
                                "domain": domain_result,
                                "avg_position": pos,
                                "intersections": 0,
                                "keywords": 0,
                                "traffic": 0,
                                "traffic_value": 0,
                                "source": "serp",
                                "serp_keyword": q["keyword"],
                                "serp_label": q["label"],
                                "url": url,
                                "competitor_type": _classify_competitor(domain_result),
                            })
                except Exception:
                    pass

        # Deduplicate: keep best (lowest) position per domain
        seen_serp = {}
        for sc in serp_competitors:
            d = sc["domain"]
            if d not in seen_serp or sc["avg_position"] < seen_serp[d]["avg_position"]:
                seen_serp[d] = sc
        serp_competitors = list(seen_serp.values())

    except Exception:
        serp_competitors = []
        own_serp_position = {}

    # Merge: SERP competitors first (most accurate for local), then keyword-overlap
    seen_domains = set()
    competitors = []
    for c in serp_competitors:
        d = c["domain"]
        if d not in seen_domains:
            seen_domains.add(d)
            competitors.append(c)
    for c in competitors_raw:
        d = c["domain"]
        if d not in seen_domains:
            seen_domains.add(d)
            competitors.append(c)

    # ── Apply competitor type classification to all competitors ─────────────────
    for c in competitors:
        if "competitor_type" not in c:
            c["competitor_type"] = _classify_competitor(c.get("domain", ""))

    # ── Enrich competitor traffic via domain_rank_overview ──────────────────────
    # Pull ETV for top 5 competitors that don't already have traffic data.
    # Cost: ~$0.010 per competitor domain.
    comps_needing_traffic = [c for c in competitors if c.get("traffic", 0) == 0][:5]
    if comps_needing_traffic:
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as comp_ex:
                def _fetch_comp_traffic(comp):
                    try:
                        r = post(
                            "/v3/dataforseo_labs/google/domain_rank_overview/live",
                            [{"target": comp["domain"], "language_code": "en", "location_code": 2840}]
                        )
                        ov_items = r["tasks"][0]["result"][0].get("items", []) or []
                        ov = ov_items[0] if ov_items else {}
                        m = ov.get("metrics", {}).get("organic", {}) or {}
                        comp["traffic"] = safe_int(m.get("etv", 0))
                        comp["traffic_value"] = safe_int(m.get("etv", 0))
                        comp["keywords"] = safe_int(m.get("count", 0))
                    except Exception:
                        pass
                    return comp
                comp_futs = [comp_ex.submit(_fetch_comp_traffic, c) for c in comps_needing_traffic]
                enriched = [f.result() for f in comp_futs]
                # Update the competitors list with enriched data
                enriched_domains = {c["domain"]: c for c in enriched}
                competitors = [enriched_domains.get(c["domain"], c) for c in competitors]
        except Exception:
            pass  # Enrichment is best-effort, never crash

    # Compute weighted avg position across pos 1-20 keywords (always a real number)
    total_pos_kws = pos1 + pos2_3 + pos4_10 + pos11_20
    if total_pos_kws > 0:
        avg_position = round((pos1*1.0 + pos2_3*2.5 + pos4_10*7.0 + pos11_20*15.5) / total_pos_kws, 1)
    else:
        avg_position = 0.0

    return {
        "source":                  "dataforseo",
        "domain_rank":             domain_rank,
        "referring_domains":       referring_domains,   # sites linking to this domain (from Labs overview)
        "avg_position":            avg_position,        # weighted avg SERP position (always real, never 0)
        "unique_keywords":         total_kws,
        "estimated_traffic":       estimated_traffic,
        "traffic_value":           traffic_value,
        "clinical_traffic_value":  clinical_traffic_value,
        "serp_features_traffic":   0,   # DataForSEO doesn't have a direct SERP-features-traffic metric
        "serp_features_value":     0,
        "ai_overview_serp_count":  ai_overview_serp_count,
        "ai_overview_cited_count": ai_cited_count,
        "pos1_count":              pos1,
        "pos2_3_count":            pos2_3,
        "pos4_10_count":           pos4_10,
        "pos11_20_count":          pos11_20,
        "pos1_3_count":            pos1 + pos2_3,
        "quick_wins_count":        len(quick_wins),
        "top_quick_wins":          quick_wins[:15],
        "top3_sample":             top3_sample[:10],
        "top_by_volume":           top_by_volume,
        "competitors":             competitors,
        "own_serp_positions":      own_serp_position,
        "serp_city":               city,
        "serp_state":              state,
        "serp_location_code":      location_code,
        "serp_specialty":          specialty if 'specialty' in dir() else "",
    }


# ── Phase 1: SEMrush CSV parse (fallback if no API key) ────────────────────────
def parse_semrush(csv_path: str) -> dict:
    if not csv_path or not os.path.exists(csv_path):
        return {"source": "none", "unique_keywords": 0, "quick_wins_count": 0,
                "estimated_traffic": 0, "traffic_value": 0, "clinical_traffic_value": 0,
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
        "clinical_traffic_value": 0,
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
  "keywords": ["string × 30 — top local + national SEO keywords"],
  "ads": [
    {
      "campaign_name": "string",
      "target_audience": "string",
      "headlines": ["string × 5 (≤30 chars each)"],
      "descriptions": ["string (≤90 chars) × 2"],
      "keywords": ["[exact]", "\"phrase\"", "broad × 8-10 total"],
      "extensions": {
        "Callout Extensions": ["string × 4 callouts, each ≤25 chars — practice-specific benefits (e.g. Free Consultation, No Referral Needed, Root Cause Approach, Same-Week Appointments)"],
        "Sitelink Extensions": ["Label | short description × 3 (e.g. New Patients | What to expect at your first visit)"]
      }
    }
  ],
  "emails": [
    {
      "email_number": 1,
      "type": "smart_practice_value_drop",
      "subject": "string",
      "preview": "string (≤45 chars)",
      "body": "string — 150-200 words, patient-facing, 2-3 short paragraphs",
      "cta_text": "string",
      "cta_url": "string (booking URL)"
    },
    {
      "email_number": 2,
      "type": "mechanism_story",
      "subject": "string",
      "preview": "string (≤45 chars)",
      "body": "string — 150-200 words, patient-facing, 2-3 short paragraphs",
      "cta_text": "string",
      "cta_url": "string (booking URL)"
    },
    {
      "email_number": 3,
      "type": "proof_and_results",
      "subject": "string",
      "preview": "string (≤45 chars)",
      "body": "string — 150-200 words, patient-facing, 2-3 short paragraphs",
      "cta_text": "string",
      "cta_url": "string (booking URL)"
    }
  ],
  "app_config": {
    "practiceName": "string",
    "practiceShortName": "string",
    "providerName": "string",
    "providerTitle": "string",
    "tagline": "string",
    "primaryColor": "#hex — dominant BRAND color (not black/white, not a third-party service color like Google blue #4285F4)",
    "primaryDark": "#hex — darker shade of primaryColor for headers/backgrounds",
    "primaryLight": "#hex — lighter shade of primaryColor for accents",
    "primaryXLight": "#hex — very light tint (10-15% opacity) for subtle backgrounds",
    "backgroundColor": "#hex — page background (usually white or near-white)",
    "bookingUrl": "string",
    "phone": "string",
    "concerns": [{"label": "string — 2-4 word health concern", "emoji": "string — single relevant emoji"}],
    "symptom_map": {
      "<concern label>": ["symptom string × 6-8 — specific, patient-relatable symptoms for this concern"]
    },
    "careModels": [{"name": "string", "desc": "string", "price": "string"}]
  }
}
"""

def build_phase2_prompt(context: str, scrape: str, semrush: dict, crawl: dict,
                         brand_colors: dict, prebuilt_seo_report: str = "") -> str:
    color_summary = "\n".join([f"  - {k}: {v}" for k, v in brand_colors.items()])

    # Build SEO data context block — provides data for keyword/ads/email generation
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

    # AI Overview coverage
    ai_serp  = semrush.get("ai_overview_serp_count", "N/A")
    ai_cited = semrush.get("ai_overview_cited_count", "N/A")
    sf_traffic = semrush.get("serp_features_traffic", 0)
    data_source = semrush.get("source", "unknown")

    semrush_block = f"""SEO DATA ({data_source}):
Domain Snapshot:
  Global Rank:       #{semrush.get('domain_rank', 0):,}
  Keywords Ranked:   {semrush.get('unique_keywords', 0):,}
  Monthly Traffic:   ~{semrush.get('estimated_traffic', 0):,} visits
  Traffic Value:     ${semrush.get('traffic_value', 0):,}/mo
  Data Source:       {data_source}

Position Distribution:
{pos_dist}

AI Overview Coverage (Google AI search):
  Keywords triggering AI Overview on SERP: {ai_serp}
  Keywords where this practice is cited:   {ai_cited}
  SERP Features Traffic:                  ~{sf_traffic:,} visits/mo

Top Keywords by Volume:
{top_vol_lines or '  (no data available)'}

Page-1 Quick Wins (pos 4-10, vol ≥100):
{qw_lines or '  (none identified)'}

Top Organic Competitors:
{comp_lines or '  (not available)'}"""

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
- 150-200 words per email. Short paragraphs. No emojis. No aggressive urgency. Sign off as the practice name or care team.
- Keywords: exactly 30 unique strings
- DO NOT include any YouTube or Calendly URLs anywhere in output
- JSON SAFETY: NEVER use double-quote characters (") inside string values. Ad headlines, email copy, and descriptions must use single quotes (') or rephrase without internal quotation marks. Unescaped double quotes break JSON parsing."""


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


def call_anthropic_api(prompt: str, api_key: str, model: str = "claude-sonnet-4-5",
                       max_tokens: int = 8192) -> str:
    """Call Anthropic API via urllib (no SDK). Returns raw text content."""
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["content"][0]["text"].strip()


def extract_json_from_response(text: str) -> dict:
    """Strip markdown fences and parse JSON from Claude response."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```\s*$", "", text.strip(), flags=re.MULTILINE)
    return json.loads(text.strip())


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
    data_src = semrush.get("source", "dataforseo")
    return f"""You are a senior healthcare SEO analyst reviewing a practice's digital footprint. Generate a Digital Health Report using ONLY the numbers provided below — never estimate or fabricate.

SEO DATA ({data_src}):
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
                              website: str, semrush: dict, run_id: str,
                              ref_url: str = "", primary_email: str = "") -> bool:
    ai_serp  = semrush.get("ai_overview_serp_count", "N/A")
    ai_cited = semrush.get("ai_overview_cited_count", "N/A")
    send_url = ref_url if ref_url else report_url
    email_note = f"*Contact Email:*\n{primary_email}" if primary_email else "*Contact Email:*\nnot provided"
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
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": email_note},
                {"type": "mrkdwn", "text": f"*📧 Send This URL:*\n<{send_url}|Copy tracked link>"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn",
                "text": f"*👁 Preview (no Slack ping):* <{report_url}?preview=1|Open with ?preview=1>"}},
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
               existing_run_dir: str = None,
               preview: bool = False) -> dict:
    website = row.get("website", "").rstrip("/")
    context = row.get("context", "")
    # booking_url and semrush_csv are auto-resolved — not required in CSV
    semrush_csv = row.get("semrush_csv", "")

    # Extract primary email from CSV emails column for SmartLead ?ref= tracking
    raw_emails = row.get("emails", "").strip()
    primary_email = raw_emails.split(",")[0].strip() if raw_emails else ""
    ref_token = base64.b64encode(primary_email.encode()).decode() if primary_email else ""

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

        dfs_login    = env.get("DATAFORSEO_LOGIN", "").strip()
        dfs_password = env.get("DATAFORSEO_PASSWORD", "").strip()
        semrush_key  = env.get("SEMRUSH_API_KEY", "").strip()
        domain = re.sub(r"https?://", "", website).rstrip("/")
        loc_data = {"primary_city": "", "primary_state": "", "location_code": 2840,
                    "all_locations": [], "is_multi_location": False, "location_source": "fallback"}

        if dfs_login and dfs_password:
            print("  Detecting practice location (city-level SERP targeting)...")
            raw_scrape_text = raw_scrape if isinstance(raw_scrape, str) else ""
            brand = row.get("practice_name") or row.get("name") or ""
            loc_data = fetch_practice_location(
                domain, brand, raw_scrape_text, dfs_login, dfs_password
            )
            print(f"  ✓ Location: {loc_data.get('primary_city', '?')}, {loc_data.get('primary_state', '?')} "
                  f"(source: {loc_data.get('location_source', 'unknown')}, "
                  f"code: {loc_data.get('location_code', 2840)})")
            print("  Fetching DataForSEO API (~$0.04/domain)...")
            semrush = None
            for _attempt in range(2):
                try:
                    semrush = fetch_dataforseo(
                        domain, dfs_login, dfs_password,
                        city=loc_data.get("primary_city", ""),
                        state=loc_data.get("primary_state", ""),
                        location_code=loc_data.get("location_code", 2840),
                    )
                    ai_serp  = semrush.get("ai_overview_serp_count", "N/A")
                    ai_cited = semrush.get("ai_overview_cited_count", "N/A")
                    print(f"  ✓ DataForSEO: {semrush['unique_keywords']:,} KWs | "
                          f"rank #{semrush['domain_rank']:,} | "
                          f"{semrush['quick_wins_count']} quick wins | "
                          f"${semrush['traffic_value']:,}/mo | "
                          f"AI Overview SERPs: {ai_serp} (cited: {ai_cited})")
                    break
                except Exception as e:
                    print(f"  ⚠️  DataForSEO attempt {_attempt+1}/2 failed: {e}")
                    if _attempt == 0:
                        import time as _t; _t.sleep(5)
            if semrush is None:
                print("  ⚠️  DataForSEO unavailable after retry — continuing with empty SEO data")
                semrush = parse_semrush("")
        else:
            print("  ⚠️  DataForSEO not configured — add DATAFORSEO_LOGIN/PASSWORD to .env for live data")
            semrush = parse_semrush("")
        print(f"  ✓ {semrush['unique_keywords']:,} keywords | {semrush['quick_wins_count']} quick wins | ~{semrush['estimated_traffic']:,} traffic/mo")

        # Save SEMrush data for Claude Code SEO analysis step
        semrush_data_path.write_text(
            json.dumps(semrush, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        print(f"  Phase 1 complete ({time.time()-t0:.1f}s)")

    # Brand colors + page assets (logo, favicon): load from cache or extract
    brand_colors_path = run_dir / "brand_colors.json"
    page_assets_path  = run_dir / "page_assets.json"

    if brand_colors_path.exists():
        brand_colors = json.loads(brand_colors_path.read_text(encoding="utf-8"))
        print(f"  ✓ Brand colors loaded from brand_colors.json (pre-extracted)")
    else:
        print(f"  Extracting brand colors via CSS ({website})...")
        brand_colors = extract_brand_colors_css(website)
        brand_colors_path.write_text(json.dumps(brand_colors, indent=2, ensure_ascii=False), encoding="utf-8")
        n_colors = len([v for v in brand_colors.values() if str(v).startswith("#")])
        print(f"  ✓ Brand colors extracted ({n_colors} colors, method: {brand_colors.get('source', 'unknown')})")

    if page_assets_path.exists():
        page_assets = json.loads(page_assets_path.read_text(encoding="utf-8"))
        print(f"  ✓ Page assets loaded from cache (logo: {'yes' if page_assets.get('logo_url') else 'missing'})")
    else:
        print(f"  Extracting logo + favicon from HTML ({website})...")
        page_assets = extract_page_assets(website)
        page_assets_path.write_text(json.dumps(page_assets, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  ✓ Logo: {page_assets.get('logo_url') or 'not found'}")
        print(f"  ✓ Favicon: {page_assets.get('favicon_url') or 'not found'}")

    # ── PHASE 1-ONLY EXIT ──────────────────────────────────────────────────────
    if phase1_only or dry_run:
        # Write phase1_data.json now so Claude Code can generate SEO report + phase2_output.json
        # Practice name / doctor name will be enriched when phase2_output.json is available
        logo_url    = page_assets.get("logo_url", "")
        favicon_url = page_assets.get("favicon_url", "")
        booking_url = extract_booking_url(raw_scrape, website) if raw_scrape else website
        p1_data = {
            "run_id":           run_id,
            "website":          website,
            "context":          context,
            "raw_scrape":       raw_scrape[:6000] if raw_scrape else "",
            "semrush":          semrush,
            "crawl":            crawl,
            "brand_colors":     brand_colors,
            "name":             "",        # enriched from phase2_output.json app_config
            "doctor_name":      "",        # enriched from phase2_output.json app_config
            "booking_url":      booking_url,
            "logo_url":         logo_url,
            "primary_city":     loc_data.get("primary_city", ""),
            "primary_state":    loc_data.get("primary_state", ""),
            "location_code":    loc_data.get("location_code", 2840),
            "all_locations":    loc_data.get("all_locations", []),
            "is_multi_location": loc_data.get("is_multi_location", False),
            "location_source":  loc_data.get("location_source", "fallback"),
            "images": {
                "logo_url":    logo_url,
                "favicon_url": favicon_url,
                "hero_url":    "",
                "headshot_url": "",
            },
        }
        (run_dir / "phase1_data.json").write_text(
            json.dumps(p1_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

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
        # Pre-generated by Claude Code natively — load and write enriched phase1_data.json
        phase2_data = json.loads(phase2_output_path.read_text(encoding="utf-8"))
        print(f"\n🤖 Phase 2: Loaded from existing phase2_output.json ({len(phase2_data)} keys)")

        # ── Write enriched phase1_data.json (required by inject_report.py for Phase 3) ──
        app_cfg = phase2_data.get("app_config", {})

        # Use Phase 2 colors if they are non-generic, else keep Phase 1 CSS colors
        p2_primary = app_cfg.get("primaryColor", "")
        if p2_primary and p2_primary not in _THIRD_PARTY_COLORS and p2_primary.upper() not in ("#333333", "#222222", "#111111", "#000000", "#FFFFFF", "#FAFAFA"):
            merged_colors = dict(brand_colors)
            merged_colors["primary"]    = p2_primary
            merged_colors["accent"]     = app_cfg.get("primaryLight", brand_colors.get("accent", ""))
            merged_colors["secondary"]  = app_cfg.get("primaryDark", brand_colors.get("secondary", ""))
            merged_colors["background"] = app_cfg.get("backgroundColor", brand_colors.get("background", "#FFFFFF"))
            merged_colors["source"]     = "phase2_app_config"
        else:
            merged_colors = brand_colors

        logo_url = page_assets.get("logo_url", "")
        favicon_url = page_assets.get("favicon_url", "")

        phase1_data_for_inject = {
            "run_id":       run_id,
            "website":      website,
            "context":      context,
            "raw_scrape":   raw_scrape[:6000] if raw_scrape else "",
            "semrush":      semrush,
            "crawl":        crawl,
            "brand_colors": merged_colors,
            # Enriched from Phase 2 app_config
            "name":         app_cfg.get("practiceName", app_cfg.get("practice_name", "")),
            "doctor_name":  app_cfg.get("providerName", app_cfg.get("provider_name", "")),
            "booking_url":  app_cfg.get("bookingUrl", app_cfg.get("booking_url",
                            extract_booking_url(raw_scrape, website) if raw_scrape else website)),
            # Logo + favicon extracted from live HTML
            "logo_url":     logo_url,
            "images":       {
                "logo_url":    logo_url,
                "favicon_url": favicon_url,
                "hero_url":    "",
                "headshot_url": "",
            },
        }
        (run_dir / "phase1_data.json").write_text(
            json.dumps(phase1_data_for_inject, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    else:
        # ── Phase 2: PENDING — Claude Code generates natively (zero API cost) ──
        print(f"\n🤖 Phase 2: PENDING — generate phase2_output.json natively in Claude Code")
        print(f"   Read phase1_data.json + use build_phase2_prompt() from this runner as the prompt.")

        # Write partial phase1_data.json so Claude Code has all scraped data as input
        _booking = extract_booking_url(raw_scrape, website) if raw_scrape else website
        _logo    = page_assets.get("logo_url", "")
        _favicon = page_assets.get("favicon_url", "")
        phase1_partial = {
            "run_id":       run_id,
            "website":      website,
            "context":      context,
            "raw_scrape":   raw_scrape[:6000] if raw_scrape else "",
            "semrush":      semrush,
            "crawl":        crawl,
            "brand_colors": brand_colors,
            "name":         "",
            "doctor_name":  "",
            "booking_url":  _booking,
            "logo_url":     _logo,
            "images":       {
                "logo_url":    _logo,
                "favicon_url": _favicon,
                "hero_url":    "",
                "headshot_url": "",
            },
        }
        (run_dir / "phase1_data.json").write_text(
            json.dumps(phase1_partial, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  ✓ phase1_data.json written — ready for Claude Code native Phase 2")
        print(f"  ⏭  Skipping Phase 3 for {domain} — run --phase3-only after Phase 2 completes")
        return {"url": website, "run_dir": str(run_dir), "status": "phase2_pending",
                "domain_rank": semrush.get("domain_rank", 0),
                "unique_keywords": semrush.get("unique_keywords", 0)}

    print(f"  Quick wins: {semrush.get('quick_wins_count', 0)}")

    # ── PHASE 3: Inject template → index.html → Deploy ──────────────────────────
    print("\n🚀 Phase 3: Building deliverables page from template + deploying...")
    t3 = time.time()

    # Extract practice name from phase1_data.json (most reliable source)
    phase1_data_path = run_dir / "phase1_data.json"
    practice_name = None
    if phase1_data_path.exists():
        try:
            p1_loaded = json.loads(phase1_data_path.read_text(encoding="utf-8"))
            practice_name = p1_loaded.get("name")
        except Exception:
            pass
    if not practice_name:
        practice_name = (
            phase2_data.get("app_config", {}).get("practice_name")
            or phase2_data.get("app_config", {}).get("practiceName")
            or re.sub(r"https?://", "", website).rstrip("/")
        )

    slack_webhook = env.get("SLACK_WEBHOOK_URL", "")

    # ── 3a: Inject template → index.html ────────────────────────────────────────
    injector_path = SCRIPT_DIR / "inject_report.py"
    if injector_path.exists():
        # Run injector as subprocess to isolate imports
        import subprocess as _sp
        inj_result = _sp.run(
            [sys.executable, str(injector_path), str(run_dir)],
            capture_output=True, text=True, timeout=60,
        )
        if inj_result.returncode != 0:
            raise RuntimeError(
                f"BUILD_FAILED: inject_report.py failed:\n{inj_result.stderr}\n{inj_result.stdout}"
            )
        print(inj_result.stdout.strip())
    else:
        # Fall back: seo_report.html must already exist (legacy mode)
        seo_report_path = run_dir / "seo_report.html"
        if not seo_report_path.exists():
            raise RuntimeError(
                f"BUILD_FAILED: Neither inject_report.py nor seo_report.html found. "
                f"Ensure {injector_path} exists or run SKILL_D100_report_builder first."
            )
        import shutil as _sh
        _sh.copy(str(seo_report_path), str(run_dir / "index.html"))
        print(f"  ✓ Copied seo_report.html → index.html (legacy mode)")

    index_path = run_dir / "index.html"
    if not index_path.exists():
        raise RuntimeError(f"BUILD_FAILED: index.html not found in {run_dir} after injection")
    if index_path.stat().st_size < 10_000:
        raise RuntimeError(
            f"BUILD_FAILED: index.html too small ({index_path.stat().st_size} bytes)"
        )
    print(f"  ✓ index.html ready — {index_path.stat().st_size // 1024}KB")

    # ── 3b: Deploy ────────────────────────────────────────────────────────────────
    vercel_token = env.get("VERCEL_TOKEN", "")
    if vercel_token and not dry_run:
        # Vercel incremental deploy — single project, subfolder per company
        # healthbizleads.com/[slug]/  +  app.healthbizleads.com/[slug]/
        sys.path.insert(0, str(SCRIPT_DIR))
        from deploy_vercel_incremental import deploy_deliverables, deploy_assessment_app
        report_url = deploy_deliverables(run_dir, practice_name, vercel_token, dry_run=False)
        # Deploy assessment app (best-effort — don't fail the run if app deploy errors)
        try:
            p1_data = json.loads((run_dir / "phase1_data.json").read_text(encoding="utf-8"))
            p2_data = json.loads((run_dir / "phase2_output.json").read_text(encoding="utf-8")) if (run_dir / "phase2_output.json").exists() else {}
            app_url = deploy_assessment_app(run_dir, practice_name, vercel_token, p1_data, p2_data, dry_run=False)
            print(f"  ✓ App URL: {app_url}")
        except Exception as app_err:
            print(f"  ⚠ App deploy failed (non-fatal): {app_err}")
            app_url = None
    else:
        # Fall back to GitHub Pages
        if not vercel_token:
            print("  ℹ VERCEL_TOKEN not set — falling back to GitHub Pages")
        report_url = deploy_report_to_github(run_dir, practice_name, dry_run=dry_run)
        app_url = None

    print(f"  ✓ Live URL: {report_url}")
    ref_url = f"{report_url}?ref={ref_token}" if ref_token else report_url
    if ref_token:
        print(f"  ✓ Ref URL (send this): {ref_url}")
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
        json.dumps({
            "report_url": report_url,
            "app_url":    app_url,
            "practice":   practice_name,
            "run_id":     run_id,
        }, indent=2),
        encoding="utf-8",
    )

    # Slack success — fires automatically when SLACK_WEBHOOK_URL is set; suppressed with --preview
    if slack_webhook and not preview:
        try:
            notify_slack_report_live(slack_webhook, practice_name, report_url, website, semrush, run_id,
                                          ref_url=ref_url, primary_email=primary_email)
            print("  ✓ Slack notified")
        except Exception as e:
            print(f"  ⚠️  Slack failed: {e}")

    # Google Sheets tracking — append row if GOOGLE_SHEETS_ID is set
    sheets_id = env.get("GOOGLE_SHEETS_ID", "")
    if sheets_id:
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from sheets_helper import append_to_tracking_sheet
            append_to_tracking_sheet(sheets_id, {
                "Company Name":     practice_name,
                "Website":          website,
                "Run Date":         datetime.now().strftime("%Y-%m-%d"),
                "Deliverables URL": report_url,
                "App URL":          app_url or "",
                "Preview URL":      f"{report_url}?preview=1",
                "Loom Status":      "PENDING",
                "Organic Traffic":  semrush.get("estimated_traffic", 0),
                "Keywords":         semrush.get("unique_keywords", 0),
                "Quick Wins":       semrush.get("quick_wins_count", 0),
                "Outreach Status":  "NOT_SENT",
            })
            print("  ✓ Sheets row appended")
        except Exception as e:
            print(f"  ⚠️  Sheets append failed: {e}")

    # ── Summary ────────────────────────────────────────────────────────────────
    files = list(run_dir.rglob("*"))
    file_list = [str(f.relative_to(run_dir)) for f in files if f.is_file()]
    print(f"\n✅ COMPLETE — {run_id}")
    print(f"   Preview: {report_url}?preview=1")
    print(f"   Live:    {report_url}")
    if ref_token:
        print(f"   📧 Send this URL: {ref_url}")
    else:
        print(f"   ⚠️  No email in CSV — SmartLead tracking disabled (add 'emails' column)")
    if app_url:
        print(f"   App:     {app_url}")
    print(f"   Files: {', '.join(file_list)}")

    return {
        "run_id": run_id,
        "status": "completed",
        "website": website,
        "report_url": report_url,
        "ref_url": ref_url,
        "primary_email": primary_email,
        "gamma_url": report_url,   # shim — CSV column kept for backward compat
        "keywords_count": len(phase2_data.get("keywords", [])),
        "quick_wins": semrush.get("quick_wins_count", 0),
        "traffic_value": semrush.get("traffic_value", 0),
        "ai_overview_serp_count": semrush.get("ai_overview_serp_count", "N/A"),
    }


# ── Main ───────────────────────────────────────────────────────────────────────
MAX_WORKERS = 5  # 5 parallel runs ≈ 5x throughput; safe for DataForSEO + Vercel rate limits


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


def run_with_checkpoint(args_tuple):
    """Thread worker: checkpoint check → run_single → write checkpoint on success."""
    i, row, env, dry_run, phase1_only, existing_run_dir, preview_flag = args_tuple
    website = row.get("website", "")

    # Checkpoint: skip already-completed runs
    existing = find_run_dir_for_site(website) if not existing_run_dir else existing_run_dir
    if existing:
        checkpoint = Path(existing) / "checkpoint.json"
        if checkpoint.exists():
            try:
                chk = json.loads(checkpoint.read_text(encoding="utf-8"))
                if chk.get("status") == "completed":
                    return {"website": website, "status": "skipped_checkpoint",
                            "report_url": chk.get("report_url", ""),
                            "gamma_url": chk.get("report_url", "")}
            except Exception:
                pass

    result = run_single(row, env, dry_run=dry_run, phase1_only=phase1_only,
                        existing_run_dir=existing_run_dir,
                        preview=preview_flag)

    # Write checkpoint on success
    if result.get("status") == "completed":
        run_dir_path = OUTPUT_ROOT / result.get("run_id", "")
        if run_dir_path.exists():
            try:
                (run_dir_path / "checkpoint.json").write_text(
                    json.dumps({"status": "completed",
                                "report_url": result.get("report_url", ""),
                                "timestamp": datetime.now().isoformat()},
                               indent=2),
                    encoding="utf-8"
                )
            except Exception:
                pass

    return result


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
                             "run Phase 3 (template inject → Vercel/GitHub Pages + Slack) only.")
    parser.add_argument("--run-dir", type=str, default=None,
                        help="Existing run directory to use (single-site override for --phase3-only).")
    parser.add_argument("--preview", action="store_true",
                        help="Preview run — suppresses Slack notification even if webhook is configured.")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        sys.exit(1)

    env = load_env()
    dfs_status = "✓ DataForSEO" if (env.get("DATAFORSEO_LOGIN") and env.get("DATAFORSEO_PASSWORD")) else ""
    smr_status = "✓ SEMrush (fallback)" if env.get("SEMRUSH_API_KEY") else ""
    seo_status = dfs_status or smr_status or "✗ no SEO API"
    print(f"✓ Env loaded: SEO={seo_status} | "
          f"Slack={'✓ always-on' if env.get('SLACK_WEBHOOK_URL') else '✗ no webhook (add SLACK_WEBHOOK_URL)'}")
    print(f"  Note: All LLM generation is Claude Code native (Claude Max — zero API cost)")
    vercel_tok = env.get("VERCEL_TOKEN", "")
    print(f"  Note: Phase 3 = template inject → {'Vercel' if vercel_tok else 'GitHub Pages'}")

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

    # ── Run all sites (parallel, max_workers=3) ──────────────────────────────────
    n = len(rows)
    results = []
    failure_count = 0
    FAILURE_LIMIT = 3
    slack_webhook = env.get("SLACK_WEBHOOK_URL", "")

    # Build args for each row; resolve phase3-only run dirs upfront (serial, fast)
    worker_args = []
    for i, row in enumerate(rows):
        website = row.get("website", "?")
        existing_run_dir = args.run_dir
        if args.phase3_only and not existing_run_dir:
            existing_run_dir = find_run_dir_for_site(website)
            if not existing_run_dir:
                print(f"  ⚠️  No run dir with phase2_output.json found for {website} — skipping")
                results.append({"website": website, "status": "skipped_no_phase2", "report_url": ""})
                continue
            print(f"  📁 [{i+1}/{n}] {website} → {existing_run_dir}")
        worker_args.append((i, row, env, args.dry_run, args.phase1_only, existing_run_dir, getattr(args, "preview", False)))

    workers = 1 if (args.site_index is not None or args.phase1_only) else MAX_WORKERS
    print(f"\n🚀 Starting {len(worker_args)} run(s) with max_workers={workers}...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_row = {executor.submit(run_with_checkpoint, a): a[1] for a in worker_args}
        for future in concurrent.futures.as_completed(future_to_row):
            row = future_to_row[future]
            website = row.get("website", "?")
            context = row.get("context", "")
            practice_name_hint = context.split(";")[0].strip() if context else website
            try:
                result = future.result()
                results.append(result)
                status = result.get("status", "")
                if status == "completed":
                    failure_count = 0
                    print(f"  ✅ {website} → {result.get('report_url','')}")
                elif status == "skipped_checkpoint":
                    print(f"  ⏭  {website} already done → {result.get('report_url','')}")
                elif status not in ("failed", "scrape_failed", "semrush_failed", "build_failed"):
                    failure_count = 0
            except Exception as e:
                err_str = str(e)
                print(f"  ❌ FAILED: {website}: {err_str[:200]}")

                if "SCRAPE_FAILED" in err_str or "scrape" in err_str.lower():
                    failure_type = "SCRAPE_FAILED"
                elif "SEMRUSH_FAILED" in err_str or "semrush" in err_str.lower():
                    failure_type = "SEMRUSH_FAILED"
                elif "BUILD_FAILED" in err_str or "seo_report" in err_str.lower():
                    failure_type = "BUILD_FAILED"
                else:
                    failure_type = "BUILD_FAILED"

                result = {
                    "website": website,
                    "status": failure_type.lower(),
                    "error": err_str[:500],
                    "report_url": "",
                    "gamma_url": "",
                }
                results.append(result)

                if slack_webhook:
                    notify_slack_error(slack_webhook, practice_name_hint, website,
                                       failure_type, err_str, "unknown")

                failure_count += 1
                print(f"  ⚠️  Failures so far: {failure_count}/{FAILURE_LIMIT}")
                if failure_count >= FAILURE_LIMIT:
                    msg = f"🛑 D100 halted — {FAILURE_LIMIT} failures. Last error on {website}: {err_str[:200]}"
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

    success = sum(1 for r in results if r.get("status") in ("completed", "submitted", "skipped_checkpoint", "phase1_complete", "dry_run"))
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {success}/{len(results)} succeeded")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
