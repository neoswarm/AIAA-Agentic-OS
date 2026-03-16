"""
Gamma Presentation Generator for IMC North Carolina D100 Run
Run after all assets are ready.
"""
import json, re, time, os, sys
import requests
from pathlib import Path
from datetime import datetime

RUN_DIR = Path("/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/output/d100_runs/imc_20260218_223623")
ENV_PATH = Path("/Users/neo/Documents/Claude Code/AIAA-Agentic-OS/.env")
TEMPLATE_ID = "g_tibdaac6hk58l4v"
GAMMA_API_BASE = "https://public-api.gamma.app/v1.0"

# Load API keys
api_key = ""
slack_webhook = ""
with open(ENV_PATH) as f:
    for line in f:
        if line.startswith("GAMMA_API_KEY="):
            api_key = line.strip().split("=", 1)[1]
        if line.startswith("SLACK_WEBHOOK_URL="):
            slack_webhook = line.strip().split("=", 1)[1]

company_name = "Integrative Medical Clinic of North Carolina"
app_url = "https://portal.healthbizscale.com/Integrative-Medical-Clinic-of-North-Carolina"

# Load content files
def load_file(path, fallback):
    if Path(path).exists():
        return Path(path).read_text(encoding="utf-8").strip()
    return fallback

seo_insights = load_file(RUN_DIR / "seo_data/seo_insights.md", "[SEO analysis not available]")
# Strip markdown headers for cleaner Gamma text
seo_insights = re.sub(r'^#{1,3} .+\n', '', seo_insights, flags=re.MULTILINE).strip()[:4000]

# Load ads - split into campaigns
ads_text = load_file(RUN_DIR / "ads/google_ads_campaign.md", "")
if ads_text:
    sections = re.split(r'\n(?=### CAMPAIGN |\n## )', ads_text)
    campaigns = [s.strip() for s in sections if s.strip() and len(s.strip()) > 30]
    if len(campaigns) < 3:
        # Try alternate split
        sections2 = re.split(r'\n(?=## (?:\d+\.|Campaign |\w+ \d+))', ads_text)
        campaigns2 = [s.strip() for s in sections2 if s.strip() and len(s.strip()) > 30]
        if len(campaigns2) > len(campaigns):
            campaigns = campaigns2
else:
    campaigns = []

while len(campaigns) < 5:
    campaigns.append("[Ad campaign not available]")
campaigns = [c[:2000] for c in campaigns[:5]]

# Load emails - split into 3
emails_text = load_file(RUN_DIR / "emails/sequence.md", "")
if emails_text:
    sections = re.split(r'\n(?=Email \d|EMAIL \d|## Email \d|────+\nEMAIL \d)', emails_text)
    emails = [s.strip() for s in sections if s.strip() and len(s.strip()) > 20]
else:
    emails = []

while len(emails) < 3:
    emails.append("[Email not available]")
emails = [e[:2000] for e in emails[:3]]

# Build prompt
prompt = f"""Fill in this Dream 100 presentation for IMCNC - a premium integrative medicine practice.

[COMPANY] = {company_name}
[APP_URL] = {app_url}

[SEO_INSIGHTS] =
{seo_insights[:2000]}

[AD_CAMPAIGN1] =
{campaigns[0]}

[AD_CAMPAIGN2] =
{campaigns[1]}

[AD_CAMPAIGN3] =
{campaigns[2]}

[AD_CAMPAIGN4] =
{campaigns[3]}

[AD_CAMPAIGN5] =
{campaigns[4]}

[EMAIL1] =
{emails[0]}

[EMAIL2] =
{emails[1]}

[EMAIL3] =
{emails[2]}

CRITICAL INSTRUCTIONS:
- Replace ALL placeholder text in the template with the actual content above.
- The company is {company_name}, abbreviated IMCNC.
- Located in Chapel Hill, NC serving Chapel Hill, Durham, Raleigh, Research Triangle.
- Cash-pay integrative medicine practice. Founded by Julie McGregor MD and Will Pendergraft MD PhD.
- Specialty: Integrative/Functional Medicine, Lyme Disease, Mold Illness, Hormone Health, IV Therapy, MedSpa.
- ONLY Low Dose Allergen (LDA) immunotherapy program in North Carolina.
- Use all campaign and email content verbatim from above.
- Keep all slide structure and headings from the original template."""

print(f"Calling Gamma API (template: {TEMPLATE_ID})...")
print(f"Prompt length: {len(prompt)} chars")

headers = {
    "X-API-KEY": api_key,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

payload = {"gammaId": TEMPLATE_ID, "prompt": prompt}

response = requests.post(
    f"{GAMMA_API_BASE}/generations/from-template",
    headers=headers,
    json=payload,
    timeout=180
)

print(f"Response status: {response.status_code}")
if response.status_code not in (200, 201):
    print(f"ERROR: {response.text[:500]}")
    sys.exit(1)

data = response.json()
print(f"Response: {json.dumps(data, indent=2)}")

generation_id = data.get("generationId", "")
gamma_url = None

if generation_id:
    print(f"Polling for URL (generationId: {generation_id})...")
    for attempt in range(30):
        time.sleep(15)
        status_resp = requests.get(
            f"{GAMMA_API_BASE}/generations/{generation_id}",
            headers=headers,
            timeout=30
        )
        if status_resp.status_code == 200:
            status_data = status_resp.json()
            gamma_url = status_data.get("gammaUrl", "")
            gen_status = status_data.get("status", "")
            print(f"  Attempt {attempt+1}: status={gen_status}, url={gamma_url}")
            if gamma_url and gamma_url not in ("unknown", ""):
                data.update({"url": gamma_url, "gammaUrl": gamma_url, "id": generation_id})
                data["credits"] = status_data.get("credits", {})
                break
            elif gen_status == "failed":
                print(f"FAILED: {status_data}")
                sys.exit(1)
    else:
        data["url"] = f"https://gamma.app (pending - generationId: {generation_id})"
        data["id"] = generation_id
        print(f"Timed out - generationId: {generation_id}")

# Save response
response_path = RUN_DIR / "gamma_response.json"
response_path.write_text(json.dumps(data, indent=2))
print(f"Saved to: {response_path}")
print(f"Gamma URL: {data.get('url', 'UNKNOWN')}")

# Slack notification
if slack_webhook and gamma_url:
    msg = {
        "text": f"📊 *Gamma Presentation Created: {company_name}*\n\n🔗 View: {gamma_url}\n📋 Template: `{TEMPLATE_ID}`\n⏱️ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    }
    try:
        requests.post(slack_webhook, json=msg, timeout=10)
        print("Slack notified")
    except Exception as e:
        print(f"Slack error (non-blocking): {e}")

print("DONE")
