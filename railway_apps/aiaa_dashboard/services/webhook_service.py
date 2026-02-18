"""
AIAA Dashboard - Webhook Service
Business logic for webhook registration, forwarding, logging, and management.
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    get_workflow_by_slug,
    upsert_workflow,
    log_webhook_call,
    complete_webhook_log,
    get_webhook_logs,
    get_webhook_stats,
    log_event
)
from config import Config

# Import resilience utilities from shared module
try:
    # Try relative import from project root
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from _shared.resilience import retry, with_timeout, graceful_fallback
    _has_resilience = True
except ImportError:
    # Fallback: define simple retry decorator
    import functools
    
    def retry(max_attempts=3, backoff_factor=2.0, exceptions=(Exception,)):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_attempts - 1:
                            raise
                        wait_time = backoff_factor ** attempt
                        print(f"⚠️  Attempt {attempt + 1}/{max_attempts} failed: {e}")
                        print(f"   Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                if last_exception:
                    raise last_exception
            return wrapper
        return decorator
    
    _has_resilience = False


# =============================================================================
# Webhook Configuration Management
# =============================================================================

WEBHOOK_CONFIG_PATH = Path(__file__).parent.parent / "webhook_config.json"


def load_webhook_config() -> Dict[str, Any]:
    """
    Load webhook configuration from database, falling back to webhook_config.json file.
    
    Priority:
    1. Database (models.py) - workflows table
    2. webhook_config.json file seed
    
    Returns:
        Dict with structure: {"webhooks": {slug: {name, description, ...}}}
    """
    webhooks = {}
    
    # Try loading from database first (webhook-type workflows)
    try:
        from models import get_workflows
        db_workflows = get_workflows(workflow_type="webhook", status="active")
        for wf in db_workflows:
            slug = wf.get("webhook_slug")
            if slug:
                webhooks[slug] = {
                    "name": wf.get("name", slug),
                    "description": wf.get("description", f"Webhook: {slug}"),
                    "enabled": wf.get("status") == "active",
                    "source": wf.get("config", {}).get("source", "Unknown") if isinstance(wf.get("config"), dict) else "Unknown",
                    "slack_notify": wf.get("slack_notify", False),
                    "forward_url": wf.get("forward_url", ""),
                    "workflow_id": wf.get("id")
                }
    except Exception as e:
        print(f"⚠️  Could not load webhooks from database: {e}")
    
    # Fallback to file seed if database is empty
    if not webhooks:
        try:
            if WEBHOOK_CONFIG_PATH.exists():
                with open(WEBHOOK_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    webhooks = config.get("webhooks", {})
                    print(f"✅ Loaded {len(webhooks)} webhooks from webhook_config.json seed")
        except Exception as e:
            print(f"⚠️  Error loading webhook_config.json: {e}")
    
    return {"webhooks": webhooks}


def get_webhook_config(slug: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific webhook by slug."""
    config = load_webhook_config()
    return config.get("webhooks", {}).get(slug)


# =============================================================================
# Webhook Request Forwarding
# =============================================================================

@retry(max_attempts=Config.WEBHOOK_RETRY_ATTEMPTS, backoff_factor=Config.WEBHOOK_RETRY_DELAY_SECONDS, exceptions=(requests.RequestException,))
def _forward_with_retry(url: str, payload: Dict, headers: Dict, timeout: int) -> requests.Response:
    """
    Internal function: Forward request to external URL with retry logic.
    
    Uses resilience.py @retry decorator for exponential backoff.
    """
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()  # Raise exception for 4xx/5xx
    return response


