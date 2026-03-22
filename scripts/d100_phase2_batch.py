#!/usr/bin/env python3
"""
d100_phase2_batch.py — Batch Phase 2 generator via Anthropic API
Scans all run dirs with phase1_data.json but no phase2_output.json,
calls Claude Sonnet 4.6 API for each, writes phase2_output.json.

Usage:
    python3 scripts/d100_phase2_batch.py
    python3 scripts/d100_phase2_batch.py --workers 5
    python3 scripts/d100_phase2_batch.py --run-dir output/d100_runs/specific-dir
"""
import json
import os
import re
import sys
import time
import concurrent.futures
import urllib.request
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_ROOT  = PROJECT_ROOT / "output" / "d100_runs"
ENV_PATH     = PROJECT_ROOT / ".env"
MODEL        = "claude-sonnet-4-6"
MAX_TOKENS   = 8192
MAX_WORKERS  = 4  # parallel API calls

# ── Load env ──────────────────────────────────────────────────────────────────
def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if v})
    return env

# ── CLAUDE_JSON_SCHEMA (matches runner) ───────────────────────────────────────
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
        "Callout Extensions": ["string × 4 callouts, each ≤25 chars — practice-specific benefits"],
        "Sitelink Extensions": ["Label | short description × 3"]
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
    "primaryColor": "#hex — dominant BRAND color (not black/white)",
    "primaryDark": "#hex — darker shade",
    "primaryLight": "#hex — lighter shade",
    "primaryXLight": "#hex — very light tint",
    "backgroundColor": "#hex",
    "bookingUrl": "string",
    "phone": "string",
    "concerns": [{"label": "string — 2-4 word health concern", "emoji": "string"}],
    "symptom_map": {
      "<concern label>": ["symptom string × 6-8"]
    },
    "careModels": [{"name": "string", "desc": "string", "price": "string"}]
  }
}
"""

def build_prompt(p1: dict) -> str:
    context = p1.get("context", p1.get("website", ""))
    scrape  = p1.get("raw_scrape", "")[:6000]
    semrush = p1.get("semrush", {})
    crawl   = p1.get("crawl", {})
    colors  = p1.get("brand_colors", {})

    color_summary = "\n".join([f"  - {k}: {v}" for k, v in colors.items()])

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
        f"  Pos #1:      {semrush.get('pos1_count', semrush.get('pos1_3_count',0))} keywords\n"
        f"  Pos #2-3:    {semrush.get('pos2_3_count', 0)} keywords\n"
        f"  Pos #4-10:   {semrush.get('pos4_10_count', 0)} keywords ← page 1, low CTR\n"
        f"  Pos #11-20:  {semrush.get('pos11_20_count', 0)} keywords ← page 2, near-zero CTR"
    )
    ai_serp  = semrush.get("ai_overview_serp_count", "N/A")
    ai_cited = semrush.get("ai_overview_cited_count", "N/A")
    sf_traffic = semrush.get("serp_features_traffic", 0)
    data_source = semrush.get("source", "dataforseo")

    semrush_block = f"""SEO DATA ({data_source}):
Domain Snapshot:
  Global Rank:       #{semrush.get('domain_rank', 0):,}
  Keywords Ranked:   {semrush.get('unique_keywords', 0):,}
  Monthly Traffic:   ~{semrush.get('estimated_traffic', 0):,} visits
  Traffic Value:     ${semrush.get('traffic_value', 0):,}/mo

Position Distribution:
{pos_dist}

