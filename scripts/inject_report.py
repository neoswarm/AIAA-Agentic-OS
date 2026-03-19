#!/usr/bin/env python3
"""
inject_report.py — D100 Template Injector
==========================================
Reads phase1_data.json + phase2_output.json from a run directory,
replaces all {{PLACEHOLDER}} tokens in seo_report_template.html,
and writes index.html ready for Vercel deployment.

Usage:
    python3 inject_report.py <run_dir>
    python3 inject_report.py <run_dir> --deploy-vercel
    python3 inject_report.py <run_dir> --dry-run

Zero Claude tokens. Runs in <5 seconds.
"""

import json
import re
import sys
import os
import shutil
import urllib.request
import urllib.parse
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from html import escape

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
TEMPLATE    = PROJECT_DIR / "templates" / "seo_report_template.html"

# Load .env into os.environ (simple parser — no external dependency)
_env_path = PROJECT_DIR / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


# ── Helpers ───────────────────────────────────────────────────────────────────


def _clarity_snippet(project_id: str) -> str:
    """Return the Microsoft Clarity <script> tag, or '' if no project_id."""
    if not project_id:
        return ""
    return (
        '<script type="text/javascript">'
        "(function(c,l,a,r,i,t,y){"
        "c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};"
        "t=l.createElement(r);t.async=1;"
        't.src="https://www.clarity.ms/tag/"+i;'
        "y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);"
        f'}})(window,document,"clarity","script","{project_id}");'
        "</script>"
    )

def fmt_number(n, default="N/A"):
    """4561840 → '4,561,840'"""
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return default


def fmt_domain_rank(n):
    """Format domain rank: 4561840 → '#4,561,840'. Returns empty string when 0."""
    try:
        v = int(n)
        if v == 0:
            return ""
        return f"#{v:,}"
    except (TypeError, ValueError):
        return ""


def build_domain_rank_display(semrush: dict):
    """
    Return (display_value, label) for the Domain Rank stat card.
    Priority:
      1. domain_rank (global ordinal) if > 0 — only populated for high-authority domains
      2. Page 1 Keywords (pos 1-10 count) — always real, easy to understand for practice owners
      3. avg_position (weighted avg keyword position) — always computable
    Never returns N/A.
    """
    dr = semrush.get("domain_rank", 0) or 0
    if dr > 0:
        return f"#{dr:,}", "Domain Rank"

    # Page 1 Keywords: count of keywords ranking positions 1-10.
    # More compelling and understandable than an abstract authority score.
    # "You have 662 keywords on page 1 of Google right now."
    page1 = (
        (semrush.get("pos1_count", 0) or 0) +
        (semrush.get("pos2_3_count", 0) or 0) +
        (semrush.get("pos4_10_count", 0) or 0)
    )
    if page1 > 0:
        return f"{page1:,}", "Page 1 Keywords"

    avg_pos = semrush.get("avg_position", 0) or 0
    if avg_pos > 0:
        return f"{avg_pos:.1f}", "Avg. Position"

    return "New", "SEO Status"


def difficulty_label(kd):
    """Return color-coded difficulty label."""
    try:
        kd = float(kd)
    except (TypeError, ValueError):
        return '<span style="color:#94a3b8;">N/A</span>'
    if kd == 0:
        return '<span style="color:#22c55e;font-weight:700;">Very Easy</span>'
    if kd < 15:
        return '<span style="color:#22c55e;font-weight:700;">Easy</span>'
    if kd < 30:
        return '<span style="color:#f59e0b;font-weight:700;">Medium</span>'
    return '<span style="color:#ef4444;font-weight:700;">Hard</span>'


def action_for_quick_win(position):
    """Return recommended action based on position."""
    try:
        pos = int(position)
    except (TypeError, ValueError):
        return "Optimize content"
    if pos <= 5:
        return "Featured snippet grab"
    if pos <= 10:
        return "Push to top 3"
    return "Push to page 1"


def escape_html(s):
    return escape(str(s)) if s else ""


def _extract_city(p1: dict) -> str:
    """Extract city from context string."""
    context = p1.get("context", "") or ""
    m = re.search(r'([A-Z][a-zA-Z\s]+,\s*[A-Z]{2})', context)
    if m:
        return m.group(1).strip()
    website = p1.get("website", "")
    if website:
        domain = website.replace("https://","").replace("http://","").split("/")[0].split(".")[0]
        return domain.replace("-"," ").title()
    return "your area"


def _extract_primary_condition(p1: dict) -> str:
    """Extract primary condition from keywords or practice name."""
    app_cfg = p1.get("app_config", {}) or {}
    specialty = app_cfg.get("specialty", "") or app_cfg.get("primary_condition", "")
    if specialty:
        return specialty.lower()
    semrush = p1.get("semrush", {}) or {}
    top = semrush.get("top_by_volume", [])
    if top:
        kw = top[0].get("keyword", "")
        kw = re.sub(r'\b(near me|michigan|mi|bloomfield|west|dr|doctor|specialist|com)\b', '', kw, flags=re.IGNORECASE).strip()
        if kw:
            return kw.lower()
    name = (p1.get("name", "") or "").lower()
    for word in ["chiropractic", "functional medicine", "naturopathic", "integrative", "neurofeedback"]:
        if word in name:
            return word
    return "your condition"


def extract_favicon_url(raw_scrape: str, website: str) -> str:
    """Try to extract favicon from scraped HTML."""
    patterns = [
        r'<link[^>]+rel=["\'](?:shortcut )?icon["\'][^>]+href=["\']([^"\']+)["\']',
        r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\'](?:shortcut )?icon["\']',
    ]
    for pat in patterns:
        m = re.search(pat, raw_scrape, re.IGNORECASE)
        if m:
            href = m.group(1)
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                base = website.rstrip("/")
                href = base + href
            return href
    # Default: try /favicon.ico
    return website.rstrip("/") + "/favicon.ico"


