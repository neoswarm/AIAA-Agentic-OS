// D100 Open Tracking — Vercel Edge Function
// CRITICAL FIXES:
//   1. await Slack fetch (fire-and-forget is killed before completion in Edge Runtime)
//   2. Buffer.from() replaced with atob()+Uint8Array (Buffer doesn't exist in Edge)
//   3. Removed `channel` field (webhook URL already determines channel)
//   4. Accepts rich browser params from JS beacon: tz, mob, scr, sid, new, lp
// Posts rich notification to Slack #d100-opens.

export const config = { runtime: "edge" };

const SLACK_WEBHOOK = process.env.SLACK_D100_OPENS_WEBHOOK;

// 1x1 transparent GIF — Web API safe (no Buffer)
function gifResponse() {
  const gif  = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
  const bin  = atob(gif);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Response(bytes, {
    status: 200,
    headers: {
      "Content-Type":  "image/gif",
      "Cache-Control": "no-store, no-cache, must-revalidate, private",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

export default async function handler(req) {
  // CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS" },
    });
  }

  // ── Parse params ───────────────────────────────────────────────────────────
  const url     = new URL(req.url);
  const company = decodeURIComponent(url.searchParams.get("c") || "Unknown Practice");
  const name    = decodeURIComponent(url.searchParams.get("n") || company);
  const slug    = url.searchParams.get("s") || "";
  const tz      = url.searchParams.get("tz")  || "—";              // client timezone
  const mobile  = url.searchParams.get("mob") === "1";             // is mobile
  const screen  = url.searchParams.get("scr") || "—";              // WxH pixels
  const sid     = url.searchParams.get("sid") || "—";              // session ID
  const isNew   = url.searchParams.get("new") === "1";             // first visit?
  const landingPage = url.searchParams.get("lp") || "";            // page path

  // ── Server-side info ───────────────────────────────────────────────────────
  const city    = req.headers.get("x-vercel-ip-city")            || "";
  const region  = req.headers.get("x-vercel-ip-country-region")  || "";
  const country = req.headers.get("x-vercel-ip-country")         || "";
  const geo     = [decodeURIComponent(city), region, country].filter(Boolean).join(", ") || "Unknown";
  const ip      = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  const ua      = req.headers.get("user-agent") || "";
  const now     = new Date().toISOString().replace("T", " ").slice(0, 19) + " UTC";

  // ── Preview/owner bypass — ?preview=1 silences Slack ──────────────────────
  if (url.searchParams.get("preview") === "1") return gifResponse();

  // ── Bot filter (narrow — only skip obvious crawlers, not real browsers) ────
  const isBot = /googlebot|bingbot|baiduspider|yandexbot|duckduckbot|sogou|exabot|facebot|ia_archiver|linkedinbot|twitterbot|slackbot|Vercel-Screenshot|Vercel-Preview/i.test(ua);
  if (isBot) return gifResponse();

  // ── Build Slack message ────────────────────────────────────────────────────
  const liveUrl    = slug ? `https://healthbizleads.com/${slug}/` : `https://healthbizleads.com/`;
  const visitEmoji = isNew ? "🆕" : "🔄";
  const visitLabel = isNew ? "First visit" : "Return visit";
  const deviceIcon = mobile ? "📱 Mobile" : "🖥️ Desktop";
  const uaShort    = ua.length > 80 ? ua.slice(0, 80) + "…" : ua;

  const slackBody = {
    blocks: [
      {
        type: "header",
        text: { type: "plain_text", text: `${visitEmoji} Prospect Opened Report`, emoji: true }
      },
      {
        type: "section",
        fields: [
          { type: "mrkdwn", text: `*🏥 Practice:*\n${name}` },
          { type: "mrkdwn", text: `*${visitEmoji} Visit:*\n${visitLabel}` },
        ]
      },
      {
        type: "section",
        fields: [
          { type: "mrkdwn", text: `*🕐 Time (UTC):*\n${now}` },
          { type: "mrkdwn", text: `*🌐 Timezone:*\n${tz}` },
        ]
      },
      {
        type: "section",
        fields: [
          { type: "mrkdwn", text: `*📍 Location:*\n${geo}` },
          { type: "mrkdwn", text: `*🔌 IP:*\n\`${ip}\`` },
        ]
      },
      {
        type: "section",
        fields: [
          { type: "mrkdwn", text: `*${deviceIcon}:*\n${screen}` },
          { type: "mrkdwn", text: `*🆔 Session:*\n\`${sid.slice(0, 16)}\`` },
        ]
      },
      {
        type: "section",
        text: { type: "mrkdwn", text: `*🔗 Report:* <${liveUrl}|${liveUrl}>` }
      },
      {
        type: "context",
        elements: [
          { type: "mrkdwn", text: `UA: ${uaShort}` }
        ]
      },
      { type: "divider" }
    ]
  };

  // ── AWAIT the Slack call so Edge Runtime doesn't kill it ───────────────────
  if (SLACK_WEBHOOK) {
    try {
      await fetch(SLACK_WEBHOOK, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(slackBody),
      });
    } catch (_) {
      // Log error but don't break tracking pixel
    }
  }

  return gifResponse();
}
