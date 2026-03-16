#!/usr/bin/env python3
"""
d100_funnel_builder.py — D100 Funnel Builder Runner v1.0

Given a CSV of prospects (name + website), research each prospect's live site,
extract brand identity, and write prospect_data.json for Claude Code to build
a high-converting landing page. Then deploy each page to GitHub Pages.

Usage:
  # Phase 1: Research all prospects in CSV
  python3 -u scripts/d100_funnel_builder.py --csv prospects.csv

  # Phase 1: Research single prospect (0-indexed)
  python3 -u scripts/d100_funnel_builder.py --csv prospects.csv --site-index 0

  # Phase 3: Deploy (after Claude Code has built index.html)
  python3 -u scripts/d100_funnel_builder.py --csv prospects.csv --deploy-only

CSV Format:
  name,website,notes,assessment_url
  Dr. Aaron Hartman,https://richmondfunctionalmedicine.com,"Focuses on autoimmune.",https://user.github.io/richmond-funnel/

Environment (.env at project root):
  SLACK_WEBHOOK_URL=https://hooks.slack.com/...
  (gh CLI must be authenticated: gh auth login)
"""

import argparse
import concurrent.futures
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# ── Project paths ───────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_ROOT = PROJECT_ROOT / "output" / "funnel_builds"
D100_RUNS_ROOT = PROJECT_ROOT / "output" / "d100_runs"   # shared scrape cache
SKILL_FILE = PROJECT_ROOT / "skills" / "SKILL_D100_funnel_builder.md"

GH_CLI = "/opt/homebrew/bin/gh"


# ── Load .env ───────────────────────────────────────────────────────────────────
def load_env() -> dict:
    env_path = PROJECT_ROOT / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    for k in ("SLACK_WEBHOOK_URL",):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


# ── Slugify ─────────────────────────────────────────────────────────────────────
def slugify(website: str) -> str:
    """Convert URL to a safe filesystem/GitHub slug."""
    s = re.sub(r"https?://", "", website.rstrip("/"))
    s = s.lstrip("www.")
    s = re.sub(r"[^a-zA-Z0-9]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-").lower()
    return s[:40]  # keep repo names sane


