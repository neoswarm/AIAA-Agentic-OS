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