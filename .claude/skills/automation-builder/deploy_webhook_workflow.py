#!/usr/bin/env python3
"""
Deploy Webhook Workflow to AIAA Dashboard

Registers a new webhook endpoint by calling the live dashboard API.
NO rebuild or redeploy required — the webhook is active immediately.

Usage:
    python3 execution/deploy_webhook_workflow.py --slug stripe --name "Stripe Payments" --description "Processes Stripe payment webhooks" --source Stripe --slack-notify
    python3 execution/deploy_webhook_workflow.py --slug ai-news --name "AI News" --description "Fetches AI news" --source Automation --forward-url https://my-processor.up.railway.app/process
    python3 execution/deploy_webhook_workflow.py --interactive
    python3 execution/deploy_webhook_workflow.py --list
    python3 execution/deploy_webhook_workflow.py --unregister --slug stripe
    python3 execution/deploy_webhook_workflow.py --dry-run --slug test-hook --name "Test" --description "Test webhook" --source Test

How it works:
    POSTs to the live dashboard API at /api/webhook-workflows/register.
    The dashboard updates its in-memory registry instantly — no rebuild needed.
    Config is persisted to WEBHOOK_CONFIG env var for durability across restarts.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Dashboard URL
DASHBOARD_URL = os.getenv(
    "DASHBOARD_URL",
    "https://aiaa-dashboard-production-10fa.up.railway.app"
)

# Session cookie for authenticated requests
# Set via env var or the script will prompt for login
SESSION_COOKIE = os.getenv("DASHBOARD_SESSION", "")


def get_session():
    """Get a session cookie by logging into the dashboard."""
    import urllib.request
    import urllib.parse
    import http.cookiejar

    username = os.getenv("DASHBOARD_USERNAME", "admin")
    password = os.getenv("DASHBOARD_PASSWORD", "")

    if not password:
        import getpass
        password = getpass.getpass(f"Dashboard password for '{username}': ")

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    login_data = urllib.parse.urlencode({
        "username": username,
        "password": password
    }).encode()

    try:
        req = urllib.request.Request(f"{DASHBOARD_URL}/login", data=login_data, method='POST')
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        opener.open(req, timeout=10)

        for cookie in cj:
            if cookie.name == "session":
                return cookie.value
    except Exception as e:
        print(f"  ERROR: Login failed: {e}")

    return None


def api_request(endpoint: str, method: str = "GET", data: dict = None, session: str = "") -> dict:
    """Make an authenticated API request to the dashboard."""
    import urllib.request
    import urllib.error

    url = f"{DASHBOARD_URL}{endpoint}"
    body = json.dumps(data).encode() if data else None

    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if session:
        req.add_header("Cookie", f"session={session}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"status": resp.status, "data": json.loads(resp.read())}
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except Exception:
            body = {"error": str(e)}
        return {"status": e.code, "data": body}
    except Exception as e:
        return {"status": 0, "data": {"error": str(e)}}


def list_webhooks(session: str):
    """List all registered webhooks from live dashboard."""
    result = api_request("/api/webhook-workflows", session=session)
    if result["status"] != 200:
        print(f"  ERROR: {result['data'].get('error', 'Failed to fetch webhooks')}")
        return

    webhooks = result["data"].get("webhook_workflows", [])
    if not webhooks:
        print("  No webhook workflows registered.")
        return

    print(f"\n  Registered webhook workflows ({len(webhooks)}):\n")
    for wh in webhooks:
        status = "ENABLED" if wh.get("enabled") else "DISABLED"
        slack = "Slack ON" if wh.get("slack_notify") else "Slack OFF"
        print(f"    [{status}] /webhook/{wh['slug']}")
        print(f"      Name:   {wh['name']}")
        print(f"      Source:  {wh.get('source', 'Unknown')}")
        print(f"      Desc:   {wh.get('description', 'No description')}")
        print(f"      Slack:  {slack}")
        print(f"      URL:    {wh.get('webhook_url', '')}")
        fwd = wh.get('forward_url', '')
        if fwd:
            print(f"      Fwd:    {fwd}")
        print()


def main():
    global DASHBOARD_URL

    parser = argparse.ArgumentParser(description="Deploy Webhook Workflow to AIAA Dashboard (no rebuild required)")
    parser.add_argument("--slug", "-s", help="Webhook slug (e.g., 'stripe', 'typeform-leads')")
    parser.add_argument("--name", "-n", help="Display name (e.g., 'Stripe Payments')")
    parser.add_argument("--description", "-d", help="What the webhook does")
    parser.add_argument("--source", help="External service name (e.g., 'Stripe', 'Typeform')")
    parser.add_argument("--forward-url", "-f", help="URL to forward webhook payloads to (for custom processing)")
    parser.add_argument("--slack-notify", action="store_true", help="Enable Slack notifications")
    parser.add_argument("--no-slack", action="store_true", help="Disable Slack notifications")
    parser.add_argument("--interactive", "-i", action="store_true", help="Prompt for all values")
    parser.add_argument("--list", "-l", action="store_true", help="List registered webhooks from live dashboard")
    parser.add_argument("--unregister", action="store_true", help="Unregister a webhook (use with --slug)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be sent without doing it")
    parser.add_argument("--dashboard-url", help=f"Dashboard URL (default: {DASHBOARD_URL})")

    args = parser.parse_args()

    if args.dashboard_url:
        DASHBOARD_URL = args.dashboard_url

    print("\n" + "=" * 60)
    print("  AIAA Webhook Workflow Deployment (Live API)")
    print("=" * 60)

    # Authenticate
    print("\n[1/3] Authenticating with dashboard...")
    session = SESSION_COOKIE
    if not session:
        session = get_session()
    if not session:
        print("  ERROR: Could not authenticate. Set DASHBOARD_SESSION or DASHBOARD_PASSWORD env var.")
        return 1
    print("  Authenticated: OK")

    # List mode
    if args.list:
        list_webhooks(session)
        return 0

    # Unregister mode
    if args.unregister:
        slug = args.slug
        if not slug:
            print("ERROR: --slug required with --unregister")
            return 1
        print(f"\n[2/3] Unregistering webhook '{slug}'...")
        result = api_request("/api/webhook-workflows/unregister", method="POST", data={"slug": slug}, session=session)
        if result["status"] in (200, 201):
            print(f"  Unregistered: {result['data'].get('name', slug)}")
        else:
            print(f"  ERROR: {result['data'].get('error', 'Failed')}")
            return 1
        return 0

    # Get webhook details
    if args.interactive:
        slug = input("\n  Webhook slug (lowercase, hyphens): ").strip()
        name = input("  Display name: ").strip()
        description = input("  Description: ").strip()
        source = input("  External service name: ").strip()
        forward_url = input("  Forward URL (leave blank for default handler): ").strip()
        slack_notify = input("  Send Slack notifications? (y/n): ").strip().lower() == 'y'
    else:
        slug = args.slug
        name = args.name
        description = args.description
        source = args.source or "Unknown"
        forward_url = args.forward_url or ""
        slack_notify = args.slack_notify and not args.no_slack

    if not slug or not name or not description:
        print("ERROR: --slug, --name, and --description are required (or use --interactive)")
        return 1

    # Validate slug
    slug = slug.lower().replace(" ", "-")
    if not all(c.isalnum() or c == '-' for c in slug):
        print(f"ERROR: Invalid slug '{slug}'. Use only lowercase letters, numbers, and hyphens.")
        return 1

    payload = {
        "slug": slug,
        "name": name,
        "description": description,
        "source": source,
        "slack_notify": slack_notify
    }
    if forward_url:
        payload["forward_url"] = forward_url

    print(f"\n[2/3] Registering webhook...")
    print(f"  Slug:        {slug}")
    print(f"  Name:        {name}")
    print(f"  Description: {description}")
    print(f"  Source:      {source}")
    print(f"  Slack:       {'Yes' if slack_notify else 'No'}")
    if forward_url:
        print(f"  Forward URL: {forward_url}")

    if args.dry_run:
        print("\n[DRY RUN] Would POST to /api/webhook-workflows/register:")
        print(json.dumps(payload, indent=2))
        print(f"\n  Webhook URL: {DASHBOARD_URL}/webhook/{slug}")
        return 0

    # Register via live API
    result = api_request("/api/webhook-workflows/register", method="POST", data=payload, session=session)

    if result["status"] in (200, 201):
        data = result["data"]
        webhook_url = data.get("webhook_url", f"{DASHBOARD_URL}/webhook/{slug}")
        action = data.get("status", "registered")

        print(f"\n[3/3] Webhook {action}!")
        print("\n" + "=" * 60)
        print(f"  Webhook '{name}' is LIVE — no rebuild needed!")
        print("=" * 60)
        print(f"\n  Webhook URL: {webhook_url}")
        print(f"  Status:      {action.upper()}")
        print(f"  Source:      {source}")
        print(f"  Slack:       {'Enabled' if slack_notify else 'Disabled'}")
        if forward_url:
            print(f"  Forward URL: {forward_url}")
            print(f"  Mode:        FORWARDING (payloads routed to processing service)")
        else:
            print(f"  Mode:        DEFAULT (log + Slack notification)")
        print(f"\n  Next steps:")
        if forward_url:
            print(f"    1. Deploy your processing service to {forward_url}")
            print(f"    2. Configure {source} to send webhooks to: {webhook_url}")
            print(f"    3. Test via dashboard UI or curl:")
        else:
            print(f"    1. Configure {source} to send webhooks to the URL above")
            print(f"    2. Test via dashboard UI (Active Workflows page → Test button)")
            print(f"    3. Or test via curl:")
        print(f'       curl -X POST "{webhook_url}" -H "Content-Type: application/json" -d \'{{"test": true}}\'')
        print("=" * 60 + "\n")
        return 0
    else:
        print(f"\n  ERROR: Registration failed: {result['data'].get('error', 'Unknown error')}")
        print(f"  HTTP Status: {result['status']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
