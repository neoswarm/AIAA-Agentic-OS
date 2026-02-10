#!/usr/bin/env python3
"""
Modal Slack Test - Minimal webhook that forwards POST data to Slack.

Verifies the Modal -> Slack pipeline works end-to-end.

Usage (local test):
    python3 execution/modal_slack_test.py --test --message "Hello from local"

Deploy to Modal:
    modal deploy execution/modal_slack_test.py

Test deployed webhook:
    curl -X POST https://<your-endpoint>/webhook \
      -H "Content-Type: application/json" \
      -d '{"message": "test from modal"}'
"""

import argparse
import json
import os
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Not needed on Modal -- env vars injected via secrets

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


def send_slack_message(text: str) -> bool:
    """Send a message to Slack via webhook."""
    if not SLACK_WEBHOOK_URL:
        print(f"[NO SLACK WEBHOOK] {text}")
        return False

    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"Slack error: {e}")
        return False


def handle_webhook(payload: dict) -> dict:
    """Process incoming webhook payload and send to Slack."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    if "message" in payload:
        text = payload["message"]
    else:
        text = f"Webhook received:\n```{json.dumps(payload, indent=2)}```"

    slack_text = f"*Modal Webhook* ({timestamp})\n{text}"
    success = send_slack_message(slack_text)

    return {
        "status": "sent" if success else "failed",
        "timestamp": timestamp,
        "slack_delivered": success,
    }


# =============================================================================
# Modal Deployment
# =============================================================================

try:
    import modal

    app = modal.App("slack-test")
    image = modal.Image.debian_slim().pip_install("requests", "fastapi")

    @app.function(
        image=image,
        secrets=[modal.Secret.from_name("slack-webhook")],
        timeout=30,
    )
    @modal.fastapi_endpoint(method="POST")
    def webhook(payload: dict):
        """Receive POST data and forward to Slack."""
        return handle_webhook(payload)

    @app.function(image=image)
    @modal.fastapi_endpoint(method="GET")
    def health():
        """Health check."""
        return {"status": "ok", "service": "slack-test"}

except ImportError:
    pass


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Modal Slack Test")
    parser.add_argument("--test", action="store_true", help="Send a test message")
    parser.add_argument("--message", default="Test from modal_slack_test.py", help="Message to send")
    args = parser.parse_args()

    if args.test:
        result = handle_webhook({"message": args.message})
        print(json.dumps(result, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
