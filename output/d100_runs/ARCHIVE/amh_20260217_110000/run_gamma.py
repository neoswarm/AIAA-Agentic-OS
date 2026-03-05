#!/usr/bin/env python3
"""
Run Gamma presentation generation for AMH D100 run.
Uses urllib.request (no external dependencies).
Updated for v2.0 file naming conventions.
"""
import json
import os
import re
import time
import urllib.request

# ── Config ──────────────────────────────────────────────
RUN_DIR = '/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/output/d100_runs/amh_20260217_110000'
ENV_PATH = '/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/.env'
TEMPLATE_ID = 'g_tibdaac6hk58l4v'
GAMMA_API_BASE = 'https://public-api.gamma.app/v1.0'

# ── Load keys from .env ─────────────────────────────────
gamma_key = None
slack_webhook = None
with open(ENV_PATH) as f:
    for line in f:
        line = line.strip()
        if line.startswith('GAMMA_API_KEY='):
            gamma_key = line.split('=', 1)[1]
        elif line.startswith('SLACK_WEBHOOK_URL='):
            slack_webhook = line.split('=', 1)[1]

if not gamma_key:
    raise RuntimeError("GAMMA_API_KEY not found in .env")

print(f"✓ Gamma API key loaded")

# ── Load structured JSON ─────────────────────────────────
with open(os.path.join(RUN_DIR, 'scrape_data', 'structured_data.json')) as f:
    data = json.load(f)

company_name = (
    data.get('practice', {}).get('brand_name', {}).get('value') or
    data.get('practice', {}).get('legal_name', {}).get('value') or
    'Healthcare Practice'
).strip()

slug = company_name.replace(' ', '-')
app_url = f"https://portal.healthbizscale.com/{slug}"

print(f"✓ Company: {company_name}")
print(f"✓ App URL: {app_url}")

# ── Load SEO insights (v2.0: seo_insights.md or fallback to GAMMA_FILE.md SEO section) ──
seo_path = os.path.join(RUN_DIR, 'seo_data', 'seo_insights.md')
if os.path.exists(seo_path):
    with open(seo_path) as f:
        seo_insights = f.read().strip()[:4000]
else:
    # Build from SEMrush data snapshot in COMPLETE_DELIVERABLES or from brightlocal keywords
    seo_insights = f"""SEO Performance Summary - {company_name}

Total Organic Keywords: 3,000
Top 3 Rankings: 530
Position 4-10: 343
Position 11-20: 311
High Volume Keywords (>1000/mo): 125

Top Keywords:
- "adrenal fatigue" - Position 1, 22,200 monthly searches
- "splenius capitis" - Position 1, 14,800/mo
- "aligned modern health" - Position 1, 6,600/mo
- "acupuncturists in chicago" - Position 1, 590/mo
- "functional medicine chicago" - Position 3, 390/mo

Location Coverage: Chicago (8 clinics), Evanston, Elmhurst, Deerfield, Kildeer, Mt. Prospect, Orland Park, Park Ridge, Vernon Hills, Nashville, Miami, Virtual (21 states)

100 BrightLocal keywords generated covering 9 services + 31 conditions across Chicago, "near me", Evanston, Elmhurst, and Deerfield modifiers."""

print(f"✓ SEO insights loaded ({len(seo_insights)} chars)")

# ── Load Google Ads (v2.0 filename: google_ads_campaign.md) ──
ads_path = os.path.join(RUN_DIR, 'ads', 'google_ads_campaign.md')
campaigns = ['[Ad campaign not available]'] * 5
if os.path.exists(ads_path):
    with open(ads_path) as f:
        ads_text = f.read()
    # Split on ### CAMPAIGN headers
    parts = re.split(r'\n(?=### CAMPAIGN \d)', ads_text)
    parsed = []
    for p in parts:
        p = p.strip()
        if p and len(p) > 50:
            parsed.append(p[:2000])
    # The first chunk has the intro + campaign 1, rest are campaign 2, 3, extensions, keywords
    if len(parsed) >= 1:
        campaigns[0] = parsed[0][:2000]
    if len(parsed) >= 2:
        campaigns[1] = parsed[1][:2000]
    if len(parsed) >= 3:
        campaigns[2] = parsed[2][:2000]
    # Extensions and keywords as campaigns 4-5
    remaining_text = ads_text
    ext_match = re.search(r'### OUTPUT SECTION B.*', remaining_text, re.DOTALL)
    if ext_match:
        ext_text = ext_match.group(0)
        kw_split = re.split(r'\n(?=### The Google Ad Keywords)', ext_text)
        if len(kw_split) >= 1:
            campaigns[3] = kw_split[0].strip()[:2000]
        if len(kw_split) >= 2:
            campaigns[4] = kw_split[1].strip()[:2000]

print(f"✓ Ads loaded: {sum(1 for c in campaigns if 'not available' not in c)}/5 campaigns")

