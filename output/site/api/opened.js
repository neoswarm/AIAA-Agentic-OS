// Vercel Serverless Function — fires Slack notification when a D100 report is opened
// Called by JS beacon in report page: /api/opened?slug=...&practice=...
// Suppress by opening URL with ?preview=1 (beacon checks before calling)

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');

  if (req.method === 'OPTIONS') return res.status(200).end();

  const webhook = process.env.SLACK_WEBHOOK_URL;
  if (!webhook) return res.status(200).json({ ok: false, reason: 'no_webhook' });

  const slug     = (req.query.slug     || 'unknown').replace(/[^a-z0-9-]/gi, '');
  const practice = decodeURIComponent(req.query.practice || slug);
  const reportUrl = `https://healthbizleads.com/${slug}/`;
  const ts = new Date().toLocaleString('en-US', {
    timeZone: 'America/Denver', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit', hour12: true
  });

  const payload = {
    text: `👁 Report opened — ${practice}`,
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `👁 *Report Opened*\n*Practice:* ${practice}\n*URL:* <${reportUrl}|${reportUrl}>\n*Time:* ${ts} MT`
        }
      }
    ]
  };

  try {
    await fetch(webhook, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (_) { /* silent — never block the page */ }

  return res.status(200).json({ ok: true });
}
