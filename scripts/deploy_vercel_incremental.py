#!/usr/bin/env python3
"""
D100 Vercel Incremental Deployer
=================================
Deploys company pages to two Vercel projects:
  - healthbizleads.com/[slug]/       (deliverables page)
  - app.healthbizleads.com/[slug]/   (standalone health assessment)

Architecture: Single project per domain, all companies as subfolders.
Each new company = copy index.html into vercel-dist/[slug]/ and run vercel --prod.
Vercel diffs by content hash, so only changed/new files are uploaded.

Scale: Handles 500–1000 companies/month with no project-count limits.
"""

import os
import sys
import json
import shutil
import hashlib
import base64
import subprocess
import urllib.parse
import urllib.request
import time
from pathlib import Path


# ── Brand-adaptive theme color computation ──────────────────────────────────────
def _brightness(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r * 299 + g * 587 + b * 114) / 1000


def _tint(hex_color: str, amount: float) -> str:
    """Mix brand color toward white by amount (0=original, 1=white)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = min(255, int(r + (255 - r) * amount))
    g = min(255, int(g + (255 - g) * amount))
    b = min(255, int(b + (255 - b) * amount))
    return f"#{r:02X}{g:02X}{b:02X}"


def _shade(hex_color: str, amount: float) -> str:
    """Mix brand color toward black by amount (0=original, 1=black)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = max(0, int(r * (1 - amount)))
    g = max(0, int(g * (1 - amount)))
    b = max(0, int(b * (1 - amount)))
    return f"#{r:02X}{g:02X}{b:02X}"


