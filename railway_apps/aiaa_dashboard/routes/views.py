#!/usr/bin/env python3
"""
AIAA Dashboard - Views Blueprint
All page routes for the dashboard interface.
"""

import os
import json
import hashlib
import hmac
import threading
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, current_app
import requests as http_requests

# Import models and config
import models
from config import Config
from workflow_registry import WORKFLOWS


# =============================================================================
# Blueprint Definition
# =============================================================================

views_bp = Blueprint('views', __name__)


# =============================================================================
# Decorator
# =============================================================================

def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('views.login'))
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# Helper Functions
# =============================================================================

def check_password(password: str) -> bool:
    """Check password against configured hash."""
    password_hash = Config.DASHBOARD_PASSWORD_HASH
    
    if not password_hash:
        return False
    
    # Detect bcrypt hash (starts with $2b$)
    if password_hash.startswith("$2b$"):
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except ImportError:
            return False
    
    # Legacy SHA-256 with constant-time comparison
    return hmac.compare_digest(
        hashlib.sha256(password.encode()).hexdigest(),
        password_hash
    )


def send_slack_message(text: str, blocks=None) -> bool:
    """Send a message to Slack via webhook URL."""
    slack_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not slack_url:
        return False
    
    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    
    try:
        resp = http_requests.post(slack_url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def get_base_url():
    """Get base URL for webhooks."""
    return request.host_url.rstrip('/')


def get_username():
    """Get current username from session."""
    return session.get('username', 'Admin')


# =============================================================================
# Authentication Routes
# =============================================================================

@views_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler."""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if username == Config.DASHBOARD_USERNAME and check_password(password):
            session['logged_in'] = True
            session['username'] = username
            session.permanent = True
            
            # Log successful login
            models.log_event(
                event_type="auth",
                status="success",
                data={"username": username, "action": "login"},
                source="web"
            )
            
            return redirect(url_for('views.dashboard'))
        else:
            # Log failed login
            models.log_event(
                event_type="auth",
                status="failed",
                data={"username": username, "action": "login"},
                source="web"
            )
            
            return render_template('login.html', error="Invalid credentials")
    
    # GET request - show login form
    return render_template('login.html')


@views_bp.route('/logout')
def logout():
    """Logout handler."""
    username = session.get('username', 'unknown')
    
    # Log logout
    models.log_event(
        event_type="auth",
        status="success",
        data={"username": username, "action": "logout"},
        source="web"
    )
    
    session.clear()
    return redirect(url_for('views.login'))


# =============================================================================
# Dashboard Pages
# =============================================================================

@views_bp.route('/')
@login_required
def dashboard():
    """Dashboard home page with stats and quick actions."""
    username = get_username()
    
    # Get workflow count
    workflow_count = len(WORKFLOWS)
    
    # Get recent events
    recent_events = models.get_recent_events(limit=5)
    
    # Get execution stats
    execution_stats = models.get_execution_stats()
    
    # Get system health
    import database
    db_health = database.check_health()
    system_health = {
        "database": db_health.get("status", "unknown"),
        "railway_api": "configured" if Config.RAILWAY_API_TOKEN else "not configured",
        "slack": "configured" if os.getenv("SLACK_WEBHOOK_URL") else "not configured"
    }
    
    return render_template(
        'dashboard.html',
        username=username,
        active_page='dashboard',
        workflow_count=workflow_count,
        recent_events=recent_events,
        execution_stats=execution_stats,
        system_health=system_health
    )


@views_bp.route('/workflows')
@login_required
def workflows():
    """Workflow catalog page."""
    username = get_username()
    base_url = get_base_url()
    
    # Get cron workflows from database
    cron_workflows = models.get_workflows(workflow_type='cron')
    
    # Get webhook workflows from database
    webhook_workflows = models.get_workflows(workflow_type='webhook')
    
    # Build workflow list with favorites
    favorites = models.get_favorites()
    
    workflows_list = []
    
    # Add cron workflows
    for wf in cron_workflows:
        workflows_list.append({
            "name": wf['name'],
            "description": wf['description'],
            "type": "cron",
            "status": wf['status'],
            "schedule": wf.get('cron_schedule', 'Not scheduled'),
            "platform": "Railway Cron",
            "is_favorite": wf['name'] in favorites,
            "service_id": wf.get('service_id'),
            "project_id": wf.get('project_id')
        })
    
    # Add webhook workflows
    for wf in webhook_workflows:
        workflows_list.append({
            "name": wf['name'],
            "description": wf['description'],
            "type": "webhook",
            "status": wf['status'],
            "slug": wf.get('webhook_slug'),
            "webhook_url": f"{base_url}/webhook/{wf.get('webhook_slug')}",
            "forward_url": wf.get('forward_url'),
            "slack_notify": bool(wf.get('slack_notify')),
            "is_favorite": wf['name'] in favorites
        })
    
    return render_template(
        'workflow_catalog.html',
        username=username,
        active_page='workflows',
        workflows=workflows_list,
        workflow_registry=WORKFLOWS,
        base_url=base_url
    )


@views_bp.route('/executions')
@login_required
def executions():
    """Execution history page."""
    username = get_username()
    
    # Get executions from database
    limit = request.args.get('limit', 50, type=int)
    workflow_filter = request.args.get('workflow')
    
    execution_list = models.get_executions(workflow_id=workflow_filter, limit=limit)
    
    # Get execution stats
    stats = models.get_execution_stats()
    
    return render_template(
        'execution_history.html',
        username=username,
        active_page='executions',
        executions=execution_list,
        stats=stats
    )


@views_bp.route('/env', methods=['GET', 'POST'])
@login_required
def environment():
    """Environment variable management page."""
    username = get_username()
    
    if request.method == 'POST':
        # Set environment variable
        var_name = request.form.get('var_name')
        var_value = request.form.get('var_value')
        
        if var_name and var_value:
            # Set in current process (runtime only)
            os.environ[var_name] = var_value
            
            # TODO: Persist to Railway API (requires Railway GraphQL mutation)
            # This would be similar to the old app's approach
            
            # Log event
            models.log_event(
                event_type="env_var",
                status="set",
                data={"variable": var_name, "by": username},
                source="web"
            )
            
            # Success message (would normally be flash message)
            return redirect(url_for('views.environment'))
    
    # GET request - show current vars
    tracked_vars = Config.TRACKED_ENV_VARS
    
    env_vars = []
    for var in tracked_vars:
        value = os.getenv(var, "")
        is_set = bool(value)
        
        # Redact sensitive values
        if value and len(value) > 10:
            preview = f"{value[:4]}...{value[-4:]}"
        elif value:
            preview = "***"
        else:
            preview = ""
        
        env_vars.append({
            "name": var,
            "set": is_set,
            "preview": preview
        })
    
    return render_template(
        'env.html',
        username=username,
        active_page='env',
        env_vars=env_vars,
        tracked_vars=tracked_vars
    )


@views_bp.route('/events')
@login_required
def events():
    """Event log page."""
    username = get_username()
    
    # Get events from database
    limit = request.args.get('limit', 100, type=int)
    event_type = request.args.get('type')
    status = request.args.get('status')
    
    if event_type:
        events_list = models.get_events_by_type(event_type, limit=limit)
    elif status:
        events_list = models.get_events_by_status(status, limit=limit)
    else:
        events_list = models.get_events(limit=limit)
    
    # Get event stats
    event_stats = models.count_events_by_status()
    
    return render_template(
        'events.html',
        username=username,
        active_page='events',
        events=events_list,
        event_stats=event_stats
    )


@views_bp.route('/settings/api-keys')
@login_required
def api_keys():
    """API key management page."""
    username = get_username()
    
    # Get API keys from database
    keys = models.list_api_keys()
    
    return render_template(
        'api_keys.html',
        username=username,
        active_page='api-keys',
        api_keys=keys
    )


# =============================================================================
# Webhook Routes
# =============================================================================

@views_bp.route('/webhook/<slug>', methods=['GET', 'POST'])
def webhook_handler(slug):
    """
    Universal webhook endpoint handler.
    Supports both GET (info) and POST (receive).
    """
    if request.method == 'GET':
        # GET - return webhook info
        workflow = models.get_workflow_by_slug(slug)
        
        if not workflow:
            return jsonify({
                "error": "Webhook not found",
                "slug": slug,
                "available_endpoints": "/api/webhook-workflows"
            }), 404
        
        return jsonify({
            "webhook": slug,
            "name": workflow['name'],
            "description": workflow['description'],
            "status": workflow['status'],
            "enabled": workflow['status'] == 'active',
            "webhook_url": f"{get_base_url()}/webhook/{slug}",
            "forward_url": workflow.get('forward_url'),
            "slack_notify": bool(workflow.get('slack_notify')),
            "method": "POST",
            "content_type": "application/json"
        })
    
    # POST - handle webhook
    payload = request.get_json() or {}
    headers = dict(request.headers)
    
    # Log webhook call to database
    webhook_log_id = models.log_webhook_call(
        webhook_slug=slug,
        payload=payload,
        headers=headers
    )
    
    # Get workflow config
    workflow = models.get_workflow_by_slug(slug)
    
    if not workflow:
        models.complete_webhook_log(webhook_log_id, 404, "Webhook not found")
        return jsonify({"error": "Webhook not found", "slug": slug}), 404
    
    if workflow['status'] != 'active':
        models.complete_webhook_log(webhook_log_id, 403, "Webhook disabled")
        return jsonify({"error": "Webhook disabled", "slug": slug}), 403
    
    # Handle webhook
    result = {"status": "received", "webhook": slug, "timestamp": datetime.utcnow().isoformat()}
    
    # Forward to external URL if configured
    forward_url = workflow.get('forward_url')
    if forward_url:
        try:
            resp = http_requests.post(
                forward_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            result["forwarded"] = True
            result["forward_status"] = resp.status_code
            result["forward_response"] = resp.text[:500]  # Truncate
        except Exception as e:
            result["forwarded"] = False
            result["forward_error"] = str(e)
    
    # Send Slack notification if enabled
    if workflow.get('slack_notify'):
        slack_text = f"🔔 Webhook received: `{slug}`\n```{json.dumps(payload, indent=2)[:500]}```"
        send_slack_message(slack_text)
        result["slack_notified"] = True
    
    # Complete webhook log
    models.complete_webhook_log(
        webhook_log_id,
        200,
        json.dumps(result)
    )
    
    # Log event
    models.log_event(
        event_type=f"webhook:{slug}",
        status="success",
        data={"payload_size": len(json.dumps(payload))},
        source="webhook"
    )
    
    return jsonify(result), 200


# =============================================================================
# Health Check
# =============================================================================

@views_bp.route('/health')
def health():
    """Public health check endpoint (no auth required)."""
    import database
    db_health = database.check_health()
    
    return jsonify({
        "status": "healthy" if db_health['status'] == 'healthy' else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "aiaa-dashboard",
        "database": db_health['status'],
        "version": "3.0"
    })


# =============================================================================
# Error Handlers
# =============================================================================

@views_bp.errorhandler(404)
def page_not_found(e):
    """404 error handler."""
    if session.get('logged_in'):
        username = get_username()
        return render_template(
            'error.html',
            username=username,
            active_page=None,
            error_code=404,
            error_message="Page not found"
        ), 404
    else:
        return redirect(url_for('views.login'))


@views_bp.errorhandler(500)
def internal_error(e):
    """500 error handler."""
    if session.get('logged_in'):
        username = get_username()
        return render_template(
            'error.html',
            username=username,
            active_page=None,
            error_code=500,
            error_message="Internal server error"
        ), 500
    else:
        return jsonify({"error": "Internal server error"}), 500
