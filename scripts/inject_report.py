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
    """Format domain rank: 4561840 → '#4,561,840'"""
    try:
        return f"#{int(n):,}"
    except (TypeError, ValueError):
        return "N/A"


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


def build_competitors_rows(competitors: list) -> str:
    """Build <tr> rows for Competitors table."""
    if not competitors:
        return '<tr><td colspan="4" style="padding:20px;color:#94a3b8;text-align:center;">No competitor data available.</td></tr>'

    rows = []
    for comp in competitors:
        domain  = escape_html(comp.get("domain", ""))
        kws     = fmt_number(comp.get("keywords", 0))
        traffic = fmt_number(comp.get("traffic", 0))
        tv      = comp.get("traffic_value", 0)
        tv_fmt  = f"${fmt_number(tv)}" if tv else "$0"
        rows.append(f"""<tr style="border-bottom:1px solid rgba(255,255,255,0.06);">
              <td style="padding:14px 16px;color:#f0f4ff;font-family:monospace;">{domain}</td>
              <td style="padding:14px 16px;color:#84bdbb;font-weight:700;">{kws}</td>
              <td style="padding:14px 16px;color:#f0f4ff;">{traffic}/mo</td>
              <td style="padding:14px 16px;color:#f0f4ff;">{tv_fmt}/mo</td>
            </tr>""")
    return "\n".join(rows)


def build_data_nerds_rows(semrush: dict) -> str:
    """Build full data breakdown table rows."""
    rows_data = [
        ("Domain Rank",             fmt_domain_rank(semrush.get("domain_rank"))),
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
    domain_rank      = fmt_domain_rank(semrush.get("domain_rank"))
    unique_keywords  = fmt_number(semrush.get("unique_keywords", 0))
    monthly_traffic  = fmt_number(semrush.get("estimated_traffic", 0))
    traffic_value    = fmt_number(semrush.get("traffic_value", 0))
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

    practice_name_raw = p1.get("name", "Your Practice")
    company_slug = make_company_slug(practice_name_raw)

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
        "UNIQUE_KEYWORDS":           unique_keywords,
        "MONTHLY_TRAFFIC":           monthly_traffic,
        "TRAFFIC_VALUE":             traffic_value,
        "AI_OVERVIEW_COUNT":         ai_overview_cnt,
        "AI_CITED_COUNT":            ai_cited_cnt,
        "QUICK_WINS_COUNT":          quick_wins_count,
        "RUN_DATE":                  run_date,
        "QUICK_WINS_TABLE_ROWS":     build_quick_wins_rows(quick_wins),
        "COMPETITORS_TABLE_ROWS":    build_competitors_rows(competitors),
        "DATA_NERDS_ROWS":           build_data_nerds_rows(semrush),   # kept for legacy
        "KEYWORD_ROWS_HTML":         build_keyword_rows_html(semrush, p2.get("keywords", [])),
        "AD_CAMPAIGNS_HTML":         build_ad_campaigns_html(p2.get("ads", [])),
        "PATIENT_EMAIL_SEQUENCE_HTML": build_patient_email_html(p2.get("emails", [])),
        "ASSESSMENT_CONCERNS_JSON":  assessment_concerns_json,
        "ASSESSMENT_SYMPTOMS_JSON":  assessment_symptoms_json,
        "LOOM_ID":                   p1.get("loom_id", "PASTE_LOOM_ID_HERE"),
        "CLARITY_SNIPPET":           _clarity_snippet(os.environ.get("CLARITY_PROJECT_ID", "")),
        "CITY":                      _extract_city(p1),
        "PRIMARY_CONDITION":         _extract_primary_condition(p1),
        "IS_MULTI_LOCATION":         "true" if p1.get("is_multi_location") else "false",
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


def deploy_to_vercel(run_dir: Path, practice_name: str, dry_run: bool = False) -> str:
    """
    Deploy index.html (+ favicon) to Vercel.
    Project name: hbs-{company-slug}
    Returns live URL.
    """
    import shutil

    vercel_token = os.environ.get("VERCEL_TOKEN", "")
    if not vercel_token:
        # Try loading from .env
        env_path = PROJECT_DIR / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("VERCEL_TOKEN="):
                    vercel_token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not vercel_token:
        raise RuntimeError("VERCEL_TOKEN not set in environment or .env file")

    slug = make_company_slug(practice_name)
    project_name = f"hbs-{slug}"

    index_path   = run_dir / "index.html"
    favicon_path = run_dir / "favicon.ico"

    if not index_path.exists():
        raise FileNotFoundError(f"index.html not found in {run_dir}")

    if dry_run:
        print(f"   [DRY RUN] Would deploy to Vercel project: {project_name}")
        return f"https://{project_name}.vercel.app"

    # Create temp deploy directory with required Vercel structure
    with tempfile.TemporaryDirectory() as tmpdir:
        deploy_dir = Path(tmpdir) / "deploy"
        deploy_dir.mkdir()

        # Copy files
        shutil.copy(str(index_path), str(deploy_dir / "index.html"))
        if favicon_path.exists():
            shutil.copy(str(favicon_path), str(deploy_dir / "favicon.ico"))

        # Write vercel.json to prevent build step (static deploy)
        # Project name set here — --name flag deprecated in newer Vercel CLI
        vercel_config = {
            "version": 2,
            "name": project_name,
            "builds": [{"src": "**/*", "use": "@vercel/static"}],
            "routes": [{"src": "/(.*)", "dest": "/$1"}]
        }
        (deploy_dir / "vercel.json").write_text(json.dumps(vercel_config, indent=2))

        print(f"   Deploying to Vercel project: {project_name}")

        # Check if vercel CLI is available
        vercel_bin = shutil.which("vercel")
        if not vercel_bin:
            raise RuntimeError("vercel CLI not found. Install with: npm i -g vercel")

        result = subprocess.run(
            [
                vercel_bin,
                "--yes",
                "--prod",
                "--scope", "kohl-digital",
                "--token", vercel_token,
                "--cwd", str(deploy_dir),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Vercel deploy failed:\n{result.stderr}\n{result.stdout}")

        # Extract URL from output
        output = result.stdout.strip()
        print(f"   Vercel output:\n{output}")

        # Find production URL (last line with https://)
        live_url = ""
        for line in reversed(output.splitlines()):
            line = line.strip()
            if line.startswith("https://") and ".vercel.app" in line:
                live_url = line
                break

        if not live_url:
            live_url = f"https://{project_name}.vercel.app"

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