# ── Shared scrape cache: reuse D100 runner scrape if it exists ──────────────────
def find_existing_scrape(website: str):
    """
    Check output/d100_runs/ for an existing raw_scrape.md for this domain.
    Returns (scrape_text, source_path) or (None, None) if not found.
    Reuses the most recent run dir that has a raw_scrape.md.
    """
    slug = re.sub(r"https?://", "", website.rstrip("/")).replace("/", "").replace(".", "-")
    if not D100_RUNS_ROOT.exists():
        return None, None
    candidates = sorted(
        [d for d in D100_RUNS_ROOT.iterdir()
         if d.is_dir() and d.name.startswith(slug)
         and (d / "scrape_data" / "raw_scrape.md").exists()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        scrape_path = candidates[0] / "scrape_data" / "raw_scrape.md"
        return scrape_path.read_text(encoding="utf-8"), scrape_path
    return None, None


# ── Phase 1: Page scraper ───────────────────────────────────────────────────────
def scrape_page(url: str, timeout: int = 8) -> str:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", errors="ignore")
        # Strip scripts, styles, tags
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3500]
    except Exception as e:
        return f"ERROR scraping {url}: {e}"


def scrape_site(website: str) -> str:
    """Scrape 12 pages in parallel. Expanded set vs D100 runner for funnel research."""
    base = website.rstrip("/")
    slugs = [
        "", "/about/", "/services/", "/team/", "/new-patients/",
        "/functional-medicine/", "/weight-loss/", "/hormone/", "/contact/",
        "/testimonials/", "/programs/", "/work-with-me/", "/pricing/",
    ]
    urls = [base + slug for slug in slugs]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        results = list(ex.map(scrape_page, urls))
    sections = [f"## PAGE: {url}\n\n{text}" for url, text in zip(urls, results)]
    return "\n\n---\n\n".join(sections)


# ── Phase 1: Brand color extraction ────────────────────────────────────────────
def extract_brand_colors_css(website: str) -> dict:
    """Extract brand colors via CSS parsing (same algorithm as D100 v3 runner)."""
    try:
        req = urllib.request.Request(website, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return {"note": f"CSS extraction failed: {e}", "background": "#FFFFFF",
                "source": "css_extraction_failed"}

    # 1. Elementor global CSS custom properties
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

    # 2. Frequency-count all 6-digit hex colors (exclude near-black/near-white)
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


# ── Phase 1: Booking URL extraction ────────────────────────────────────────────
def extract_booking_url(markdown: str, base_url: str) -> str:
    """Scan scraped text for booking/scheduling links."""
    base = base_url.rstrip("/")
    text_kw = re.compile(
        r"book|schedul|appointment|new.patient|portal|consult|intake|request.appoint",
        re.I
    )
    url_kw = re.compile(
        r"/book|/schedul|/appointment|/new.patient|/portal|/consult|/intake",
        re.I
    )
    for text, url in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", markdown):
        if text_kw.search(text) or url_kw.search(url):
            url = url.strip()
            if url.startswith("http"):
                return url
            if url.startswith("/"):
                return base + url
    for url in re.findall(r"https?://\S+", markdown):
        if url_kw.search(url):
            return url.rstrip(")")
    return ""


# ── Phase 1: robots/sitemap crawlability check ─────────────────────────────────
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

    def fetch_sitemap():
        try:
            with urllib.request.urlopen(f"https://{domain}/sitemap.xml", timeout=5) as r:
                sitemap = r.read().decode("utf-8", errors="ignore")
                results["sitemap_urls"] = len(re.findall(r"<loc>", sitemap))
        except Exception:
            results["sitemap_urls"] = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(fetch_robots), ex.submit(fetch_sitemap)]
        concurrent.futures.wait(futs)
    return results


# ── Phase 1 NEW: Image extraction ───────────────────────────────────────────────
def extract_images(website: str) -> dict:
    """
    Fetch homepage HTML and pull candidate images:
    - og:image → likely the best hero/headshot
    - logo candidates: near 'logo' class/alt/src, or first img near h1
    - hero candidates: large img tags in header/hero sections
    Returns {logo_url, hero_url, headshot_url} — all may be empty strings.
    """
    images = {"logo_url": "", "hero_url": "", "headshot_url": ""}
    try:
        req = urllib.request.Request(website, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return images

    base = website.rstrip("/")

    def make_absolute(src: str) -> str:
        if not src:
            return ""
        if src.startswith("http"):
            return src
        if src.startswith("//"):
            return "https:" + src
        if src.startswith("/"):
            # Extract domain
            m = re.match(r"(https?://[^/]+)", base)
            return (m.group(1) if m else base) + src
        return base + "/" + src

    # 1. og:image (best single candidate)
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.I)
    if m:
        images["hero_url"] = make_absolute(m.group(1))

    # 2. Logo: look for <img> tags with logo in class, alt, src, or id
    logo_pattern = re.compile(
        r'<img[^>]+(class|alt|src|id)=["\'][^"\']*logo[^"\']*["\'][^>]*>',
        re.I
    )
    for tag in logo_pattern.findall(html)[:3]:
        # tag is just the attribute name match — get the full tag
        pass
    # Better: find full img tags and check for logo
    img_tags = re.findall(r'<img[^>]+>', html, re.I)
    for tag in img_tags:
        src_m = re.search(r'src=["\']([^"\']+)["\']', tag, re.I)
        if not src_m:
            continue
        src = src_m.group(1)
        combined = tag.lower()
        if "logo" in combined and not images["logo_url"]:
            images["logo_url"] = make_absolute(src)
            break

    # 3. Headshot: look for img near words like 'dr', 'doctor', 'founder', 'provider', 'headshot', 'portrait'
    headshot_kw = re.compile(r'headshot|portrait|founder|provider|physician|dr[\-_\s]', re.I)
    for tag in img_tags:
        src_m = re.search(r'src=["\']([^"\']+)["\']', tag, re.I)
        if not src_m:
            continue
        combined = tag + src_m.group(1)
        if headshot_kw.search(combined) and not images["headshot_url"]:
            images["headshot_url"] = make_absolute(src_m.group(1))
            break

    # Fallback: if no headshot found but we have og:image and no hero already, use og:image as headshot too
    # (og:image is often the provider's photo on functional medicine sites)

    return images


# ── Phase 1 NEW: Public presence / social links ─────────────────────────────────
def scrape_public_presence(name: str, website: str) -> dict:
    """
    DuckDuckGo HTML search (urllib, no API key) to find:
    - Instagram, LinkedIn, YouTube profile URLs
    - Media / podcast mentions
    Returns {instagram, linkedin, youtube, media_mentions[]}
    """
    presence = {
        "instagram": "",
        "linkedin": "",
        "youtube": "",
        "media_mentions": [],
    }
    domain = re.sub(r"https?://", "", website).rstrip("/").lstrip("www.")
    query = f'"{name}" site:instagram.com OR site:linkedin.com OR site:youtube.com OR podcast OR interview'
    encoded = urllib.parse.quote_plus(query)

    try:
        req = urllib.request.Request(
            f"https://html.duckduckgo.com/html/?q={encoded}",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return presence

    # Extract all result URLs from DDG HTML
    result_urls = re.findall(r'href="(https?://[^"]+)"', html)

    for url in result_urls:
        url_lower = url.lower()
        if "instagram.com" in url_lower and "/" in url_lower.replace("instagram.com", "") and not presence["instagram"]:
            presence["instagram"] = url
        elif "linkedin.com/in/" in url_lower and not presence["linkedin"]:
            presence["linkedin"] = url
        elif ("youtube.com/@" in url_lower or "youtube.com/channel/" in url_lower or
              "youtube.com/user/" in url_lower) and not presence["youtube"]:
            presence["youtube"] = url
        elif any(kw in url_lower for kw in ["podcast", "interview", "episode", "show"]):
            # Exclude their own site and social platforms
            if (domain not in url_lower and
                "instagram.com" not in url_lower and
                "linkedin.com" not in url_lower and
                "youtube.com" not in url_lower and
                len(presence["media_mentions"]) < 5):
                presence["media_mentions"].append(url)

    return presence


# ── Phase 1 NEW: Testimonial extraction ─────────────────────────────────────────
def extract_testimonials(raw_scrape: str) -> list:
    """
    Pull testimonial/quote blocks from scraped text.
    Heuristics: quoted blocks, words before star ratings, short paragraphs near names.
    Returns list of raw strings (max 10). Empty list if none found.
    Never fabricates — returns empty if nothing credible found.
    """
    testimonials = []
    seen = set()

    # 1. Quoted text patterns: "..." or '...' that are 30-300 chars
    for m in re.finditer(r'["\u201c\u2018\u276e]([\w\s][^"\u201d\u2019\u276f]{30,300})["\u201d\u2019\u276f]', raw_scrape):
        text = m.group(1).strip()
        normalized = re.sub(r'\s+', ' ', text)
        if normalized not in seen and len(normalized) > 30:
            testimonials.append(normalized)
            seen.add(normalized)
            if len(testimonials) >= 10:
                break

    # 2. Patterns like "★★★★★ Some text" or "5/5 text"
    for m in re.finditer(r'(?:★{3,5}|5\/5|\*{3,5})\s*([A-Z][^.!?]{20,200}[.!?])', raw_scrape):
        text = m.group(1).strip()
        normalized = re.sub(r'\s+', ' ', text)
        if normalized not in seen:
            testimonials.append(normalized)
            seen.add(normalized)
            if len(testimonials) >= 10:
                break

    # 3. Short paragraph blocks that look like patient testimonials (contain "I" + health words)
    health_kw = re.compile(r'\b(doctor|practice|treatment|health|symptoms|condition|pain|feel|better|helped|recommend|changed)\b', re.I)
    first_person = re.compile(r'\bI\s+(was|have|had|felt|feel|noticed|saw|went|tried|couldn\'t|can\'t|am)\b', re.I)
    for sentence in re.findall(r'([A-Z][^.!?]{30,250}[.!?])', raw_scrape):
        normalized = re.sub(r'\s+', ' ', sentence.strip())
        if (first_person.search(normalized) and
                health_kw.search(normalized) and
                normalized not in seen and
                len(testimonials) < 10):
            testimonials.append(normalized)
            seen.add(normalized)

    return testimonials[:10]


# ── Phase 1: Research single prospect ──────────────────────────────────────────
def research_prospect(row: dict, run_dir: Path) -> dict:
    """
    Phase 1: Scrape all data for one prospect. Returns prospect_data dict.
    """
    name = row.get("name", "").strip()
    website = row.get("website", "").rstrip("/")
    notes = row.get("notes", "").strip()
    assessment_url = row.get("assessment_url", "").strip()

    slug = slugify(website)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{slug}_{ts}"

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "scrape_data").mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"🔍 Funnel Builder — {name}")
    print(f"   Website: {website}")
    print(f"   Run dir: {run_dir}")
    print(f"{'='*60}")

    # ── Parallel data collection ────────────────────────────────────────────────
    t0 = time.time()

    print("\n📡 Phase 1: Collecting prospect data (parallel)...")

    # Check if D100 runner already scraped this site — reuse master scrape, don't hit server twice
    cached_scrape, cached_path = find_existing_scrape(website)
    if cached_scrape:
        print(f"  ♻️  Reusing D100 master scrape ({len(cached_scrape):,} chars) ← {cached_path}")
        raw_scrape = cached_scrape
        # Fire remaining jobs in parallel (skip scrape)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            fut_colors   = ex.submit(extract_brand_colors_css, website)
            fut_images   = ex.submit(extract_images, website)
            fut_presence = ex.submit(scrape_public_presence, name, website)
            fut_crawl    = ex.submit(check_crawlability, website)
            brand_colors = fut_colors.result()
            images       = fut_images.result()
            presence     = fut_presence.result()
            crawl        = fut_crawl.result()
    else:
        # No existing scrape — fire everything including fresh scrape
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            fut_scrape    = ex.submit(scrape_site, website)
            fut_colors    = ex.submit(extract_brand_colors_css, website)
            fut_images    = ex.submit(extract_images, website)
            fut_presence  = ex.submit(scrape_public_presence, name, website)
            fut_crawl     = ex.submit(check_crawlability, website)
            raw_scrape   = fut_scrape.result()
            brand_colors = fut_colors.result()
            images       = fut_images.result()
            presence     = fut_presence.result()
            crawl        = fut_crawl.result()

    # Booking URL (needs scrape result first)
    booking_url = extract_booking_url(raw_scrape, website)

    # Testimonials (needs scrape result first)
    testimonials = extract_testimonials(raw_scrape)

    elapsed = time.time() - t0
    print(f"  ✓ Scraped {len(raw_scrape):,} chars ({elapsed:.1f}s)")
    print(f"  ✓ Brand colors: {brand_colors.get('source', 'unknown')} → {list(brand_colors.items())[:3]}")
    print(f"  ✓ Images: logo={bool(images['logo_url'])} hero={bool(images['hero_url'])} headshot={bool(images['headshot_url'])}")
    print(f"  ✓ Social: instagram={bool(presence['instagram'])} linkedin={bool(presence['linkedin'])} mentions={len(presence['media_mentions'])}")
    print(f"  ✓ Testimonials found: {len(testimonials)}")
    print(f"  ✓ Booking URL: {booking_url or '(not found — placeholder will be used)'}")
    print(f"  ✓ Crawlability: {crawl.get('ai_status', 'unknown')} | sitemap: {crawl.get('sitemap_urls', 0)} URLs")

    # Write raw scrape
    scrape_path = run_dir / "scrape_data" / "raw_scrape.md"
    scrape_path.write_text(raw_scrape, encoding="utf-8")

    # Build prospect_data.json
    prospect_data = {
        "name": name,
        "website": website,
        "notes": notes,
        "assessment_url": assessment_url,
        "run_id": run_id,
        "raw_scrape": raw_scrape[:8000],
        "brand_colors": brand_colors,
        "images": images,
        "booking_url": booking_url,
        "testimonials": testimonials,
        "public_presence": presence,
        "crawl": crawl,
    }

    out_path = run_dir / "prospect_data.json"
    out_path.write_text(json.dumps(prospect_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  ✅ prospect_data.json written → {out_path}")
    print(f"  ➡️  Next: Claude Code reads prospect_data.json + SKILL_D100_funnel_builder.md → writes index.html")

    return prospect_data


# ── Phase 3: Deploy to GitHub Pages ────────────────────────────────────────────
def deploy_to_github(run_dir: Path, name: str, slug: str) -> str:
    """
    Create a public GitHub repo, push index.html, enable GitHub Pages.
    Returns the live GitHub Pages URL.
    """
    repo_name = f"{slug}-funnel"

    print(f"\n🚀 Deploying to GitHub Pages...")
    print(f"   Repo: {repo_name}")

    # 1. Get GitHub username
    try:
        username = subprocess.check_output(
            [GH_CLI, "api", "user", "--jq", ".login"],
            stderr=subprocess.PIPE
        ).decode().strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"gh CLI failed — run 'gh auth login' first: {e.stderr.decode()}")

    print(f"   GitHub user: {username}")

    # 2. Check if repo already exists
    check = subprocess.run(
        [GH_CLI, "repo", "view", f"{username}/{repo_name}"],
        capture_output=True
    )
    repo_exists = check.returncode == 0

    if not repo_exists:
        # Create public repo
        subprocess.run([
            GH_CLI, "repo", "create", repo_name,
            "--public",
            "--description", f"Demo landing page — {name}",
        ], check=True)
        print(f"   ✓ Repo created: github.com/{username}/{repo_name}")
    else:
        print(f"   ℹ️  Repo already exists: github.com/{username}/{repo_name}")

    # 3. Clone → copy index.html → push
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        clone_url = f"https://github.com/{username}/{repo_name}.git"

        subprocess.run(
            ["git", "clone", clone_url, str(tmp_path / "repo")],
            check=True,
            capture_output=True,
        )
        repo_local = tmp_path / "repo"

        # Copy index.html
        shutil.copy(run_dir / "index.html", repo_local / "index.html")

        # Stage, commit, push
        subprocess.run(["git", "-C", str(repo_local), "add", "index.html"], check=True)
        subprocess.run([
            "git", "-C", str(repo_local), "commit",
            "-m", f"Add demo landing page for {name}"
        ], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo_local), "push"], check=True, capture_output=True)

    print(f"   ✓ index.html pushed")

    # 4. Enable GitHub Pages (may already be enabled on re-deploy)
    try:
        subprocess.run([
            GH_CLI, "api", f"repos/{username}/{repo_name}/pages",
            "--method", "POST",
            "--field", "source[branch]=main",
            "--field", "source[path]=/",
        ], check=True, capture_output=True)
        print(f"   ✓ GitHub Pages enabled")
    except subprocess.CalledProcessError:
        # Pages already enabled or branch not ready yet — not fatal
        print(f"   ℹ️  GitHub Pages already enabled (or pending)")

    pages_url = f"https://{username}.github.io/{repo_name}/"
    print(f"   ✅ Live URL (ready in ~1-2 min): {pages_url}")
    return pages_url


