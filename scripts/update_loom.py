#!/usr/bin/env python3
"""
update_loom.py — Swap the Loom video ID in a deployed deliverables page.

Usage:
  python3 update_loom.py <slug> <loom_id_or_url>

Examples:
  python3 update_loom.py integrated-health-of-indiana-inc abc123def456
  python3 update_loom.py integrated-health-of-indiana-inc https://www.loom.com/share/abc123def456

What it does:
  1. Reads vercel-dist/<slug>/index.html
  2. Replaces all loom embed IDs in-place
  3. Re-deploys to Vercel (single file, ~10 seconds)
  4. Also patches phase1_data.json so future inject_report runs keep it

Also supports --all to update every slug at once (broadcast same Loom to all).
"""

import sys, re, json, subprocess
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent
ROOT_DIR    = SCRIPT_DIR.parent
VERCEL_DIST = ROOT_DIR / "vercel-dist"
OUTPUT_RUNS = ROOT_DIR / "output" / "d100_runs"


def extract_loom_id(raw: str) -> str:
    """Accept full URL or bare ID — always return just the ID."""
    # https://www.loom.com/share/abc123  or  /embed/abc123
    m = re.search(r'loom\.com/(?:share|embed)/([a-f0-9]+)', raw)
    if m:
        return m.group(1)
    # Bare alphanumeric ID
    if re.fullmatch(r'[a-f0-9]{32}', raw.strip()):
        return raw.strip()
    # Allow shorter IDs too
    if re.fullmatch(r'[a-zA-Z0-9_-]{8,}', raw.strip()):
        return raw.strip()
    raise ValueError(f"Could not parse Loom ID from: {raw!r}")


def patch_html(html: str, new_id: str) -> tuple[str, int]:
    """Replace all loom embed IDs. Returns (new_html, count)."""
    # Matches: loom.com/embed/ANYTHING  (up to next quote/question mark)
    new_html, n = re.subn(
        r'(loom\.com/embed/)[a-zA-Z0-9_-]+',
        rf'\g<1>{new_id}',
        html
    )
    # Also patch JS CONFIG loom_id: "..."
    new_html, n2 = re.subn(
        r'(loom_id:\s*")[^"]*(")',
        rf'\g<1>{new_id}\g<2>',
        new_html
    )
    return new_html, n + n2


def find_run_dir(slug: str) -> Path | None:
    """Find the most recent run dir matching slug."""
    matches = sorted(OUTPUT_RUNS.glob(f"*{slug}*"), reverse=True)
    for m in matches:
        if m.is_dir():
            return m
    return None


def deploy_to_vercel(slug: str, html_path: Path) -> bool:
    """Deploy a single file via deploy_vercel_incremental.py."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from deploy_vercel_incremental import deploy_single_file
        token = _get_vercel_token()
        deploy_single_file(slug, html_path, token)
        return True
    except ImportError:
        pass

    # Fallback: re-run inject + full deploy
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "inject_report.py"),
             str(find_run_dir(slug) or ""), "--deploy-vercel"],
            capture_output=True, text=True
        )
        print(result.stdout[-2000:] if result.stdout else "")
        return result.returncode == 0
    except Exception as e:
        print(f"  ⚠ Deploy failed: {e}")
        return False


def _get_vercel_token() -> str:
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("VERCEL_TOKEN="):
                return line.split("=", 1)[1].strip()
    import os
    return os.environ.get("VERCEL_TOKEN", "")


def _patch_vercel_dist(slug: str, new_id: str) -> bool:
    html_path = VERCEL_DIST / slug / "index.html"
    if not html_path.exists():
        print(f"  ✗ Not found: {html_path}")
        return False
    html = html_path.read_text(encoding="utf-8")
    new_html, count = patch_html(html, new_id)
    if count == 0:
        print(f"  ⚠ No Loom embeds found in {slug}/index.html")
        return False
    html_path.write_text(new_html, encoding="utf-8")
    print(f"  ✓ Patched {count} loom embed(s) in vercel-dist/{slug}/index.html")
    return True


def _patch_phase1(slug: str, new_id: str):
    run_dir = find_run_dir(slug)
    if not run_dir:
        return
    p1_path = run_dir / "phase1_data.json"
    if not p1_path.exists():
        return
    p1 = json.loads(p1_path.read_text(encoding="utf-8"))
    p1["loom_id"] = new_id
    p1_path.write_text(json.dumps(p1, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Saved loom_id to {p1_path.relative_to(ROOT_DIR)}")


def update_slug(slug: str, new_id: str, deploy: bool = True):
    print(f"\n🎬 Updating Loom → {slug}")
    print(f"   New ID: {new_id}")
    ok = _patch_vercel_dist(slug, new_id)
    _patch_phase1(slug, new_id)
    if ok and deploy:
        token = _get_vercel_token()
        if not token:
            print("  ⚠ No VERCEL_TOKEN found — skipping deploy")
            return
        print("  🚀 Deploying to Vercel...")
        sys.path.insert(0, str(SCRIPT_DIR))
        try:
            from deploy_vercel_incremental import deploy_deliverables
            html_path = VERCEL_DIST / slug / "index.html"
            run_dir = find_run_dir(slug) or (VERCEL_DIST / slug)
            url = deploy_deliverables(run_dir, slug.replace("-", " ").title(), token)
            print(f"  ✅ Live: {url}")
        except Exception as e:
            print(f"  ⚠ Deploy error: {e}")


def main():
    args = sys.argv[1:]
    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    deploy = "--no-deploy" not in args
    args = [a for a in args if a != "--no-deploy"]

    # --all: broadcast same Loom to every slug in vercel-dist
    if "--all" in args:
        args.remove("--all")
        if not args:
            print("Usage: update_loom.py --all <loom_id_or_url>")
            sys.exit(1)
        new_id = extract_loom_id(args[0])
        slugs = [d.name for d in VERCEL_DIST.iterdir() if d.is_dir() and d.name != "api"]
        print(f"Broadcasting Loom ID {new_id} to {len(slugs)} slug(s)...")
        for slug in slugs:
            update_slug(slug, new_id, deploy=deploy)
        return

    if len(args) < 2:
        print("Usage: update_loom.py <slug> <loom_id_or_url>")
        sys.exit(1)

    slug   = args[0]
    new_id = extract_loom_id(args[1])
    update_slug(slug, new_id, deploy=deploy)


if __name__ == "__main__":
    main()