def forward_webhook(slug: str, payload: Dict[str, Any], headers: Optional[Dict] = None) -> Tuple[bool, int, str, Optional[str]]:
    """
    Forward webhook payload to configured external URL.
    
    Args:
        slug: Webhook slug identifier
        payload: Original webhook payload
        headers: Optional headers from original request
    
    Returns:
        Tuple of (success, status_code, response_body, error_message)
    
    Behavior:
        - Wraps payload with metadata (slug, timestamp, source)
        - Forwards to configured forward_url with retry logic
        - Handles timeouts gracefully (30s default)
        - Logs all attempts to database
    """
    webhook_config = get_webhook_config(slug)
    
    if not webhook_config:
        return False, 404, "", "Webhook not registered"
    
    forward_url = webhook_config.get("forward_url", "")
    if not forward_url:
        return False, 400, "", "No forward_url configured for this webhook"
    
    # Wrap payload with metadata
    wrapped_payload = {
        "webhook_slug": slug,
        "webhook_name": webhook_config.get("name", slug),
        "source": webhook_config.get("source", "Unknown"),
        "payload": payload,
        "timestamp": datetime.now().isoformat(),
        "headers": headers or {}
    }
    
    # Forward with retry and timeout
    try:
        response = _forward_with_retry(
            forward_url,
            wrapped_payload,
            headers={"Content-Type": "application/json"},
            timeout=Config.WEBHOOK_TIMEOUT_SECONDS
        )
        
        try:
            response_body = response.json()
        except ValueError:
            response_body = response.text[:500]
        
        return True, response.status_code, str(response_body), None
        
    except requests.Timeout:
        error_msg = f"Forward request timed out after {Config.WEBHOOK_TIMEOUT_SECONDS}s"
        return False, 504, "", error_msg
        
    except requests.RequestException as e:
        error_msg = f"Forward request failed: {str(e)}"
        return False, 502, "", error_msg
        
    except Exception as e:
        error_msg = f"Unexpected error during forward: {str(e)}"
        return False, 500, "", error_msg


# =============================================================================
# Webhook Processing & Logging
# =============================================================================

