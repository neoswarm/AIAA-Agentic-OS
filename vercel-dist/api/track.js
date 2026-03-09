// D100 Open Tracking — Vercel Edge Function
// Fires when a prospect opens their deliverables page.
// Posts a rich notification to Slack #d100-opens.
// The Slack webhook URL lives here server-side — never exposed to the browser.

export const config = { runtime: "edge" };

const SLACK_WEBHOOK = process.env.SLACK_D100_OPENS_WEBHOOK;

// Simple country/city from Vercel geo headers
function geoLabel(req) {
  const city    = req.headers.get("x-vercel-ip-city")    || "";
  const region  = req.headers.get("x-vercel-ip-country-region") || "";
  const country = req.headers.get("x-vercel-ip-country") || "";
  const parts   = [city, region, country].filter(Boolean);
  return parts.length ? parts.join(", ") : "Unknown location";
}

export default async function handler(req) {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      },
    });
  }

  const url      = new URL(req.url);
  const company  = url.searchParams.get("c") || "Unknown Practice";
  const name     = url.searchParams.get("n") || company;        // display name
  const slug     = url.searchParams.get("s") || "";             // company slug
  const geo      = geoLabel(req);
  const ip       = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  const ua       = req.headers.get("user-agent") || "";
  const referer  = req.headers.get("referer")    || "";
  const now      = new Date().toISOString().replace("T", " ").slice(0, 19) + " UTC";

  // Detect bot/crawler — skip Slack notification for bots
  const isBot = /bot|crawl|slurp|spider|preview|facebookexternalhit|linkedinbot|twitterbot|whatsapp/i.test(ua);
  if (isBot) {
    return new Response("ok", { status: 200, headers: { "Access-Control-Allow-Origin": "*" } });
  }

  // Build the live URL
  const liveUrl = slug
    ? `https://healthbizleads.com/${slug}/`
    : `https://healthbizleads.com/`;

  // Slack Block Kit message — rich formatting
  const slackBody = {
    channel: "#d100-opens",
    username: "D100 Open Tracker",
    icon_emoji: ":eyes:",
    blocks: [
      {
        type: "header",
        text: { type: "plain_text", text: "👀 Prospect Opened Report", emoji: true }
      },
      {
        type: "section",
        fields: [
          { type: "mrkdwn", text: `*Practice:*\n${name}` },
          { type: "mrkdwn", text: `*Time:*\n${now}` },
          { type: "mrkdwn", text: `*Location:*\n${geo}` },
          { type: "mrkdwn", text: `*IP:*\n${ip}` }
        ]
      },
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: `*Report URL:* <${liveUrl}|${liveUrl}>`
        }
      },
      { type: "divider" }
    ]
  };

  // Fire and forget — don't block the response
  if (SLACK_WEBHOOK) {
    fetch(SLACK_WEBHOOK, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(slackBody),
    }).catch(() => {});  // swallow errors — don't break tracking
  }

  // Return 1x1 transparent GIF so <img> tags work too
  const gif1x1 = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
  return new Response(Buffer.from(gif1x1, "base64"), {
    status: 200,
    headers: {
      "Content-Type": "image/gif",
      "Cache-Control": "no-store, no-cache, must-revalidate, private",
      "Access-Control-Allow-Origin": "*",
    },
  });
}