def download_favicon(favicon_url: str, dest: Path) -> bool:
    """Download favicon to dest. Returns True on success."""
    try:
        req = urllib.request.Request(
            favicon_url,
            headers={"User-Agent": "Mozilla/5.0 (D100 Runner)"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"  ⚠ Favicon download failed ({favicon_url}): {e}")
        return False


# ── HTML Builders ─────────────────────────────────────────────────────────────

def build_quick_wins_rows(quick_wins: list) -> str:
    """Build <tr> rows for Quick Wins table."""
    if not quick_wins:
        return '<tr><td colspan="5" style="padding:20px;color:#94a3b8;text-align:center;">No quick wins data available.</td></tr>'

    rows = []
    for qw in quick_wins:
        kw   = escape_html(qw.get("keyword", ""))
        pos  = qw.get("position", "–")
        vol  = fmt_number(qw.get("volume", 0))
        kd   = qw.get("kd", 0)
        action = action_for_quick_win(pos)
        rows.append(f"""<tr style="border-bottom:1px solid rgba(255,255,255,0.06);">
              <td style="padding:14px 16px;color:#f0f4ff;font-weight:600;">{kw}</td>
              <td style="padding:14px 16px;color:#84bdbb;font-weight:700;font-size:1.2rem;">#{pos}</td>
              <td style="padding:14px 16px;color:#f0f4ff;">{vol}/mo</td>
              <td style="padding:14px 16px;">{difficulty_label(kd)}</td>
              <td style="padding:14px 16px;color:#84bdbb;font-style:italic;">{action}</td>
            </tr>""")
    return "\n".join(rows)


# Domains to exclude from competitors table — social, directories, info giants
_COMPETITOR_BLOCKLIST = {
    # Social media
    "facebook.com", "youtube.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "pinterest.com", "tiktok.com", "reddit.com", "quora.com",
    # Directories & review sites
    "yelp.com", "healthgrades.com", "ratemds.com", "vitals.com", "doximity.com",
    "findatopdoc.com", "zocdoc.com", "booksy.com", "thumbtack.com", "bark.com",
    "homeadvisor.com", "massagebook.com", "massageenvy.com", "thervo.com",
    # Generic web
    "google.com", "maps.google.com", "amazon.com", "wikipedia.org",
    "dictionary.cambridge.org", "dictionary.com", "merriam-webster.com", "thesaurus.com",
    # National health publishers & government
    "webmd.com", "healthline.com", "mayoclinic.org", "clevelandclinic.org",
    "medlineplus.gov", "nih.gov", "cdc.gov", "who.int", "cancer.gov", "va.gov",
    "hhs.gov", "fda.gov", "betterhealth.vic.gov.au", "hms.harvard.edu",
    "hopkinsmedicine.org", "usnews.com", "nytimes.com",
    "verywellhealth.com", "medicalnewstoday.com", "everydayhealth.com",
    "drugs.com", "rxlist.com", "psychologytoday.com", "psychology-today.com",
    # Professional associations (not direct competitors)
    "amtamassage.org", "medicalacupuncture.org",
}

def _is_real_competitor(domain: str, own_domain: str = "") -> bool:
    """Return True if this domain is likely an actual competing practice."""
    d = domain.lower().strip()
    if own_domain and d == own_domain.lower().replace("https://", "").replace("www.", "").rstrip("/"):
        return False
    for blocked in _COMPETITOR_BLOCKLIST:
        if d == blocked or d.endswith("." + blocked):
            return False
    return True


def build_competitors_rows(competitors: list, own_domain: str = "") -> str:
    """Build <tr> rows for Competitors table — filters generic/directory domains."""
    real = [c for c in competitors if _is_real_competitor(c.get("domain", ""), own_domain)]

    if not real:
        return (
            '<tr><td colspan="4" style="padding:20px;color:#94a3b8;text-align:center;">' +
            'No direct practice competitors tracked in this dataset. ' +
            'This means there is an open window — most competing practices in your area ' +
            'are not investing in SEO yet.</td></tr>'
        )

    rows = []
    for comp in real:
        domain   = escape_html(comp.get("domain", ""))
        avg_pos  = comp.get("avg_position", 0) or 0
        source   = comp.get("source", "")
        kw_kw    = escape_html(comp.get("serp_keyword", ""))

        # Position badge — only for SERP-sourced competitors (have real position data)
        if source == "serp" and avg_pos:
            pos_color = "#22c55e" if avg_pos <= 3 else "#f59e0b" if avg_pos <= 7 else "#94a3b8"
            pos_badge = (f'<span style="background:{pos_color};color:#000;font-size:11px;'
                         f'font-weight:800;padding:2px 8px;border-radius:12px;">#{int(avg_pos)}</span>')
            source_note = f'<div style="font-size:11px;color:#64748b;margin-top:3px;">for "{kw_kw}"</div>' if kw_kw else ""
        else:
            kws    = fmt_number(comp.get("keywords", 0))
            pos_badge   = f'<span style="color:#84bdbb;font-weight:700;">{kws} kws</span>'
            source_note = ""

        # Traffic display
        traffic_raw = comp.get("traffic", 0) or 0
        traffic_display = f"{fmt_number(traffic_raw)}/mo" if traffic_raw > 0 else "—"

        # Type badge
        comp_type = comp.get("competitor_type", "practice")
        type_badge = ('<span style="background:#334155;color:#94a3b8;font-size:10px;font-weight:700;'
                      'padding:2px 7px;border-radius:10px;letter-spacing:0.05em;">HEALTH SYSTEM</span>'
                      if comp_type == "health_system" else
                      '<span style="background:#14532d;color:#86efac;font-size:10px;font-weight:700;'
                      'padding:2px 7px;border-radius:10px;letter-spacing:0.05em;">PRACTICE</span>')

        rows.append(f"""<tr style="border-bottom:1px solid rgba(255,255,255,0.06);">
              <td style="padding:14px 16px;color:#f0f4ff;font-family:monospace;">{domain}{source_note}</td>
              <td style="padding:14px 16px;">{pos_badge}</td>
              <td style="padding:14px 16px;color:#f0f4ff;">{traffic_display}</td>
              <td style="padding:14px 16px;">{type_badge}</td>
            </tr>""")
    return "\n".join(rows)


def build_data_nerds_rows(semrush: dict) -> str:
    """Build full data breakdown table rows."""
    rows_data = [
        ("Page 1 Keywords",          fmt_number(
            (semrush.get("pos1_count", 0) or 0) +
            (semrush.get("pos2_3_count", 0) or 0) +
            (semrush.get("pos4_10_count", 0) or 0)
        )),
        ("Top 3 Keywords",           fmt_number(
            (semrush.get("pos1_count", 0) or 0) +
            (semrush.get("pos2_3_count", 0) or 0)
        )),
        ("Avg. Keyword Position",    str(semrush.get("avg_position", 0) or "—")),
        ("Total Keywords Ranked",   fmt_number(semrush.get("unique_keywords", 0))),
        ("Estimated Monthly Traffic", fmt_number(semrush.get("estimated_traffic", 0)) + " visits"),
        ("Traffic Value",           f"${fmt_number(semrush.get('traffic_value', 0))}/mo"),
        ("Keywords in Position 1",  fmt_number(semrush.get("pos1_count", 0))),
        ("Keywords in Position 2–3", fmt_number(semrush.get("pos2_3_count", 0))),
        ("Keywords in Position 4–10", fmt_number(semrush.get("pos4_10_count", 0))),
        ("Keywords in Position 11–20", fmt_number(semrush.get("pos11_20_count", 0))),
        ("Quick Win Keywords",      fmt_number(semrush.get("quick_wins_count", 0))),
        ("AI Overview SERPs",       fmt_number(semrush.get("ai_overview_serp_count", 0))),
        ("AI Overview Citations",   fmt_number(semrush.get("ai_overview_cited_count", 0))),
        ("SERP Features Traffic",   fmt_number(semrush.get("serp_features_traffic", 0))),
    ]
    rows = []
    for i, (label, value) in enumerate(rows_data):
        bg = "rgba(255,255,255,0.02)" if i % 2 == 0 else "transparent"
        rows.append(f"""<tr style="background:{bg};">
              <td style="padding:12px 16px;color:#94a3b8;font-size:1.05rem;">{label}</td>
              <td style="padding:12px 16px;color:#f0f4ff;font-weight:700;font-size:1.1rem;">{value}</td>
            </tr>""")
    return "\n".join(rows)


def build_keyword_rows_html(semrush: dict, phase2_keywords: list) -> str:
    """Build interactive keyword accordion rows from SEMrush + phase2 data."""
    rows = []
    seen = set()

    def kd_badge(kd):
        if kd == 0:
            return '<span style="background:#d1fae5;color:#065f46;font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;">Easy</span>'
        elif kd < 30:
            return '<span style="background:#fef3c7;color:#92400e;font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;">Low</span>'
        elif kd < 60:
            return '<span style="background:#fde68a;color:#78350f;font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;">Medium</span>'
        else:
            return '<span style="background:#fee2e2;color:#991b1b;font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;">Hard</span>'

    def pos_display(pos):
        if pos <= 3:
            color = "#10b981"
        elif pos <= 10:
            color = "#f59e0b"
        else:
            color = "#94a3b8"
        return f'<span style="font-weight:700;color:{color};">#{pos}</span>'

    def add_row(kw, pos, vol, kd, row_type, i):
        bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
        type_badge = (
            '<span style="background:rgba(132,189,187,0.15);color:var(--brand-accent);font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;">Quick Win</span>'
            if row_type == "quick_win" else
            '<span style="background:#eff6ff;color:#3b82f6;font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;">Ranking</span>'
            if row_type == "ranking" else
            '<span style="background:#f5f3ff;color:#7c3aed;font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;">Target</span>'
        )
        pos_str = pos_display(pos) if pos else '<span style="color:#cbd5e1;font-size:13px;">—</span>'
        vol_str = f'{vol:,}' if vol else '<span style="color:#cbd5e1;font-size:13px;">—</span>'
        kd_str  = kd_badge(kd) if kd is not None else '<span style="color:#cbd5e1;font-size:13px;">—</span>'
        return (
            f'<tr style="background:{bg};">'
            f'<td style="padding:12px 16px;color:#1e293b;font-weight:500;font-size:15px;text-align:left;">{escape_html(kw)}</td>'
            f'<td style="padding:12px 16px;text-align:center;">{pos_str}</td>'
            f'<td style="padding:12px 16px;text-align:center;font-size:15px;color:#334155;">{vol_str}</td>'
            f'<td style="padding:12px 16px;text-align:center;">{kd_str}</td>'
            f'<td style="padding:12px 16px;text-align:center;">{type_badge}</td>'
            f'</tr>'
        )

    i = 0
    # Quick wins first (SEMrush data with position/volume/kd)
    for kw_data in semrush.get("top_quick_wins", []):
        kw = kw_data.get("keyword", "")
        if kw and kw not in seen:
            seen.add(kw)
            rows.append(add_row(kw, kw_data.get("position"), kw_data.get("volume", 0), kw_data.get("kd"), "quick_win", i))
            i += 1

    # Top by volume (SEMrush data)
    for kw_data in semrush.get("top_by_volume", []):
        kw = kw_data.get("keyword", "")
        if kw and kw not in seen:
            seen.add(kw)
            rows.append(add_row(kw, kw_data.get("position"), kw_data.get("volume", 0), kw_data.get("kd"), "ranking", i))
            i += 1

    # Phase 2 target keywords (no SEMrush data — just strings)
    for kw in phase2_keywords:
        if isinstance(kw, str) and kw and kw not in seen:
            seen.add(kw)
            rows.append(add_row(kw, None, None, None, "target", i))
            i += 1

    if not rows:
        return '<tr><td colspan="5" style="padding:20px;text-align:center;color:#94a3b8;">No keyword data available</td></tr>'
    return "\n".join(rows)


def build_ad_campaigns_html(ads: list) -> str:
    """Build expandable Google Ad Campaign cards. No copy buttons."""
    if not ads:
        return '<p style="color:#94a3b8;font-size:1.1rem;">Ad campaign data not available.</p>'

    cards = []
    for i, ad in enumerate(ads):
        campaign     = escape_html(ad.get("campaign", f"Campaign {i+1}"))
        headlines    = ad.get("headlines", [])
        descriptions = ad.get("descriptions", [])
        keywords     = ad.get("keywords", [])
        extensions   = ad.get("extensions", {})

        # Headlines list
        hl_items = "\n".join(
            f'<li style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);color:#f0f4ff;font-size:1.05rem;line-height:1.5;">'
            f'<span style="color:#94a3b8;font-size:0.9rem;display:block;margin-bottom:2px;">Headline {j+1}</span>'
            f'{escape_html(h)}</li>'
            for j, h in enumerate(headlines)
        )

        # Descriptions list
        desc_items = "\n".join(
            f'<li style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06);color:#f0f4ff;font-size:1.05rem;line-height:1.6;">'
            f'<span style="color:#94a3b8;font-size:0.9rem;display:block;margin-bottom:2px;">Description {j+1}</span>'
            f'{escape_html(d)}</li>'
            for j, d in enumerate(descriptions)
        )

        # Keywords as comma list
        kw_html = ""
        if keywords:
            kw_pills = " ".join(
                f'<span style="display:inline-block;background:rgba(132,189,187,0.12);border:1px solid rgba(132,189,187,0.3);color:#84bdbb;padding:4px 12px;border-radius:20px;font-size:0.95rem;margin:3px;">{escape_html(k)}</span>'
                for k in keywords
            )
            kw_html = f'<div style="margin-top:20px;"><h4 style="color:#94a3b8;font-size:1rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin:0 0 12px;">Keywords</h4><div>{kw_pills}</div></div>'

        # Extensions
        ext_html = ""
        if extensions:
            ext_lines = []
            for ext_type, items in extensions.items():
                if isinstance(items, list):
                    ext_lines.append(
                        f'<strong style="color:#94a3b8;display:block;margin-bottom:6px;">{escape_html(ext_type)}</strong>'
                        + "\n".join(f'<div style="color:#f0f4ff;font-size:1rem;padding:4px 0;">• {escape_html(str(item))}</div>' for item in items)
                    )
                else:
                    ext_lines.append(f'<div style="color:#f0f4ff;font-size:1rem;"><strong style="color:#94a3b8;">{escape_html(ext_type)}:</strong> {escape_html(str(items))}</div>')
            if ext_lines:
                ext_html = f'''<details style="margin-top:20px;background:rgba(255,255,255,0.04);border-radius:8px;border:1px solid rgba(255,255,255,0.08);">
              <summary style="padding:14px 18px;cursor:pointer;list-style:none;font-size:1rem;font-weight:700;color:#84bdbb;">Ad Extensions</summary>
              <div style="padding:0 18px 18px;">{"".join(ext_lines)}</div>
            </details>'''

        open_attr = ""  # All campaigns start collapsed — prospect chooses to expand
        cards.append(f'''<details {open_attr} style="background:var(--bg-card);border-radius:12px;margin-bottom:20px;border:1px solid var(--border);overflow:hidden;">
          <summary style="padding:24px 28px;cursor:pointer;list-style:none;display:flex;align-items:center;justify-content:space-between;background:var(--bg-card2);">
            <div>
              <div style="font-size:1.3rem;font-weight:800;color:var(--text);">Campaign {i+1}: {campaign}</div>
              <div style="font-size:1rem;color:var(--text-muted);margin-top:4px;">{len(headlines)} headlines · {len(descriptions)} descriptions · {len(keywords)} keywords</div>
            </div>
            <span style="color:var(--brand-accent);font-size:2rem;font-weight:300;flex-shrink:0;margin-left:16px;">+</span>
          </summary>
          <div style="padding:28px;">
            <h4 style="color:#94a3b8;font-size:1rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin:0 0 12px;">Headlines</h4>
            <ul style="list-style:none;margin:0 0 24px;padding:0;">{hl_items}</ul>
            <h4 style="color:#94a3b8;font-size:1rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin:0 0 12px;">Descriptions</h4>
            <ul style="list-style:none;margin:0;padding:0;">{desc_items}</ul>
            {kw_html}
            {ext_html}
          </div>
        </details>''')

    return "\n".join(cards)


def build_patient_email_html(emails: list) -> str:
    """Build patient email sequence cards."""
    if not emails:
        return '<p style="color:#94a3b8;font-size:1.1rem;">Email sequence data not available.</p>'

    email_types = {
        "value_drop":      ("Value Drop",       "Email 1 of 3", "#22c55e"),
        "mechanism_story": ("Mechanism Story",  "Email 2 of 3", "#f59e0b"),
        "proof_results":   ("Proof & Results",  "Email 3 of 3", "#84bdbb"),
    }
    fallback_labels = [("Email 1", "Email 1 of 3", "#22c55e"),
                       ("Email 2", "Email 2 of 3", "#f59e0b"),
                       ("Email 3", "Email 3 of 3", "#84bdbb")]

    cards = []
    for i, email in enumerate(emails):
        etype    = email.get("type", "")
        label, badge, color = email_types.get(etype, fallback_labels[min(i, 2)])
        subject  = escape_html(email.get("subject", ""))
        preview  = escape_html(email.get("preview", ""))
        body_raw = email.get("body", "")

        # Convert newlines to <br> tags, preserve paragraphs
        body_html = ""
        if body_raw:
            paras = [p.strip() for p in str(body_raw).split("\n\n") if p.strip()]
            body_html = "\n".join(
                f'<p style="margin:0 0 16px;color:#d1d5db;font-size:1.05rem;line-height:1.75;">{escape_html(p)}</p>'
                for p in paras
            )

        open_attr = ""  # All emails start collapsed — prospect chooses to expand
        cards.append(f'''<details {open_attr} style="background:var(--bg-card);border-radius:12px;margin-bottom:20px;border:1px solid var(--border);overflow:hidden;">
          <summary style="padding:24px 28px;cursor:pointer;list-style:none;display:flex;align-items:center;justify-content:space-between;background:var(--bg-card2);">
            <div>
              <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
                <span style="background:{color};color:#000;font-size:0.85rem;font-weight:800;padding:3px 10px;border-radius:20px;white-space:nowrap;">{badge}</span>
                <span style="font-size:1.25rem;font-weight:800;color:var(--text);">{label}</span>
              </div>
              <div style="font-size:1.05rem;color:var(--brand-accent);font-weight:600;">Subject: {subject}</div>
              {f'<div style="font-size:0.95rem;color:var(--text-muted);margin-top:4px;font-style:italic;">Preview: {preview}</div>' if preview else ""}
            </div>
            <span style="color:var(--brand-accent);font-size:2rem;font-weight:300;flex-shrink:0;margin-left:16px;">+</span>
          </summary>
          <div style="padding:28px;">
            <div style="background:var(--bg-deep);border-radius:8px;padding:6px 16px;margin-bottom:20px;border-left:3px solid {color};">
              <span style="color:#94a3b8;font-size:0.9rem;">Subject line:</span>
              <div style="color:#f0f4ff;font-weight:700;font-size:1.1rem;margin-top:2px;">{subject}</div>
            </div>
            <div style="font-family:'Georgia',serif;font-size:1.05rem;line-height:1.8;color:#d1d5db;">
              {body_html}
            </div>
          </div>
        </details>''')

    return "\n".join(cards)


# ── Main Injector ─────────────────────────────────────────────────────────────

def build_competitor_context_sentence(semrush: dict, p1: dict) -> str:
    """
    Generate the competitor context sentence under the stats bar.
    Uses real SERP position data and search volume — never shows '0 visits'.
    """
    competitors = semrush.get("competitors", [])
    own_positions = semrush.get("own_serp_positions", {})
    city = p1.get("primary_city", "") or _extract_city(p1)
    state = p1.get("primary_state", "")
    specialty = semrush.get("serp_specialty", "functional medicine")

    # Find the top local competitor (SERP-sourced, lowest position = best rank)
    serp_comps = sorted(
        [c for c in competitors if c.get("source") == "serp" and _is_real_competitor(c.get("domain",""), p1.get("website",""))],
        key=lambda x: x.get("avg_position", 999)
    )

    # Build the geo context string
    geo = f"{city}, {state}" if city and state else city or "your market"

    # Own position context
    own_pos_str = ""
    if own_positions:
        best_kw = min(own_positions, key=own_positions.get)
        best_pos = own_positions[best_kw]
        if best_pos <= 10:
            own_pos_str = f" You rank #{best_pos} — close, but page 1 is where patients book."
        elif best_pos <= 20:
            own_pos_str = f" You're at #{best_pos} — one optimization sprint from being found first."
        else:
            own_pos_str = f" You don't appear in the top 20 yet — this is fixable."

    if serp_comps:
        top_comp = serp_comps[0]
        top_domain = escape_html(top_comp.get("domain", "a competitor"))
        top_pos = top_comp.get("avg_position", 0)
        kw = escape_html(top_comp.get("serp_keyword", f"{specialty} near me"))

        # Format as bold inline
        return (
            f'When patients in <strong>{escape_html(geo)}</strong> search '
            f'<em>"{escape_html(kw)}"</em>, '
            f'<strong>{escape_html(top_domain)}</strong> is the first practice they find '
            f'(ranking #{top_pos}).{own_pos_str} '
            f'Not because they\'re better — because they showed up first.'
        )
    else:
        # Fallback: no SERP competitors, use keyword volume
        total_kws = semrush.get("unique_keywords", 0)
        qw_count  = semrush.get("quick_wins_count", 0)
        loc_str   = f"in {geo} " if geo and geo != "your market" else ""
        return (
            f'Patients {loc_str}are already searching for what you offer — '
            f'<strong>{fmt_number(total_kws)} keywords</strong> rank for your site right now. '
            f'<strong>{fmt_number(qw_count)} of them</strong> are sitting in positions 4–10, '
            f'one push away from page 1. That\'s booked appointments waiting to happen.'
        )


def build_ai_seo_callout(semrush: dict, p1: dict) -> str:
    """
    Build the AI SEO callout paragraph.
    Flips 623/518 impossible math to accurate positive framing:
      - ai_overview_cited_count = times practice content is cited IN AI Overviews (strength)
      - ai_overview_serp_count  = keywords where AI Overview appears in SERP (opportunity/risk)
    """
    cited  = int(semrush.get("ai_overview_cited_count", 0) or 0)
    ai_kws = int(semrush.get("ai_overview_serp_count", 0) or 0)
    practice = escape_html(p1.get("name", "Your Practice"))
    city = p1.get("primary_city", "") or _extract_city(p1)
    city_str = f" in {escape_html(city)}" if city else ""

    if cited > 0 and ai_kws > 0:
        return (
            f'✅ Google\'s AI already cites <strong>{practice}</strong> content '
            f'<strong>{cited:,} times</strong> in AI Overviews — your expertise is surfaced '
            f'before patients even click a link. '
            f'But <strong>{ai_kws:,} of your keywords</strong> now trigger an AI answer box '
            f'where a competitor could displace you overnight. '
            f'AEO (Answer Engine Optimization) locks in your position{city_str} and expands it.'
        )
    elif cited > 0:
        return (
            f'✅ Google\'s AI already cites <strong>{practice}</strong> '
            f'<strong>{cited:,} times</strong> in AI Overviews. '
            f'We build on that foundation with AEO to make you the undisputed source '
            f'AI turns to{city_str} — before your competitors even know this game exists.'
        )
    elif ai_kws > 0:
        return (
            f'🔶 <strong>{ai_kws:,} of your keywords</strong> now show an AI-generated '
            f'answer above organic results{city_str}. Patients get an answer without clicking — '
            f'unless that answer comes from you. '
            f'AEO (Answer Engine Optimization) positions <strong>{practice}</strong> '
            f'as the source Google\'s AI cites. This is the new page 1.'
        )
    else:
        return (
            f'🔶 AI Overviews are reshaping how patients find doctors{city_str}. '
            f'Practices cited in AI answers get traffic without the click competition. '
            f'We build your AEO profile so <strong>{practice}</strong> becomes '
            f'the source Google\'s AI recommends when patients search your specialties.'
        )


def build_replacements(p1: dict, p2: dict) -> dict:
    """
    Build the full token → value mapping from phase1 + phase2 data.
    Returns dict where keys are the placeholder name (without {{ }}).
    """
    semrush = p1.get("semrush", {})
    images  = p1.get("images", {})
    brand   = p1.get("brand_colors", {})
    app_cfg = p2.get("app_config", {})

    # ── Brand colors ─────────────────────────────────────────────────────────
    # Phase 2 app_config colors take priority (validated in runner, non-generic)
    # then fall back to Phase 1 CSS extraction results
    GENERIC_COLORS = {"#333333", "#222222", "#111111", "#000000", "#FFFFFF", "#FAFAFA",
                      "#4285F4", "#34A853", "#FBBC05", "#EA4335", "#1877F2", "#0866FF"}
    p2_primary = app_cfg.get("primaryColor", "")
    if p2_primary and p2_primary.upper() not in GENERIC_COLORS:
        brand_primary = p2_primary
        brand_accent  = (app_cfg.get("primaryLight") or app_cfg.get("primaryDark")
                         or brand.get("accent") or "#84bdbb")
    else:
        brand_primary = brand.get("primary") or "#036797"
        brand_accent  = brand.get("secondary") or brand.get("accent") or "#84bdbb"

    # ── SEO data numbers (DataForSEO primary / SEMrush fallback) ─────────────
    domain_rank, domain_rank_label = build_domain_rank_display(semrush)
    unique_keywords  = fmt_number(semrush.get("unique_keywords", 0))
    monthly_traffic  = fmt_number(semrush.get("estimated_traffic", 0))
    traffic_value    = fmt_number(semrush.get("traffic_value", 0))
    clinical_tv_raw  = semrush.get("clinical_traffic_value", 0) or 0
    clinical_traffic_value = fmt_number(clinical_tv_raw)
    ai_overview_cnt  = str(semrush.get("ai_overview_serp_count", 0))
    ai_cited_cnt     = str(semrush.get("ai_overview_cited_count", 0))
    quick_wins_count = str(semrush.get("quick_wins_count", 0))

    # ── Run date ─────────────────────────────────────────────────────────────
    run_id   = p1.get("run_id", "")
    run_date = datetime.now().strftime("%B %d, %Y")
    if run_id:
        # Extract date from run_id: slug_YYYYMMDD_HHMMSS
        parts = run_id.rsplit("_", 2)
        if len(parts) >= 2 and len(parts[-2]) == 8:
            try:
                run_date = datetime.strptime(parts[-2], "%Y%m%d").strftime("%B %d, %Y")
            except ValueError:
                pass

    # ── Assessment JSON ──────────────────────────────────────────────────────
    concerns_raw = app_cfg.get("concerns", [])
    if isinstance(concerns_raw, str):
        concerns_raw = [c.strip() for c in concerns_raw.split(",") if c.strip()]
    # Normalize: [{label, emoji}] → flat string labels (what the app template expects)
    if concerns_raw and isinstance(concerns_raw, list) and isinstance(concerns_raw[0], dict):
        concern_labels = [c.get("label", "") for c in concerns_raw if c.get("label")]
    else:
        concern_labels = concerns_raw

    symptom_map = app_cfg.get("symptom_map", {})
    # Ensure symptom_map keys match concern strings
    assessment_concerns_json = json.dumps(concern_labels, ensure_ascii=False)
    assessment_symptoms_json = json.dumps(symptom_map, ensure_ascii=False)

    # ── Favicon URL ──────────────────────────────────────────────────────────
    favicon_url = images.get("favicon_url", "")
    if not favicon_url:
        raw_scrape = p1.get("raw_scrape", "")
        website    = p1.get("website", "https://example.com")
        favicon_url = extract_favicon_url(raw_scrape, website)

    # ── Table rows ────────────────────────────────────────────────────────────
    # Merge top_quick_wins + all quick wins for table
    quick_wins = semrush.get("top_quick_wins", [])
    if not quick_wins and semrush.get("top_by_volume"):
        quick_wins = semrush.get("top_by_volume", [])

    competitors = semrush.get("competitors", [])

    # First real competitor traffic for narrative text
    own_domain = p1.get("website", "")
    real_comps = [c for c in competitors if _is_real_competitor(c.get("domain", ""), own_domain)]
    if real_comps:
        comp1_traffic = fmt_number(real_comps[0].get("traffic", 0))
        comp1_domain  = real_comps[0].get("domain", "a top competitor")
    else:
        # Fall back to showing the market leader from DataForSEO's dataset
        # (Cleveland Clinic / Healthline etc.) with context framing
        non_social = [c for c in competitors if not any(
            c.get("domain","").endswith(b) for b in ["facebook.com","youtube.com","instagram.com","reddit.com"]
        ) and c.get("domain","") != own_domain.replace("https://","").replace("www.","").rstrip("/")]
        if non_social:
            comp1_traffic = fmt_number(non_social[0].get("traffic", 0))
            comp1_domain  = non_social[0].get("domain", "a top search result")
        else:
            comp1_traffic = "thousands of"
            comp1_domain  = "competitors"

    practice_name_raw = p1.get("name", "Your Practice")
    company_slug = make_company_slug(practice_name_raw)

    # ── Build context sentences ───────────────────────────────────────────────
    competitor_context_sentence = build_competitor_context_sentence(semrush, p1)
    ai_seo_callout = build_ai_seo_callout(semrush, p1)

    # ── Competitor type note ──────────────────────────────────────────────────
    comp_list = competitors  # raw list from semrush
    health_system_count = sum(1 for c in comp_list if c.get("competitor_type") == "health_system")
    practice_count = sum(1 for c in comp_list if c.get("competitor_type") == "practice")

    if health_system_count > 0 and practice_count > 0:
        competitor_type_note = (f"Includes {health_system_count} large health system(s) that rank for the same searches — "
                                f"context only, not winnable targets. Focus is on the {practice_count} independent practice(s) above.")
    elif health_system_count > 0:
        competitor_type_note = ("These are large health systems ranking for your specialty searches — "
                                "they signal strong market demand. Independent local practices are your winnable targets.")
    else:
        competitor_type_note = ""

    # ── Location tokens ───────────────────────────────────────────────────────
    primary_city  = p1.get("primary_city", "") or _extract_city(p1)
    primary_state = p1.get("primary_state", "")
    serp_specialty = semrush.get("serp_specialty", "functional medicine")

    return {
        "PRACTICE_NAME":             practice_name_raw,
        "PRACTICE_NAME_ENCODED":     urllib.parse.quote(practice_name_raw, safe=""),
        "COMPANY_SLUG":              company_slug,
        "DOCTOR_NAME":               p1.get("doctor_name", "Your Doctor"),
        "WEBSITE":                   p1.get("website", ""),
        "LOGO_URL":                  images.get("logo_url", ""),
        "BOOKING_URL":               p1.get("booking_url", "#"),
        "FAVICON_URL":               favicon_url,
        "BRAND_PRIMARY":             brand_primary,
        "BRAND_ACCENT":              brand_accent,
        "DOMAIN_RANK":               domain_rank,
        "DOMAIN_RANK_LABEL":         domain_rank_label,
        "UNIQUE_KEYWORDS":           unique_keywords,
        "MONTHLY_TRAFFIC":           monthly_traffic,
        "TRAFFIC_VALUE":             traffic_value,
        "AI_OVERVIEW_COUNT":         ai_overview_cnt,
        "AI_CITED_COUNT":            ai_cited_cnt,
        "QUICK_WINS_COUNT":          quick_wins_count,
        "RUN_DATE":                  run_date,
        "QUICK_WINS_TABLE_ROWS":     build_quick_wins_rows(quick_wins),
        "COMPETITORS_TABLE_ROWS":    build_competitors_rows(competitors, p1.get("website", "")),
        "DATA_NERDS_ROWS":           build_data_nerds_rows(semrush),   # kept for legacy
        "KEYWORD_ROWS_HTML":         build_keyword_rows_html(semrush, p2.get("keywords", [])),
        "AD_CAMPAIGNS_HTML":         build_ad_campaigns_html(p2.get("ads", [])),
        "PATIENT_EMAIL_SEQUENCE_HTML": build_patient_email_html(p2.get("emails", [])),
        "ASSESSMENT_CONCERNS_JSON":  assessment_concerns_json,
        "ASSESSMENT_SYMPTOMS_JSON":  assessment_symptoms_json,
        "LOOM_ID":                   p1.get("loom_id", ""),
        # Hide loom section if no loom_id set — unhide after adding Loom video
        "LOOM_SECTION_STYLE":        '' if p1.get("loom_id", "").strip() else 'style="display:none"',
        "CLARITY_SNIPPET":           _clarity_snippet(os.environ.get("CLARITY_PROJECT_ID", "")),
        "CITY":                      _extract_city(p1),
        "PRIMARY_CITY":              primary_city,
        "PRIMARY_STATE":             primary_state,
        "PRIMARY_CONDITION":         _extract_primary_condition(p1),
        "SERP_SPECIALTY":            serp_specialty.title(),
        "COMPETITOR_CONTEXT_SENTENCE": competitor_context_sentence,
        "AI_SEO_CALLOUT":            ai_seo_callout,
        "IS_MULTI_LOCATION":         "true" if p1.get("is_multi_location") else "false",
        "COMPETITOR_1_TRAFFIC":      comp1_traffic,
        "COMPETITOR_1_DOMAIN":       comp1_domain,
        "CLINICAL_TRAFFIC_VALUE":    clinical_traffic_value,
        "COMPETITOR_TYPE_NOTE":      competitor_type_note,
    }


def inject(run_dir: Path, deploy: bool = False, dry_run: bool = False) -> Path:
    """
    Main inject function.
    Reads data, fills template, writes index.html.
    Optionally deploys to Vercel.
    Returns path to generated index.html.
    """
    print(f"\n📄 D100 Template Injector")
    print(f"   Run dir : {run_dir}")
    print(f"   Template: {TEMPLATE}")

    # Load data
    p1_path = run_dir / "phase1_data.json"
    p2_path = run_dir / "phase2_output.json"

    if not p1_path.exists():
        raise FileNotFoundError(f"phase1_data.json not found: {p1_path}")
    if not p2_path.exists():
        raise FileNotFoundError(f"phase2_output.json not found: {p2_path}")
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE}")

    p1 = json.loads(p1_path.read_text(encoding="utf-8"))
    p2 = json.loads(p2_path.read_text(encoding="utf-8"))

    print(f"   Practice: {p1.get('name', 'Unknown')}")

    # Load template
    template = TEMPLATE.read_text(encoding="utf-8")
    print(f"   Template size: {len(template):,} bytes")

    # Build replacements
    replacements = build_replacements(p1, p2)

    # Verify all placeholders are covered
    found_placeholders = set(re.findall(r"\{\{([A-Z_]+)\}\}", template))
    missing = found_placeholders - set(replacements.keys())
    if missing:
        print(f"   ⚠ Unmapped placeholders: {missing}")

    # Apply replacements
    output = template
    replaced = 0
    for key, val in replacements.items():
        token = "{{" + key + "}}"
        count = output.count(token)
        if count > 0:
            output = output.replace(token, val)
            replaced += count

    print(f"   Replaced: {replaced} tokens across {len(replacements)} keys")

    # Check for any remaining placeholders
    remaining = re.findall(r"\{\{([A-Z_]+)\}\}", output)
    if remaining:
        print(f"   ⚠ Unreplaced placeholders: {set(remaining)}")

    # Write output
    out_path = run_dir / "index.html"
    out_path.write_text(output, encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024
    print(f"   ✓ Wrote index.html ({size_kb:.1f} KB)")

    # Mirror to output/site/{company_slug}/ so path-based deploy works correctly.
    # Use COMPANY_SLUG from replacements (derived from practice name via make_company_slug)
    # NOT from run_dir folder name, which uses domain slug (e.g. alignedmodernhealth-com).
    company_slug = replacements.get("COMPANY_SLUG", "")
    if company_slug:
        site_dir = PROJECT_DIR / "output" / "site"
        slug_dir = site_dir / company_slug
        slug_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(out_path), str(slug_dir / "index.html"))
        print(f"   ✓ Mirrored to output/site/{company_slug}/index.html")

    # Also write as seo_report.html for backward compat
    seo_report_path = run_dir / "seo_report.html"
    seo_report_path.write_text(output, encoding="utf-8")

    # Download favicon
    favicon_url = replacements["FAVICON_URL"]
    favicon_dest = run_dir / "favicon.ico"
    if favicon_url and not favicon_dest.exists():
        print(f"   Downloading favicon: {favicon_url}")
        download_favicon(favicon_url, favicon_dest)

    if deploy and not dry_run:
        from inject_report import deploy_to_vercel
        practice_name = p1.get("name", "Practice")
        deploy_url = deploy_to_vercel(run_dir, practice_name)
        return out_path, deploy_url

    return out_path