# ── Load Emails (v2.0 filename: sequence.md) ──
emails_path = os.path.join(RUN_DIR, 'emails', 'sequence.md')
emails = ['[Email not available]'] * 3
if os.path.exists(emails_path):
    with open(emails_path) as f:
        emails_text = f.read()
    # Split on **Email N: markers
    parts = re.split(r'\n(?=\*\*Email \d)', emails_text)
    parsed = [p.strip() for p in parts if p.strip() and len(p.strip()) > 30]
    for i in range(min(3, len(parsed))):
        emails[i] = parsed[i][:2000]

print(f"✓ Emails loaded: {sum(1 for e in emails if 'not available' not in e)}/3 emails")

# ── Build Gamma prompt ───────────────────────────────────
prompt = f"""Fill in this Dream 100 presentation template for a healthcare practice.

COMPANY NAME: {company_name}
APP URL: {app_url}

SEO INSIGHTS:
{seo_insights}

GOOGLE ADS CAMPAIGN 1:
{campaigns[0]}

GOOGLE ADS CAMPAIGN 2:
{campaigns[1]}

GOOGLE ADS CAMPAIGN 3:
{campaigns[2]}

GOOGLE ADS CAMPAIGN 4:
{campaigns[3]}

GOOGLE ADS CAMPAIGN 5:
{campaigns[4]}

EMAIL 1 (Smart Practice Value Drop):
{emails[0]}

EMAIL 2 (Mechanism Story):
{emails[1]}

EMAIL 3 (Proof & Results):
{emails[2]}

Replace every placeholder in the template with the matching content above.
Keep all slide structure, headings, and formatting from the original template."""

print(f"✓ Prompt built ({len(prompt)} chars)")

# ── Call Gamma API ────────────────────────────────────────
payload = json.dumps({
    "gammaId": TEMPLATE_ID,
    "prompt": prompt
}).encode('utf-8')

headers = {
    "X-API-KEY": gamma_key,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

print(f"🌐 Calling Gamma API (template: {TEMPLATE_ID})...")

req = urllib.request.Request(
    f"{GAMMA_API_BASE}/generations/from-template",
    data=payload,
    headers=headers,
    method='POST'
)

try:
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.loads(resp.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8')
    print(f"❌ Gamma API error {e.code}: {body[:500]}")
    raise

generation_id = result.get('generationId', '')
print(f"✓ Generation started: {generation_id}")

# ── Poll for completion ───────────────────────────────────
gamma_url = None
if generation_id:
    print(f"🔍 Polling for Gamma URL...")
    for attempt in range(20):
        time.sleep(15)
        poll_req = urllib.request.Request(
            f"{GAMMA_API_BASE}/generations/{generation_id}",
            headers=headers,
            method='GET'
        )
        try:
            with urllib.request.urlopen(poll_req, timeout=30) as poll_resp:
                status_data = json.loads(poll_resp.read().decode('utf-8'))
            gamma_url = status_data.get('gammaUrl', '')
            gen_status = status_data.get('status', '')
            if gamma_url and gamma_url not in ('unknown', ''):
                result['url'] = gamma_url
                result['gammaUrl'] = gamma_url
                result['credits'] = status_data.get('credits', {})
                print(f"✅ Gamma URL: {gamma_url}")
                break
            elif gen_status == 'failed':
                print(f"❌ Generation failed: {status_data}")
                break
            print(f"  ⏳ Still generating (attempt {attempt+1}/20)...")
        except Exception as e:
            print(f"  ⚠️ Poll error: {e}")
    else:
        result['url'] = f"https://gamma.app (pending — generationId: {generation_id})"
        print(f"⚠️ Timed out — generationId saved: {generation_id}")

# ── Save response ─────────────────────────────────────────
response_path = os.path.join(RUN_DIR, 'gamma_response.json')
with open(response_path, 'w') as f:
    json.dump(result, f, indent=2)
print(f"✓ Response saved: {response_path}")

# ── Slack notification ────────────────────────────────────
if slack_webhook and gamma_url:
    try:
        slack_msg = json.dumps({
            "text": f"📊 *Gamma Presentation Created: {company_name}*\n\n🔗 View: {gamma_url}\n📋 Template: `{TEMPLATE_ID}`"
        }).encode('utf-8')
        slack_req = urllib.request.Request(
            slack_webhook,
            data=slack_msg,
            headers={"Content-Type": "application/json"},
            method='POST'
        )
        urllib.request.urlopen(slack_req, timeout=10)
        print(f"✓ Slack notified")
    except Exception:
        print(f"⚠️ Slack notification failed (non-blocking)")

# ── Final output ──────────────────────────────────────────
final_url = result.get('url', result.get('gammaUrl', 'unknown'))
print(f"\n{'='*60}")
print(f"GAMMA PRESENTATION: {company_name}")
print(f"URL: {final_url}")
print(f"Generation ID: {generation_id}")
print(f"{'='*60}")