def process_webhook(slug: str, payload: Dict[str, Any], headers: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Process incoming webhook: validate, forward, log, and send notifications.
    
    Args:
        slug: Webhook slug identifier
        payload: Webhook payload
        headers: Request headers
    
    Returns:
        Dict with processing result:
        {
            "status": "success|error|disabled|not_found",
            "webhook": slug,
            "forwarded": bool,
            "forward_status": int (if forwarded),
            "response": Any (if forwarded),
            "error": str (if error),
            "timestamp": str
        }
    """
    # Load webhook config
    webhook_config = get_webhook_config(slug)
    
    # Webhook not registered
    if not webhook_config:
        log_event(f"webhook:{slug}", "error", {"error": "Not registered"}, source="webhook")
        return {
            "status": "not_found",
            "webhook": slug,
            "error": f"Webhook '{slug}' not registered",
            "timestamp": datetime.now().isoformat()
        }
    
    # Webhook disabled
    if not webhook_config.get("enabled", True):
        log_event(f"webhook:{slug}", "warning", {"action": "disabled", "slug": slug}, source="webhook")
        return {
            "status": "disabled",
            "webhook": slug,
            "error": f"Webhook '{slug}' is currently disabled",
            "timestamp": datetime.now().isoformat()
        }
    
    # Log webhook call to database
    webhook_log_id = log_webhook_call(
        webhook_slug=slug,
        payload=payload,
        headers=headers
    )
    
    forward_url = webhook_config.get("forward_url", "")
    
    # Forward webhook if forward_url configured
    if forward_url:
        log_event(f"webhook:{slug}", "info", {"action": "forwarding", "forward_url": forward_url}, source="webhook")
        
        success, status_code, response_body, error = forward_webhook(slug, payload, headers)
        
        # Complete webhook log
        complete_webhook_log(webhook_log_id, status_code, response_body)
        
        if success:
            log_event(f"webhook:{slug}", "success", {"action": "forwarded", "status_code": status_code, "forward_url": forward_url}, source="webhook")
            
            # Send Slack notification if configured
            if webhook_config.get("slack_notify", False):
                _send_webhook_slack_notification(slug, webhook_config, status_code, success=True)
            
            return {
                "status": "success",
                "webhook": slug,
                "forwarded": True,
                "forward_url": forward_url,
                "forward_status": status_code,
                "response": response_body,
                "timestamp": datetime.now().isoformat()
            }
        else:
            log_event(f"webhook:{slug}", "error", {"action": "forward_error", "error": error, "forward_url": forward_url}, source="webhook")
            
            # Send Slack notification for error
            if webhook_config.get("slack_notify", False):
                _send_webhook_slack_notification(slug, webhook_config, status_code, success=False, error=error)
            
            return {
                "status": "error",
                "webhook": slug,
                "forwarded": True,
                "forward_url": forward_url,
                "forward_status": status_code,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
    
    # No forward_url - just log and acknowledge
    complete_webhook_log(webhook_log_id, 200, "Webhook received and logged")
    log_event(f"webhook:{slug}", "success", {"action": "processed", "slug": slug}, source="webhook")
    
    # Send Slack notification if configured
    if webhook_config.get("slack_notify", False):
        _send_webhook_slack_notification(slug, webhook_config, 200, success=True, no_forward=True)
    
    return {
        "status": "success",
        "webhook": slug,
        "forwarded": False,
        "message": "Webhook received and logged",
        "timestamp": datetime.now().isoformat()
    }


def _send_webhook_slack_notification(slug: str, config: Dict, status_code: int, success: bool, error: Optional[str] = None, no_forward: bool = False):
    """Internal: Send Slack notification for webhook event."""
    slack_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not slack_url:
        return
    
    name = config.get("name", slug)
    source = config.get("source", "Unknown")
    
    if no_forward:
        status_text = "✅ Received & Logged"
        message = f"Webhook '{name}' received and logged"
    elif success:
        status_text = f"✅ Forwarded (HTTP {status_code})"
        message = f"Webhook '{name}' forwarded successfully"
    else:
        status_text = f"❌ Error (HTTP {status_code})"
        message = f"Webhook '{name}' forwarding failed"
    
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"Webhook: {name}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Source:* {source}\n*Endpoint:* `/webhook/{slug}`\n*Status:* {status_text}"}}
    ]
    
    if error:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Error:* `{error}`"}})
    
    payload = {"text": message, "blocks": blocks}
    
    try:
        requests.post(slack_url, json=payload, timeout=10)
    except Exception:
        pass  # Gracefully fail Slack notifications


# =============================================================================
# Webhook Registration & Management
# =============================================================================

def register_webhook(
    slug: str,
    name: str,
    description: str = "",
    forward_url: str = "",
    slack_notify: bool = False,
    source: str = "Unknown",
    enabled: bool = True
) -> Dict[str, Any]:
    """
    Register a new webhook or update existing one.
    
    Args:
        slug: Webhook URL slug (lowercase, alphanumeric + hyphens)
        name: Display name
        description: Description
        forward_url: Optional external URL to forward webhooks to
        slack_notify: Send Slack notifications on webhook events
        source: Source system (e.g., "Stripe", "Calendly")
        enabled: Whether webhook is active
    
    Returns:
        Dict with registration result
    """
    # Validate slug
    slug = slug.strip().lower().replace(" ", "-")
    if not slug or not all(c.isalnum() or c == '-' for c in slug):
        return {"error": "Invalid slug. Use lowercase letters, numbers, and hyphens only."}
    
    # Check if webhook already exists
    existing = get_workflow_by_slug(slug)
    workflow_id = existing["id"] if existing else f"webhook-{slug}"
    
    # Create/update webhook workflow in database
    config_dict = {"source": source}
    
    upsert_workflow(
        workflow_id=workflow_id,
        name=name,
        description=description or f"Webhook: {slug}",
        workflow_type="webhook",
        status="active" if enabled else "paused",
        webhook_slug=slug,
        forward_url=forward_url,
        slack_notify=slack_notify,
        config=config_dict
    )
    
    action = "updated" if existing else "registered"
    log_event(f"webhook:{slug}", "success", {"action": action, "name": name, "forward_url": forward_url or None}, source="api")
    
    return {
        "status": action,
        "slug": slug,
        "name": name,
        "webhook_url": f"/webhook/{slug}",
        "forward_url": forward_url or None
    }


def unregister_webhook(slug: str) -> Dict[str, Any]:
    """
    Unregister a webhook (soft delete by setting status to 'deleted').
    
    Args:
        slug: Webhook slug
    
    Returns:
        Dict with unregistration result
    """
    webhook = get_workflow_by_slug(slug)
    
    if not webhook:
        return {"error": f"Webhook '{slug}' not found"}
    
    # Soft delete by setting status to 'deleted'
    from models import delete_workflow
    delete_workflow(webhook["id"])
    
    log_event(f"webhook:{slug}", "info", {"action": "unregistered", "name": webhook.get("name", slug)}, source="api")
    
    return {
        "status": "unregistered",
        "slug": slug,
        "name": webhook.get("name", slug)
    }


def toggle_webhook(slug: str) -> Dict[str, Any]:
    """
    Toggle webhook enabled/disabled state.
    
    Args:
        slug: Webhook slug
    
    Returns:
        Dict with toggle result
    """
    webhook = get_workflow_by_slug(slug)
    
    if not webhook:
        return {"error": f"Webhook '{slug}' not found"}
    
    current_status = webhook.get("status", "active")
    new_status = "paused" if current_status == "active" else "active"
    
    from models import update_workflow_status
    update_workflow_status(webhook["id"], new_status)
    
    log_event(f"webhook:{slug}", "info", {"action": "toggled", "enabled": new_status == "active"}, source="api")
    
    return {
        "slug": slug,
        "enabled": new_status == "active",
        "name": webhook.get("name", slug)
    }


def test_webhook(slug: str, base_url: str = "") -> Dict[str, Any]:
    """
    Send a test payload to a webhook endpoint.
    
    Args:
        slug: Webhook slug
        base_url: Base URL for webhook endpoint
    
    Returns:
        Dict with test result
    """
    webhook = get_workflow_by_slug(slug)
    
    if not webhook:
        return {"error": f"Webhook '{slug}' not found"}
    
    test_payload = {
        "test": True,
        "source": "dashboard_test",
        "timestamp": datetime.now().isoformat(),
        "message": f"Test payload for webhook '{slug}'"
    }
    
    # Process test webhook
    result = process_webhook(slug, test_payload, headers={"X-Test": "true"})
    
    return {
        "slug": slug,
        "test_status": result.get("status"),
        "response": result
    }


# =============================================================================
# Webhook Statistics & Logs
# =============================================================================

def get_webhook_statistics(slug: str) -> Dict[str, Any]:
    """Get statistics for a webhook."""
    return get_webhook_stats(slug)


def get_webhook_recent_logs(slug: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent webhook logs."""
    return get_webhook_logs(slug, limit)


# =============================================================================
# CLI & Testing
# =============================================================================

if __name__ == "__main__":
    """Test webhook service functions."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AIAA Webhook Service CLI")
    parser.add_argument("--register", metavar="SLUG", help="Register a webhook")
    parser.add_argument("--name", help="Webhook name")
    parser.add_argument("--forward-url", help="Forward URL")
    parser.add_argument("--slack-notify", action="store_true", help="Enable Slack notifications")
    parser.add_argument("--test", metavar="SLUG", help="Test a webhook")
    parser.add_argument("--list", action="store_true", help="List all webhooks")
    
    args = parser.parse_args()
    
    if args.register:
        result = register_webhook(
            slug=args.register,
            name=args.name or args.register,
            forward_url=args.forward_url or "",
            slack_notify=args.slack_notify
        )
        print(json.dumps(result, indent=2))
    
    elif args.test:
        result = test_webhook(args.test, base_url="http://localhost:8080")
        print(json.dumps(result, indent=2))
    
    elif args.list:
        config = load_webhook_config()
        print(json.dumps(config, indent=2))
    
    else:
        parser.print_help()