# ── Vercel Deploy ─────────────────────────────────────────────────────────────

def make_company_slug(practice_name: str) -> str:
    """
    'Integrated Health of Indiana, Inc.' → 'integrated-health-of-indiana-inc'
    Max 50 chars for Vercel project name (hbs- prefix adds 4).
    """
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", practice_name).strip()
    slug = "-".join(clean.split()).lower()
    return slug[:50].rstrip("-")


def _load_env_var(key: str) -> str:
    """Read a variable from os.environ or .env file."""
    val = os.environ.get(key, "")
    if not val:
        env_path = PROJECT_DIR / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith(f"{key}="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return val


def _sync_site_dir(site_dir: Path) -> None:
    """
    Sync all existing run dirs that have index.html into site_dir/{slug}/.
    This ensures every deploy includes all previously-built reports.
    """
    runs_root = PROJECT_DIR / "output" / "d100_runs"
    if not runs_root.exists():
        return
    for run_dir in sorted(runs_root.iterdir()):
        idx = run_dir / "index.html"
        if not idx.exists():
            continue
        # Derive slug from run_dir name (strip timestamp suffix: slug_YYYYMMDD_HHMMSS)
        parts = run_dir.name.rsplit("_", 2)
        slug = parts[0] if len(parts) == 3 and len(parts[1]) == 8 else run_dir.name
        dest = site_dir / slug
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(idx), str(dest / "index.html"))
        fav = run_dir / "favicon.ico"
        if fav.exists():
            shutil.copy(str(fav), str(dest / "favicon.ico"))