# ── Phase 3: Slack notification ─────────────────────────────────────────────────
def notify_slack_funnel(webhook: str, name: str, website: str,
                         pages_url: str, repo_url: str) -> bool:
    msg = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text",
                "text": f"🚀 Demo Live — {name}"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Website:*\n{website}"},
                {"type": "mrkdwn", "text": f"*Live Demo:*\n{pages_url}"},
                {"type": "mrkdwn", "text": f"*GitHub Repo:*\n{repo_url}"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn",
                "text": "GitHub Pages takes ~1-2 minutes to go live after deploy."}},
        ],
    }
    req = urllib.request.Request(
        webhook,
        data=json.dumps(msg).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"  ⚠️  Slack notify failed: {e}")
        return False


# ── Find existing run dir for a prospect ───────────────────────────────────────
def find_run_dir_for_prospect(website: str):
    """Find the most recent run dir for a website that has index.html ready."""
    slug = slugify(website)
    if not OUTPUT_ROOT.exists():
        return None
    candidates = sorted(
        [d for d in OUTPUT_ROOT.iterdir()
         if d.is_dir() and d.name.startswith(slug) and (d / "index.html").exists()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def find_prospect_data_dir(website: str):
    """Find the most recent run dir for a website that has prospect_data.json."""
    slug = slugify(website)
    if not OUTPUT_ROOT.exists():
        return None
    candidates = sorted(
        [d for d in OUTPUT_ROOT.iterdir()
         if d.is_dir() and d.name.startswith(slug) and (d / "prospect_data.json").exists()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


# ── CSV helpers ─────────────────────────────────────────────────────────────────
def load_csv(csv_path: str) -> list:
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def update_csv_with_url(csv_path: str, website: str, pages_url: str, repo_url: str):
    """Add/update github_pages_url and github_repo_url columns in CSV."""
    rows = load_csv(csv_path)
    updated = []
    for row in rows:
        if row.get("website", "").rstrip("/") == website.rstrip("/"):
            row["github_pages_url"] = pages_url
            row["github_repo_url"] = repo_url
        updated.append(row)

    # Write back
    fieldnames = list(rows[0].keys()) if rows else []
    if "github_pages_url" not in fieldnames:
        fieldnames.append("github_pages_url")
    if "github_repo_url" not in fieldnames:
        fieldnames.append("github_repo_url")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated)

    print(f"  ✓ CSV updated with live URL: {csv_path}")


# ── Main entry point ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="D100 Funnel Builder v1.0 — Research prospects + deploy landing pages",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--csv", required=True,
        help="CSV file path (columns: name,website,notes,assessment_url)")
    parser.add_argument("--site-index", type=int, default=None,
        help="Run only this row index (0-based) for single-prospect mode")
    parser.add_argument("--deploy-only", action="store_true",
        help="Skip Phase 1 research; deploy existing index.html files to GitHub Pages")
    args = parser.parse_args()

    env = load_env()
    csv_path = args.csv
    rows = load_csv(csv_path)

    if args.site_index is not None:
        if args.site_index >= len(rows):
            print(f"ERROR: --site-index {args.site_index} out of range (CSV has {len(rows)} rows)")
            sys.exit(1)
        rows = [rows[args.site_index]]

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    slack_webhook = env.get("SLACK_WEBHOOK_URL", "")

    print(f"\n{'='*60}")
    print(f"D100 Funnel Builder v1.0")
    print(f"CSV: {csv_path} ({len(rows)} prospects)")
    print(f"Mode: {'Deploy Only' if args.deploy_only else 'Phase 1 Research'}")
    print(f"Slack: {'configured' if slack_webhook else 'NOT configured'}")
    print(f"{'='*60}\n")

    if args.deploy_only:
        # ── DEPLOY MODE ──────────────────────────────────────────────────────────
        deployed = 0
        failed = 0
        for row in rows:
            name = row.get("name", "").strip()
            website = row.get("website", "").rstrip("/")
            slug = slugify(website)

            run_dir = find_run_dir_for_prospect(website)
            if not run_dir:
                print(f"\n⚠️  No index.html found for {name} ({website})")
                print(f"   Expected in: {OUTPUT_ROOT}/{slug}_*/index.html")
                print(f"   → Run Phase 1 first, then have Claude Code build index.html")
                failed += 1
                continue

            # Load prospect_data for name/slug
            data_file = run_dir / "prospect_data.json"
            if data_file.exists():
                prospect_data = json.loads(data_file.read_text(encoding="utf-8"))
                display_name = prospect_data.get("name", name)
            else:
                display_name = name

            try:
                pages_url = deploy_to_github(run_dir, display_name, slug)

                # Get username for repo URL
                username = subprocess.check_output(
                    [GH_CLI, "api", "user", "--jq", ".login"],
                    stderr=subprocess.PIPE
                ).decode().strip()
                repo_url = f"https://github.com/{username}/{slug}-funnel"

                # Update prospect_data.json with live URL
                if data_file.exists():
                    prospect_data = json.loads(data_file.read_text(encoding="utf-8"))
                    prospect_data["github_pages_url"] = pages_url
                    prospect_data["github_repo_url"] = repo_url
                    data_file.write_text(json.dumps(prospect_data, indent=2, ensure_ascii=False), encoding="utf-8")

                # Update CSV
                update_csv_with_url(csv_path, website, pages_url, repo_url)

                # Slack
                if slack_webhook:
                    ok = notify_slack_funnel(slack_webhook, display_name, website, pages_url, repo_url)
                    print(f"  {'✓' if ok else '⚠️'} Slack: {'sent' if ok else 'failed'}")

                deployed += 1

            except Exception as e:
                print(f"\n  ❌ Deploy failed for {name}: {e}")
                failed += 1

        print(f"\n{'='*60}")
        print(f"DEPLOY COMPLETE: {deployed} deployed, {failed} failed")
        print(f"{'='*60}")

    else:
        # ── RESEARCH MODE (Phase 1) ───────────────────────────────────────────────
        results = []
        for i, row in enumerate(rows):
            name = row.get("name", f"Prospect {i}")
            website = row.get("website", "").rstrip("/")

            if not website:
                print(f"\n⚠️  Skipping row {i} — no website URL")
                continue

            slug = slugify(website)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir = OUTPUT_ROOT / f"{slug}_{ts}"

            try:
                prospect_data = research_prospect(row, run_dir)
                results.append({
                    "name": name,
                    "website": website,
                    "run_dir": str(run_dir),
                    "status": "research_complete",
                })
            except Exception as e:
                print(f"\n  ❌ Research failed for {name}: {e}")
                results.append({
                    "name": name,
                    "website": website,
                    "run_dir": str(run_dir),
                    "status": f"error: {e}",
                })

        print(f"\n{'='*60}")
        print(f"PHASE 1 COMPLETE — {len(results)} prospects researched")
        print(f"{'='*60}")
        print(f"\n📋 Next Steps:")
        print(f"   1. Claude Code reads each run dir's prospect_data.json")
        print(f"   2. Claude Code reads: {SKILL_FILE}")
        print(f"   3. Claude Code writes index.html to each run dir")
        print(f"   4. Run: python3 -u scripts/d100_funnel_builder.py --csv {csv_path} --deploy-only")
        print()

        # Print run dirs for easy reference
        for r in results:
            status_icon = "✅" if r["status"] == "research_complete" else "❌"
            print(f"  {status_icon} {r['name']} → {r['run_dir']}")

        print()


if __name__ == "__main__":
    main()
