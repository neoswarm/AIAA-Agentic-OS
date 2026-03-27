#!/usr/bin/env python3
"""
Fix Loom + red/green banners on 38 affected original pages.

The ads-upgrade background task re-ran inject_report.py with the new template,
which moved the red/green banners INSIDE the hidden loom-video-section div.
In the old template they were always visible (outside any loom section).

This script:
1. Moves red/green banners OUTSIDE loom-video-section (so always visible)
2. Restores forum-health loom_id to 8ba2650e0d8f4e19a3a118d86beb99ec
3. Deploys all affected pages via Vercel
"""

import re
import sys
import subprocess
from pathlib import Path

SITE_DIR = Path("output/site")

AFFECTED_SLUGS = [
    "functional-medicine-center-of-new-jersey",
    "parsley-health",
    "integrated-health-clinic",
    "advanced-functional-medicine",
    "longevity-health-clinic",
    "raby-institute-for-integrative-medicine",
    "longevity-health-institute",
    "healthy-longevity-clinic",
    "the-restore-center",
    "resilience-naturopathic",
    "proactiv-wellness-centers",
    "practical-healing-center",
    "south-carolina-center-for-integrative-medicine",
    "integrative-family-medicine-of-iowa",
    "enhanced-wellness-living",
    "alive-and-well",
    "richmond-integrative-functional-medicine",
    "integrative-wellness-center-of-jacksonville",
    "maxwell-clinic",
    "wiseman-family-practice",
    "healing-grove-health-center",
    "philadelphia-integrative-medicine",
    "inhealthrva",
    "west-holistic-medicine",
    "alive-integrative-medicine",
    "functional-medicine-florida",
    "shift-functional-medicine",
    "w-clinic-of-integrative-medicine",
    "restoration-healthcare",
    "enliven-functional-medicine",
    "atma-clinic",
    "holistic-health-collective",
    "toronto-functional-medicine-centre",
    "delaware-integrative-medicine",
    "delaware-integrative-healthcare",
    "outside-the-box-health",
    "biodesign-wellness-medspa",
    "forum-health",  # also needs loom_id restored
]

FORUM_HEALTH_LOOM_ID = "8ba2650e0d8f4e19a3a118d86beb99ec"

RED_GREEN_HTML = """
    <div class="red-block max-w-4xl mx-auto">
      <div class="red-block__title">⛔ Don't Skip The Video Above</div>
      <div class="red-block__body">Seriously… It's A Personalized Video Made For You, &amp; Only You.</div>
    </div>

    <div class="green-block max-w-4xl mx-auto">
      <h3>How This Document Can Help Your Practice</h3>
      <p>Somewhere between your website and your front desk, patients are leaving. This doc shows you exactly where — and what it costs. Every number is pulled from your market. Every campaign is built for your conditions. Read it and you'll know exactly what to fix — whether you work with us or not.</p>
    </div>
"""

def fix_page(slug: str) -> bool:
    """Fix a single page. Returns True if modified."""
    path = SITE_DIR / slug / "index.html"
    if not path.exists():
        print(f"  ⚠️  Not found: {path}")
        return False

    content = path.read_text(encoding="utf-8")
    original = content

    # ── Step 1: Remove red/green from inside loom-video-section ──────────────
    # Pattern: inside loom-video-section, red-block and green-block divs
    # We replace the content of loom-video-section to only keep the video iframe part

    loom_section_pattern = re.compile(
        r'(<div id="loom-video-section"[^>]*>)'  # opening tag
        r'(.*?)'                                   # content
        r'(</div><!-- /#loom-video-section -->)',   # closing tag
        re.DOTALL
    )

    match = loom_section_pattern.search(content)
    if not match:
        print(f"  ⚠️  No loom-video-section found in {slug}")
        return False

    loom_open = match.group(1)
    loom_content = match.group(2)
    loom_close = match.group(3)

    # Extract just the video wrapper part (before red-block)
    red_block_pos = loom_content.find('<div class="red-block')
    if red_block_pos == -1:
        print(f"  ⚠️  No red-block inside loom section in {slug} — checking if already outside")
        # Check if red-block is already outside
        loom_end_pos = content.find('</div><!-- /#loom-video-section -->')
        red_pos = content.find('<div class="red-block')
        if red_pos > loom_end_pos:
            print(f"  ✓  {slug}: banners already outside loom section")
            # Still might need loom_id fix for forum-health
        else:
            print(f"  ⚠️  {slug}: red-block missing entirely, injecting after loom section")
            # Inject red/green after loom section
            loom_end_marker = '</div><!-- /#loom-video-section -->'
            content = content.replace(
                loom_end_marker,
                loom_end_marker + "\n" + RED_GREEN_HTML,
                1
            )
    else:
        # Keep only the video part (before red-block), trim trailing whitespace
        video_only = loom_content[:red_block_pos].rstrip()

        # Rebuild loom section with only the video
        new_loom_section = loom_open + "\n" + video_only + "\n\n    " + loom_close

        # Append red/green AFTER the loom section
        new_loom_section_with_banners = new_loom_section + "\n" + RED_GREEN_HTML

        content = content[:match.start()] + new_loom_section_with_banners + content[match.end():]

    # ── Step 2: Forum-health loom_id restore ─────────────────────────────────
    if slug == "forum-health":
        # Restore loom_id in JS config
        content = re.sub(
            r'loom_id:\s*"[^"]*"',
            f'loom_id: "{FORUM_HEALTH_LOOM_ID}"',
            content,
            count=1
        )
        # Also update iframe src to include the loom ID
        content = re.sub(
            r'(src="https://www\.loom\.com/embed/)[^"]*(")',
            rf'\g<1>{FORUM_HEALTH_LOOM_ID}?hide_owner=true&hide_share=true&hide_title=true&hideEmbedTopBar=true\g<2>',
            content,
            count=1
        )
        # Remove display:none from loom-video-section for forum-health (has a real loom)
        content = content.replace(
            'id="loom-video-section" style="display:none"',
            'id="loom-video-section"',
            1
        )
        print(f"  🎥  forum-health: loom_id restored to {FORUM_HEALTH_LOOM_ID}")

    if content == original:
        print(f"  ⏭  {slug}: no changes needed")
        return False

    path.write_text(content, encoding="utf-8")
    print(f"  ✅  {slug}: fixed")
    return True


def main():
    fixed = []
    skipped = []

    print("🔧 Fixing red/green banners on affected pages...\n")
    for slug in AFFECTED_SLUGS:
        if fix_page(slug):
            fixed.append(slug)
        else:
            skipped.append(slug)

    print(f"\n📊 Fixed: {len(fixed)}, Skipped: {len(skipped)}")

    if not fixed:
        print("Nothing to deploy.")
        return

    print("\n🚀 Deploying via Vercel...")
    result = subprocess.run(
        ["vercel", "--prod", "--yes", "--scope", "kohl-digital"],
        cwd=str(SITE_DIR.parent),  # output/
        capture_output=True,
        text=True
    )

    # Try from output/site directly
    if result.returncode != 0:
        result = subprocess.run(
            ["vercel", "deploy", "--prod", "--yes", "--scope", "kohl-digital"],
            cwd=str(SITE_DIR),
            capture_output=True,
            text=True
        )

    print(result.stdout[-2000:] if result.stdout else "")
    if result.stderr:
        print("STDERR:", result.stderr[-1000:])

    if result.returncode == 0:
        print("\n✅ Deployed successfully!")
    else:
        print(f"\n❌ Deploy failed (rc={result.returncode})")
        sys.exit(1)


if __name__ == "__main__":
    main()