def deploy_to_vercel(run_dir: Path, practice_name: str, dry_run: bool = False) -> str:
    """
    Deploy ALL reports as path-based pages under healthbizleads.com/{slug}/.

    Strategy:
      1. Maintain output/site/ as accumulator — each report in its own subfolder
      2. Sync all existing run dirs into output/site/
      3. Deploy the entire output/site/ dir to healthbizleads-d100 project
      4. Return https://healthbizleads.com/{slug}/

    Returns the live healthbizleads.com URL for this specific report.
    """
    import shutil

    vercel_token       = _load_env_var("VERCEL_TOKEN")
    deliverables_proj  = _load_env_var("VERCEL_DELIVERABLES_PROJECT") or "healthbizleads-d100"
    deliverables_domain = _load_env_var("DELIVERABLES_DOMAIN") or "healthbizleads.com"
    scope              = "kohl-digital"  # Vercel team slug

    if not vercel_token:
        raise RuntimeError("VERCEL_TOKEN not set in environment or .env file")

    slug = make_company_slug(practice_name)
    live_url = f"https://{deliverables_domain}/{slug}/"

    if dry_run:
        print(f"   [DRY RUN] Would deploy to {deliverables_domain}/{slug}/")
        return live_url

    vercel_bin = shutil.which("vercel")
    if not vercel_bin:
        raise RuntimeError("vercel CLI not found. Install with: npm i -g vercel")

    # Build the accumulator site directory
    site_dir = PROJECT_DIR / "output" / "site"
    site_dir.mkdir(parents=True, exist_ok=True)

    # Sync ALL existing reports into site/{slug}/
    _sync_site_dir(site_dir)

    # Write vercel.json into site root
    # cleanUrls + trailingSlash = Vercel auto-serves slug/index.html for slug/
    # No builds/routes override so Vercel auto-detects api/ as serverless functions
    vercel_config = {
        "version": 2,
        "name": deliverables_proj,
        "cleanUrls": True,
        "trailingSlash": True,
    }
    (site_dir / "vercel.json").write_text(json.dumps(vercel_config, indent=2))

    # Always write the latest opened.js (overwrite on every deploy so SmartLead/Slack logic stays current)
    api_dir = site_dir / "api"
    api_dir.mkdir(exist_ok=True)
    api_func = api_dir / "opened.js"
    opened_js = '''\
// D100 report-open tracker: Slack (#d100-opens) + SmartLead subsequence trigger
// Reads: SLACK_D100_OPENS_WEBHOOK, SMARTLEAD_API_KEY from Vercel env
// ?ref=base64(email)  — set by runner at deploy time from CSV emails column
// ?preview=1          — suppresses all notifications (for internal testing)

const SL_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
const SL_BASE = 'https://server.smartlead.ai/api/v1';

async function triggerSmartLead(email, apiKey) {
  // 1. Find lead by email -> get their campaign_id
  const lRes = await fetch(`${SL_BASE}/leads?email=${encodeURIComponent(email)}&api_key=${apiKey}`,
    { headers: { 'User-Agent': SL_UA } });
  if (!lRes.ok) throw new Error(`lead lookup HTTP ${lRes.status}`);
  const lead = await lRes.json();
  const campData = lead.lead_campaign_data;
  if (!campData || !campData.length) throw new Error('lead not found in any campaign');
  const parentId = campData[0].campaign_id;

  // 2. Get all campaigns -> find 'Opened Report' child of that parent
  const cRes = await fetch(`${SL_BASE}/campaigns?api_key=${apiKey}`,
    { headers: { 'User-Agent': SL_UA } });
  if (!cRes.ok) throw new Error(`campaigns HTTP ${cRes.status}`);
  const campaigns = await cRes.json();
  const subseq = campaigns.find(c => c.name === 'Opened Report' && c.parent_campaign_id === parentId);
  if (!subseq) throw new Error(`no 'Opened Report' subsequence for campaign ${parentId}`);

  // 3. Add lead to subsequence (SmartLead dedupes automatically)
  const aRes = await fetch(`${SL_BASE}/campaigns/${subseq.id}/leads?api_key=${apiKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'User-Agent': SL_UA },
    body: JSON.stringify({ lead_list: [{ email }] })
  });
  if (!aRes.ok) throw new Error(`add lead HTTP ${aRes.status}`);
  return subseq.id;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (req.method === 'OPTIONS') return res.status(200).end();

  // Preview mode: suppress everything
  if (req.query.preview === '1') return res.status(200).json({ ok: true, skipped: 'preview' });

  const slug     = (req.query.slug     || 'unknown').replace(/[^a-z0-9-]/gi, '');
  const practice = decodeURIComponent(req.query.practice || slug);
  const ref      = req.query.ref || '';
  const url      = `https://healthbizleads.com/${slug}/`;
  const ts = new Date().toLocaleString('en-US', {
    timeZone: 'America/Denver', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit', hour12: true
  });

  // Decode email from ref token
  let email = '';
  if (ref) {
    try { email = Buffer.from(ref, 'base64').toString('utf8').trim(); } catch(_) {}
  }

  // SmartLead trigger
  const slApiKey = process.env.SMARTLEAD_API_KEY;
  let slStatus = 'skipped';
  if (email && slApiKey) {
    try {
      const subseqId = await triggerSmartLead(email, slApiKey);
      slStatus = `triggered (subseq ${subseqId})`;
    } catch(e) {
      slStatus = `error: ${e.message}`;
    }
  } else if (!email) {
    slStatus = 'no ref token';
  } else if (!slApiKey) {
    slStatus = 'no API key';
  }

  // Slack notification -> #d100-opens
  const webhook = process.env.SLACK_D100_OPENS_WEBHOOK || process.env.SLACK_WEBHOOK_URL;
  if (webhook) {
    const emailNote = email ? `*Email:* ${email}` : '*Email:* unknown (no ?ref token)';
    const slNote    = `*SmartLead:* ${slStatus}`;
    try {
      await fetch(webhook, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: `\ud83d\udc41 *Report Opened* \u2014 ${practice}`,
          blocks: [{ type: 'section', text: { type: 'mrkdwn',
            text: `\ud83d\udc41 *Report Opened*\n*Practice:* ${practice}\n*URL:* <${url}|${url}>\n${emailNote}\n${slNote}\n*Time:* ${ts} MT`
          }}]
        })
      });
    } catch(_) {}
  }

  return res.status(200).json({ ok: true, sl: slStatus });
}
'''  # end opened_js
    api_func.write_text(opened_js, encoding="utf-8")

    # Root index — simple redirect listing (not required, but nice to have)
    root_idx = site_dir / "index.html"
    if not root_idx.exists():
        root_idx.write_text(
            "<html><head><title>HealthBizLeads Reports</title>"
            "<meta http-equiv=\'refresh\' content=\'0;url=https://healthbizleads.com\'/>"
            "</head><body></body></html>"
        )

    print(f"   Deploying site dir to Vercel project: {deliverables_proj}")
    print(f"   Reports synced: {len(list(site_dir.iterdir()))} entries")

    result = subprocess.run(
        [
            vercel_bin,
            "--yes",
            "--prod",
            "--scope", scope,
            "--token", vercel_token,
            "--cwd", str(site_dir),
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Vercel deploy failed:\n{result.stderr}\n{result.stdout}")

    output = result.stdout.strip()
    print(f"   Vercel output:\n{output}")
    print(f"   ✓ Deployed → {live_url}")
    return live_url


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="D100 Template Injector")
    parser.add_argument("run_dir", help="Path to run directory containing phase1_data.json + phase2_output.json")
    parser.add_argument("--deploy-vercel", action="store_true", help="Deploy to Vercel after injection")
    parser.add_argument("--dry-run",       action="store_true", help="Skip actual deployment")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"ERROR: Run directory not found: {run_dir}")
        sys.exit(1)

    try:
        result = inject(run_dir, deploy=args.deploy_vercel, dry_run=args.dry_run)
        if isinstance(result, tuple):
            out_path, deploy_url = result
            print(f"\n✅ Done! index.html → {out_path}")
            print(f"🌐 Live at → {deploy_url}")
        else:
            print(f"\n✅ Done! index.html → {result}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