AI Overview Coverage:
  Keywords triggering AI Overview: {ai_serp}
  Keywords where practice is cited: {ai_cited}
  SERP Features Traffic: ~{sf_traffic:,} visits/mo

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
{scrape}

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
- Emails are PATIENT-FACING nurture emails sent BY the practice TO prospective patients after health assessment completion. NOT B2B outreach.
- Email 1 (smart_practice_value_drop): empathetic opening for [FIRST_NAME] referencing [PRIMARY_SYMPTOM], one high-value root-cause insight, soft booking CTA
- Email 2 (mechanism_story): simple analogy explaining biological mechanism, what standard care misses, practice approach as different
- Email 3 (proof_and_results): short anonymized patient story, results-vary disclaimer, clear booking CTA
- Use personalization variables: [FIRST_NAME], [PRIMARY_SYMPTOM], [KEY_ASSESSMENT_INSIGHT], [RECOMMENDED_SERVICE_OR_FOCUS], [BOOKING_LINK]
- 150-200 words per email. Short paragraphs. No emojis. No aggressive urgency.
- Keywords: exactly 30 unique strings
- DO NOT include any YouTube or Calendly URLs anywhere in output
- JSON SAFETY: NEVER use double-quote characters (") inside string values. Use single quotes (') or rephrase. Unescaped double quotes break JSON parsing."""


def call_api(prompt: str, api_key: str) -> str:
    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
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


def repair_json(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```\s*$", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return text.strip()


def process_run_dir(run_dir: Path, api_key: str, idx: int, total: int) -> dict:
    domain = run_dir.name
    p1_path = run_dir / "phase1_data.json"
    p2_path = run_dir / "phase2_output.json"

    if p2_path.exists():
        print(f"  ⏭  [{idx}/{total}] {domain} — phase2_output.json already exists, skipping")
        return {"domain": domain, "status": "skipped"}

    if not p1_path.exists():
        print(f"  ⚠️  [{idx}/{total}] {domain} — no phase1_data.json, skipping")
        return {"domain": domain, "status": "no_phase1"}

    print(f"  🤖 [{idx}/{total}] {domain} — calling API...")
    t0 = time.time()

    try:
        p1 = json.loads(p1_path.read_text(encoding="utf-8"))
        prompt = build_prompt(p1)
        raw = call_api(prompt, api_key)
        repaired = repair_json(raw)
        data = json.loads(repaired)
        p2_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        elapsed = time.time() - t0
        print(f"  ✅ [{idx}/{total}] {domain} — done in {elapsed:.1f}s")
        return {"domain": domain, "status": "completed", "run_dir": str(run_dir)}
    except json.JSONDecodeError as e:
        print(f"  ❌ [{idx}/{total}] {domain} — JSON parse error: {e}")
        # Save raw for debugging
        (run_dir / "phase2_raw_response.txt").write_text(raw if 'raw' in dir() else "no response", encoding="utf-8")
        return {"domain": domain, "status": "json_error", "error": str(e)}
    except Exception as e:
        print(f"  ❌ [{idx}/{total}] {domain} — error: {e}")
        return {"domain": domain, "status": "error", "error": str(e)}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--run-dir", help="Single run dir to process")
    args = parser.parse_args()

    env = load_env()
    api_key = env.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in .env")
        sys.exit(1)

    print(f"API key loaded: {api_key[:20]}...")

    # Find run dirs to process
    if args.run_dir:
        run_dirs = [Path(args.run_dir)]
    else:
        run_dirs = [
            d for d in OUTPUT_ROOT.iterdir()
            if d.is_dir()
            and (d / "phase1_data.json").exists()
            and not (d / "phase2_output.json").exists()
        ]
        run_dirs.sort(key=lambda d: d.name)

    total = len(run_dirs)
    print(f"\n🚀 Phase 2 batch: {total} sites to process, {args.workers} workers")
    print(f"   Model: {MODEL}\n")

    if total == 0:
        print("Nothing to do — all run dirs already have phase2_output.json")
        return

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {
            ex.submit(process_run_dir, d, api_key, i+1, total): d
            for i, d in enumerate(run_dirs)
        }
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    completed = [r for r in results if r["status"] == "completed"]
    skipped   = [r for r in results if r["status"] == "skipped"]
    errors    = [r for r in results if r["status"] not in ("completed", "skipped", "no_phase1")]

    print(f"\n{'='*60}")
    print(f"✅ Completed: {len(completed)}")
    print(f"⏭  Skipped:   {len(skipped)}")
    print(f"❌ Errors:    {len(errors)}")
    if errors:
        for e in errors:
            print(f"   - {e['domain']}: {e.get('error','')}")

    print(f"\nDone. Run --phase3-only to deploy:")
    print(f"  python3 scripts/d100_v3_runner.py --csv D100-input/batch_mar20_remaining.csv --phase3-only")


if __name__ == "__main__":
    main()