def _hex_to_rgb_str(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"


def _compute_app_theme(brand_primary: str, bg_color: str) -> dict:
    """
    Compute full app theme palette from brand primary + background color.
    Light brands (white bg) → light theme; dark brands → dark theme.
    Both feel distinctly on-brand.
    """
    bg_bright = _brightness(bg_color or "#FFFFFF")
    brand_rgb  = _hex_to_rgb_str(brand_primary)

    if bg_bright > 160:
        # ── LIGHT THEME (e.g. Sacramento green on white) ──────────────────────
        dark_text = _shade(brand_primary, 0.80)  # very dark brand-tinted text
        return {
            "APP_BG":          _tint(brand_primary, 0.96),   # near-white with brand tint
            "APP_S1":          _tint(brand_primary, 0.90),
            "APP_S2":          _tint(brand_primary, 0.82),
            "APP_S3":          _tint(brand_primary, 0.70),
            "APP_BORDER":      f"rgba({brand_rgb},0.15)",
            "APP_BORDER2":     f"rgba({brand_rgb},0.30)",
            "APP_TEXT":        dark_text,
            "APP_MUTED":       _shade(brand_primary, 0.50),
            "APP_MUTED2":      _shade(brand_primary, 0.35),
            "APP_NAV_BG":      f"rgba({brand_rgb},0.97)",    # solid brand-color nav
            # On light bg, 'bright' text must be dark (not white) for contrast
            "APP_TEXT_BRIGHT": dark_text,
        }
    else:
        # ── DARK THEME (e.g. navy/black brands) ───────────────────────────────
        return {
            "APP_BG":          _shade(brand_primary, 0.92),
            "APP_S1":          _shade(brand_primary, 0.87),
            "APP_S2":          _shade(brand_primary, 0.82),
            "APP_S3":          _shade(brand_primary, 0.72),
            "APP_BORDER":      f"rgba({brand_rgb},0.12)",
            "APP_BORDER2":     f"rgba({brand_rgb},0.22)",
            "APP_TEXT":        _tint(brand_primary, 0.88),   # near-white text
            "APP_MUTED":       _tint(brand_primary, 0.40),
            "APP_MUTED2":      _tint(brand_primary, 0.55),
            "APP_NAV_BG":      f"rgba({_hex_to_rgb_str(_shade(brand_primary, 0.95))},0.94)",
            # On dark bg, 'bright' text stays white
            "APP_TEXT_BRIGHT": "#ffffff",
        }

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT       = Path(__file__).parent.parent
VERCEL_DIST     = REPO_ROOT / "vercel-dist"
APP_DIST        = REPO_ROOT / "app-dist"
TEMPLATES_DIR   = REPO_ROOT / "templates"
ENV_FILE        = REPO_ROOT / ".env"

# ── Load env ───────────────────────────────────────────────────────────────────
def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def run_cmd(cmd: str, cwd=None) -> str:
    """Run a shell command and return stdout. Raises on non-zero exit."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr.strip()}")
    return result.stdout.strip()


# ── Vercel REST API deploy (no CLI required) ───────────────────────────────────
def _vercel_api_deploy(
    dist_dir: Path,
    project_id: str,
    team_id: str,
    token: str,
    project_name: str,
) -> str:
    """
    Deploy all files in dist_dir to a Vercel project via REST API.
    Uses Vercel Deployment API v13. Returns the deployment URL.
    Handles file upload, waits for READY state.
    """
    headers_auth = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    team_param = f"?teamId={team_id}"

    # 1. Collect all files and compute SHA1 hashes
    files_meta = []
    for fpath in sorted(dist_dir.rglob("*")):
        if not fpath.is_file():
            continue
        # Skip hidden dirs (except .vercel which Vercel uses)
        rel = fpath.relative_to(dist_dir)
        parts = rel.parts
        if any(p.startswith(".") and p != ".vercel" for p in parts):
            continue
        content = fpath.read_bytes()
        sha1 = hashlib.sha1(content).hexdigest()
        files_meta.append({
            "file":    str(rel).replace("\\", "/"),
            "sha":     sha1,
            "size":    len(content),
            "_content": content,
        })

    # 2. Create deployment
    # Note: projectId is set via .vercel/project.json in dist_dir — NOT in payload
    deploy_payload = {
        "name":   project_name,
        "target": "production",
        "files": [
            {"file": f["file"], "sha": f["sha"], "size": f["size"]}
            for f in files_meta
        ],
        "projectSettings": {
            "framework": None,
        },
    }

    def _post_deployment(payload: dict) -> dict:
        """POST to /v13/deployments. Handles both 200 and 400/missing_files."""
        req = urllib.request.Request(
            f"https://api.vercel.com/v13/deployments{team_param}",
            data=json.dumps(payload).encode(),
            headers=headers_auth,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read()), None
        except urllib.error.HTTPError as e:
            body = json.loads(e.read())
            err  = body.get("error", {})
            if err.get("code") == "missing_files":
                return body, err.get("missing", [])
            raise RuntimeError(f"Vercel deploy error {e.code}: {body}") from e

    # 3. First attempt — Vercel will tell us which files are missing
    deploy_resp, missing_shas = _post_deployment(deploy_payload)

    # 4. Upload missing files
    if missing_shas:
        sha_to_file = {f["sha"]: f for f in files_meta}
        for sha in missing_shas:
            f = sha_to_file.get(sha)
            if not f:
                continue
            content_type = (
                "application/javascript"  if f["file"].endswith(".js")   else
                "text/html; charset=utf-8" if f["file"].endswith(".html") else
                "application/json"        if f["file"].endswith(".json") else
                "text/plain"
            )
            upload_req = urllib.request.Request(
                f"https://api.vercel.com/v2/files{team_param}",
                data=f["_content"],
                headers={
                    "Authorization":   f"Bearer {token}",
                    "Content-Type":    content_type,
                    "x-vercel-digest": sha,
                    "Content-Length":  str(f["size"]),
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(upload_req, timeout=60) as ur:
                    pass  # 200 or 204 = OK
            except urllib.error.HTTPError as e:
                if e.code not in (200, 204, 409):  # 409 = already uploaded, fine
                    raise

        # 5. Re-submit deployment now that all files are uploaded
        deploy_resp, _ = _post_deployment(deploy_payload)

    deployment_id  = deploy_resp.get("id", "")
    deploy_url_raw = deploy_resp.get("url", "")

    # 6. Poll for READY
    if deployment_id:
        for _ in range(90):  # up to 90s
            poll_req = urllib.request.Request(
                f"https://api.vercel.com/v13/deployments/{deployment_id}{team_param}",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(poll_req, timeout=15) as pr:
                poll = json.loads(pr.read())
            state = poll.get("status") or poll.get("readyState", "")
            if state in ("READY", "ERROR", "CANCELED"):
                break
            time.sleep(2)

    return f"https://{deploy_url_raw}" if deploy_url_raw and not deploy_url_raw.startswith("http") else deploy_url_raw


# ── Slug helpers ───────────────────────────────────────────────────────────────
def make_company_slug(practice_name: str) -> str:
    """Convert practice name to URL-safe slug."""
    import re
    slug = practice_name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:80]  # Vercel path limit safety


def url_encode_name(practice_name: str) -> str:
    return urllib.parse.quote(practice_name, safe="")


# ── Add SLACK env var to Vercel project ───────────────────────────────────────
def ensure_vercel_env(project_id: str, token: str, slack_webhook: str):
    """Set SLACK_D100_OPENS_WEBHOOK env var on the Vercel project (idempotent)."""
    # First try to delete existing (in case it changed)
    payload = json.dumps({
        "key":    "SLACK_D100_OPENS_WEBHOOK",
        "value":  slack_webhook,
        "type":   "encrypted",
        "target": ["production", "preview"]
    }).encode()

    req = urllib.request.Request(
        f"https://api.vercel.com/v10/projects/{project_id}/env",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            pass  # 200 or 409 (already exists) are both fine
    except urllib.error.HTTPError as e:
        if e.code != 409:  # 409 = already exists, that's fine
            print(f"  ⚠ Could not set Vercel env var: {e.code}")


# ── Deploy deliverables page ───────────────────────────────────────────────────
def deploy_deliverables(
    run_dir: Path,
    practice_name: str,
    token: str,
    dry_run: bool = False,
) -> str:
    """
    Copy index.html from run_dir into vercel-dist/[slug]/index.html
    then run `vercel --prod` from vercel-dist/.
    Returns the live URL.
    """
    slug        = make_company_slug(practice_name)
    index_src   = run_dir / "index.html"
    company_dir = VERCEL_DIST / slug

    if not index_src.exists():
        raise RuntimeError(f"index.html not found in {run_dir}")
    if index_src.stat().st_size < 50_000:
        raise RuntimeError(f"index.html too small ({index_src.stat().st_size}B) — build failed?")

    if dry_run:
        print(f"  [DRY RUN] Would deploy deliverables → healthbizleads.com/{slug}/")
        return f"https://healthbizleads.com/{slug}/"

    # Create company subfolder and copy HTML
    company_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(str(index_src), str(company_dir / "index.html"))
    print(f"  ✓ Copied index.html → vercel-dist/{slug}/")

    # Deploy via Vercel REST API (no CLI needed — pure Python, works in subagents)
    print(f"  🚀 Deploying deliverables project to Vercel REST API...")
    deploy_url = _vercel_api_deploy(
        dist_dir=VERCEL_DIST,
        project_id="prj_7AZqL9Zo1z8GJMT5U0UvwA9yEK6C",
        team_id="team_PHGv2fagezEkW7AzGceiG4cs",
        token=token,
        project_name="healthbizleads-d100",
    )
    print(f"  ✓ Vercel deploy URL: {deploy_url}")

    live_url = f"https://healthbizleads.com/{slug}/"
    print(f"  ✓ Live → {live_url}")
    return live_url


# ── Build + deploy standalone assessment app ───────────────────────────────────
def deploy_assessment_app(
    run_dir: Path,
    practice_name: str,
    token: str,
    phase1_data: dict,
    phase2_data: dict,
    dry_run: bool = False,
) -> str:
    """
    Render app_template.html with the company's tokens, copy to app-dist/[slug]/,
    then deploy to app.healthbizleads.com.
    Returns the live URL.
    """
    slug        = make_company_slug(practice_name)
    app_tmpl    = TEMPLATES_DIR / "app_template.html"
    company_dir = APP_DIST / slug

    if not app_tmpl.exists():
        raise RuntimeError(f"app_template.html not found at {app_tmpl}")

    # Build token map (reuse same tokens as inject_report)
    tokens = _build_token_map(practice_name, phase1_data, phase2_data, slug)

    # Render template
    html = app_tmpl.read_text(encoding="utf-8")
    for key, val in tokens.items():
        html = html.replace(f"{{{{{key}}}}}", val)

    if dry_run:
        print(f"  [DRY RUN] Would deploy app → app.healthbizleads.com/{slug}/")
        return f"https://app.healthbizleads.com/{slug}/"

    # Write rendered app HTML
    company_dir.mkdir(parents=True, exist_ok=True)
    (company_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"  ✓ Rendered app.html → app-dist/{slug}/")

    # Deploy via Vercel REST API
    print(f"  🚀 Deploying assessment app to Vercel REST API...")
    _vercel_api_deploy(
        dist_dir=APP_DIST,
        project_id="prj_zFYgp4yGg4ou7j0xWNGSi6cSYrls",
        team_id="team_PHGv2fagezEkW7AzGceiG4cs",
        token=token,
        project_name="healthbizleads-app",
    )
    print(f"  ✓ App deploy complete")

    app_url = f"https://app.healthbizleads.com/{slug}/"
    print(f"  ✓ App live → {app_url}")
    return app_url


# ── Token map builder (mirrors inject_report.py logic) ────────────────────────
def _build_token_map(
    practice_name: str,
    phase1: dict,
    phase2: dict,
    slug: str,
) -> dict:
    """Build the {{TOKEN}} → value map for app_template.html."""
    import json as _json

    brand   = phase1.get("brand_colors", {})
    app_cfg = phase2.get("app_config", {})

    # Brand colors: prefer phase2 app_config colors (already validated in runner),
    # then fall back to phase1 CSS extraction
    brand_primary = brand.get("primary", "#1a6bff")
    brand_accent  = brand.get("accent",  "#00c2ff")
    bg_color      = brand.get("background", "#FFFFFF")

    # Compute adaptive app theme (light vs dark based on practice's bg color)
    app_theme = _compute_app_theme(brand_primary, bg_color)

    # ── Assessment: concerns list (labels for the concern selector) ──────────
    # Phase2 stores concerns as [{label, emoji}] under app_config.concerns
    DEFAULT_CONCERNS = [
        "Fatigue & Low Energy", "Gut & Digestive Health", "Hormone Imbalance",
        "Brain Fog / Cognitive", "Weight & Metabolism", "Chronic Pain / Inflammation"
    ]
    concerns_raw = app_cfg.get("concerns", [])
    if concerns_raw and isinstance(concerns_raw, list):
        if isinstance(concerns_raw[0], dict):
            # [{label, emoji}] → extract labels
            concern_labels = [c.get("label", "") for c in concerns_raw if c.get("label")]
        else:
            # already flat strings
            concern_labels = [c for c in concerns_raw if c]
    else:
        concern_labels = DEFAULT_CONCERNS

    # ── Symptom map: {concern_label: [symptom, ...]} ─────────────────────────
    # Phase2 now generates app_config.symptom_map keyed by concern label
    symptom_map = app_cfg.get("symptom_map", {})

    return {
        "PRACTICE_NAME":         practice_name,
        "PRACTICE_NAME_ENCODED": url_encode_name(practice_name),
        "COMPANY_SLUG":          slug,
        "DOCTOR_NAME":           phase1.get("doctor_name", "Dr. Smith"),
        "WEBSITE":               phase1.get("website", ""),
        "LOGO_URL":              phase1.get("logo_url", "") or phase1.get("images", {}).get("logo_url", ""),
        "FAVICON_URL":           phase1.get("images", {}).get("favicon_url", "") or phase1.get("logo_url", ""),
        "BOOKING_URL":           phase1.get("booking_url", "#") or phase1.get("website", "#"),
        "BRAND_PRIMARY":         brand_primary,
        "BRAND_ACCENT":          brand_accent,
        "ASSESSMENT_CONCERNS_JSON": _json.dumps(concern_labels, ensure_ascii=False),
        "ASSESSMENT_SYMPTOMS_JSON": _json.dumps(symptom_map, ensure_ascii=False),
        # Adaptive theme — computed from brand primary + background
        **app_theme,
    }


# ── CLI entry point ────────────────────────────────────────────────────────────
def main():
    import argparse
    p = argparse.ArgumentParser(description="D100 Vercel Incremental Deployer")
    p.add_argument("run_dir",     help="Path to the D100 run directory")
    p.add_argument("--dry-run",   action="store_true")
    p.add_argument("--no-app",    action="store_true", help="Skip assessment app deploy")
    args = p.parse_args()

    run_dir = Path(args.run_dir).resolve()
    env     = load_env()
    token   = env.get("VERCEL_TOKEN", "")

    if not token:
        print("❌ VERCEL_TOKEN not set in .env")
        sys.exit(1)

    # Load JSON data
    phase1_path = run_dir / "phase1_data.json"
    phase2_path = run_dir / "phase2_output.json"

    if not phase1_path.exists():
        print(f"❌ phase1_data.json not found in {run_dir}")
        sys.exit(1)

    phase1 = json.loads(phase1_path.read_text())
    phase2 = json.loads(phase2_path.read_text()) if phase2_path.exists() else {}

    practice_name = phase1.get("name") or phase1.get("practice_name", "Unknown Practice")
    print(f"\n📦 Deploying: {practice_name}")

    # 1) Deliverables page → healthbizleads.com/[slug]/
    report_url = deploy_deliverables(run_dir, practice_name, token, args.dry_run)

    # 2) Assessment app → app.healthbizleads.com/[slug]/
    app_url = None
    if not args.no_app:
        app_url = deploy_assessment_app(
            run_dir, practice_name, token, phase1, phase2, args.dry_run
        )

    print(f"\n✅ Deploy complete!")
    print(f"   Report: {report_url}")
    if app_url:
        print(f"   App:    {app_url}")

    return report_url, app_url


if __name__ == "__main__":
    main()
