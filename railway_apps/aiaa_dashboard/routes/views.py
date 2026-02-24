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

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, current_app, flash
import requests as http_requests

# Import models and config
import models
from config import Config
from workflow_registry import WORKFLOWS
from services.skill_execution_service import (
    list_available_skills,
    parse_skill_md,
    get_skill_categories,
    get_execution_status,
    get_skill_count,
)


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


def persist_to_railway(variables: dict):
    """Persist environment variables to Railway via GraphQL API.

    Runs in a background thread. Logs warnings on failure but never raises.
    """
    import logging
    logger = logging.getLogger(__name__)

    api_token = os.getenv('RAILWAY_API_TOKEN', '') or getattr(Config, 'RAILWAY_API_TOKEN', '')
    service_id = os.getenv('RAILWAY_SERVICE_ID', '') or getattr(Config, 'RAILWAY_SERVICE_ID', '')
    environment_id = os.getenv('RAILWAY_ENVIRONMENT_ID', '')
    project_id = os.getenv('RAILWAY_PROJECT_ID', '')

    if not api_token or not service_id:
        logger.warning("Railway persistence skipped: RAILWAY_API_TOKEN or RAILWAY_SERVICE_ID not set")
        return

    endpoint = "https://backboard.railway.app/graphql/v2"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    mutation = """
    mutation variableUpsert($input: VariableUpsertInput!) {
      variableUpsert(input: $input)
    }
    """

    for name, value in variables.items():
        payload = {
            "query": mutation,
            "variables": {
                "input": {
                    "projectId": project_id,
                    "environmentId": environment_id,
                    "serviceId": service_id,
                    "name": name,
                    "value": value,
                }
            },
        }
        try:
            resp = http_requests.post(endpoint, json=payload, headers=headers, timeout=15)
            if resp.status_code != 200:
                logger.warning("Railway variableUpsert for %s returned %s: %s", name, resp.status_code, resp.text[:200])
        except Exception as e:
            logger.warning("Railway variableUpsert for %s failed: %s", name, e)


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
            # Optional session-scoped override applied at login/session creation.
            chat_profile_override = (request.form.get('chat_profile_override') or '').strip()
            if chat_profile_override:
                session['chat_profile_override'] = chat_profile_override
            else:
                session.pop('chat_profile_override', None)
            session.permanent = True
            
            # Log successful login
            models.log_event(
                event_type="auth",
                status="success",
                data={"username": username, "action": "login"},
                source="web"
            )
            
            return redirect(url_for('views.home_v2'))
        else:
            # Log failed login
            models.log_event(
                event_type="auth",
                status="error",
                data={"username": username, "action": "login_failed"},
                source="web"
            )
            
            return render_template('login.html', error="Invalid credentials")
    
    # GET request - redirect to setup if unconfigured
    if not os.getenv('DASHBOARD_PASSWORD_HASH', ''):
        return redirect(url_for('views.setup'))

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


# Password Recovery: To reset, clear DASHBOARD_PASSWORD_HASH in Railway:
# railway variables set DASHBOARD_PASSWORD_HASH=""
# Then visit /setup to set a new password
@views_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """Initial setup page for creating dashboard credentials."""
    password_hash = os.getenv('DASHBOARD_PASSWORD_HASH', '')

    if request.method == 'GET':
        if password_hash:
            flash('Dashboard is already configured. Log in to manage settings.')
            return redirect(url_for('views.login'))
        return render_template('setup.html')

    # POST — create credentials
    if password_hash:
        flash('Dashboard is already configured. Log in to manage settings.')
        return redirect(url_for('views.login'))

    username = request.form.get('username', 'admin').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not password:
        return render_template('setup.html', error='Password is required.')

    if password != confirm_password:
        return render_template('setup.html', error='Passwords do not match.')

    if len(password) < 8:
        return render_template('setup.html', error='Password must be at least 8 characters.')

    # Hash with SHA-256 (matches existing check_password pattern)
    generated_hash = hashlib.sha256(password.encode()).hexdigest()

    # Set in current process environment
    os.environ['DASHBOARD_USERNAME'] = username
    os.environ['DASHBOARD_PASSWORD_HASH'] = generated_hash

    # Persist credentials to Railway in background
    railway_persisted = False
    railway_vars = {
        'DASHBOARD_USERNAME': username,
        'DASHBOARD_PASSWORD_HASH': generated_hash,
        'FLASK_SECRET_KEY': os.getenv('FLASK_SECRET_KEY', ''),
    }
    if os.getenv('RAILWAY_API_TOKEN', '') and os.getenv('RAILWAY_SERVICE_ID', ''):
        railway_persisted = True
        t = threading.Thread(target=persist_to_railway, args=(railway_vars,), daemon=True)
        t.start()

    # Log the setup event
    models.log_event(
        event_type="auth",
        status="success",
        data={"username": username, "action": "setup", "railway_persisted": railway_persisted},
        source="web"
    )

    return render_template('setup.html', success=True, username=username, generated_hash=generated_hash, railway_persisted=railway_persisted)


# =============================================================================
# Dashboard Pages
# =============================================================================

@views_bp.route('/')
@login_required
def dashboard():
    """Root route — redirects to the new home page."""
    return redirect(url_for('views.home_v2'))


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
    favorite_names = models.get_favorites()

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
            "is_favorite": wf['name'] in favorite_names,
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
            "is_favorite": wf['name'] in favorite_names
        })

    # Derive categories from workflow registry
    categories = sorted(set(
        wf.get('category', 'Other') for wf in WORKFLOWS.values()
    ))

    # Build favorites and recent lists for template sections
    favorites = [wf for wf in workflows_list if wf.get('is_favorite')]
    recent_workflows = models.get_recent_executions_workflows(limit=5) if hasattr(models, 'get_recent_executions_workflows') else []

    return render_template(
        'workflow_catalog.html',
        username=username,
        active_page='workflows',
        total_workflows=len(WORKFLOWS),
        categories=categories,
        favorites=favorites,
        recent_workflows=recent_workflows,
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
# V2 Page Routes
# =============================================================================

@views_bp.route('/home')
@login_required
def home_v2():
    """New dashboard home page with skill quick start and recent activity."""
    username = get_username()

    categories = get_skill_categories()
    recent_executions = models.get_recent_skill_executions(limit=10)
    total_skills = get_skill_count()

    return render_template(
        'dashboard_v2.html',
        username=username,
        active_page='home',
        categories=categories,
        recent_executions=recent_executions,
        total_skills=total_skills,
    )


@views_bp.route('/skills')
@login_required
def skill_catalog():
    """Skill catalog page — browse and search all available skills."""
    username = get_username()

    skills = list_available_skills()
    categories = get_skill_categories()
    category_filter = request.args.get('category')

    if category_filter:
        skills = [s for s in skills if s.get('category') == category_filter]

    return render_template(
        'skill_execute.html',
        username=username,
        active_page='skills',
        skills=skills,
        categories=categories,
        category_filter=category_filter,
        total_skills=get_skill_count(),
    )


@views_bp.route('/skills/<skill_name>/run')
@login_required
def skill_run(skill_name):
    """Skill execution form page — shows input form for a specific skill."""
    username = get_username()

    skill = parse_skill_md(skill_name)
    if skill is None:
        return render_template(
            'error_v2.html',
            username=username,
            active_page='skills',
            error_code=404,
            error_message=f"Skill '{skill_name}' not found",
            error_detail="Check the skill name and try again.",
            suggestions=[
                {"text": "Browse all skills", "url": "/skills"},
                {"text": "Go home", "url": "/home"},
            ],
        ), 404

    return render_template(
        'skill_execute.html',
        username=username,
        active_page='skills',
        skill=skill,
        mode='form',
    )


@views_bp.route('/executions/<execution_id>/progress')
@login_required
def execution_progress(execution_id):
    """Execution progress page — shows live status of a running skill."""
    username = get_username()

    execution = get_execution_status(execution_id)
    if execution is None:
        return render_template(
            'error_v2.html',
            username=username,
            active_page='outputs',
            error_code=404,
            error_message="Execution not found",
            error_detail=f"No execution with ID '{execution_id}' was found.",
            suggestions=[
                {"text": "View all outputs", "url": "/outputs"},
                {"text": "Go home", "url": "/home"},
            ],
        ), 404

    skill = parse_skill_md(execution.get('skill_name', ''))

    return render_template(
        'skill_progress.html',
        username=username,
        active_page='outputs',
        execution=execution,
        skill=skill,
    )


@views_bp.route('/executions/<execution_id>/output')
@login_required
def execution_output(execution_id):
    """Execution output viewer page — shows completed skill output."""
    username = get_username()

    execution = get_execution_status(execution_id)
    if execution is None:
        return render_template(
            'error_v2.html',
            username=username,
            active_page='outputs',
            error_code=404,
            error_message="Execution not found",
            error_detail=f"No execution with ID '{execution_id}' was found.",
            suggestions=[
                {"text": "View all outputs", "url": "/outputs"},
                {"text": "Go home", "url": "/home"},
            ],
        ), 404

    # Try to read the output file
    output_content = None
    output_path = execution.get('output_path')
    if output_path:
        from services.skill_execution_service import SKILLS_DIR
        full_path = Path(output_path)
        if not full_path.is_absolute():
            full_path = SKILLS_DIR.parent.parent / output_path
        if full_path.exists():
            output_content = full_path.read_text(encoding='utf-8')

    skill = parse_skill_md(execution.get('skill_name', ''))

    return render_template(
        'skill_output.html',
        username=username,
        active_page='outputs',
        execution=execution,
        skill=skill,
        output_content=output_content,
    )


@views_bp.route('/outputs')
@login_required
def outputs():
    """My Outputs page — list of skill execution history."""
    username = get_username()

    limit = request.args.get('limit', 50, type=int)
    skill_filter = request.args.get('skill')
    status_filter = request.args.get('status')

    execution_list = models.get_skill_executions(
        skill_name=skill_filter,
        status=status_filter,
        limit=limit,
    )
    stats = models.get_skill_execution_stats()

    return render_template(
        'execution_history.html',
        username=username,
        active_page='outputs',
        executions=execution_list,
        stats=stats,
        is_v2=True,
    )


@views_bp.route('/settings')
@login_required
def settings_page():
    """Settings page — API keys, preferences, and profile."""
    username = get_username()

    all_settings = models.get_all_settings()
    preferences = models.get_settings_by_prefix('pref.')

    # Check API key status
    api_key_vars = {
        'openrouter': 'OPENROUTER_API_KEY',
        'perplexity': 'PERPLEXITY_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'openai': 'OPENAI_API_KEY',
        'slack': 'SLACK_WEBHOOK_URL',
        'fal': 'FAL_KEY',
    }
    api_keys_status = {}
    for friendly, env_var in api_key_vars.items():
        value = os.getenv(env_var, '')
        api_keys_status[friendly] = {
            'env_var': env_var,
            'configured': bool(value),
            'redacted': f"{value[:6]}...{value[-4:]}" if value and len(value) > 10 else ('***' if value else ''),
        }

    return render_template(
        'settings.html',
        username=username,
        active_page='settings',
        api_keys_status=api_keys_status,
        preferences=preferences,
        settings=all_settings,
    )


@views_bp.route('/clients-manage')
@login_required
def clients_page():
    """Client management page."""
    username = get_username()

    clients = models.get_all_client_profiles()
    q = request.args.get('q', '').strip()
    if q:
        clients = models.search_client_profiles(q)

    return render_template(
        'clients.html',
        username=username,
        active_page='clients',
        clients=clients,
        search_query=q,
    )


@views_bp.route('/onboarding')
def onboarding():
    """Onboarding flow for first-time users (no login required)."""
    return render_template(
        'onboarding.html',
        active_page='onboarding',
    )


@views_bp.route('/help')
@login_required
def help_page():
    """Help and FAQ page."""
    username = get_username()

    return render_template(
        'help.html',
        username=username,
        active_page='help',
        total_skills=get_skill_count(),
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
        "version": "5.0"
    })


# =============================================================================
# Error Handlers
# =============================================================================

@views_bp.errorhandler(404)
def page_not_found(e):
    """404 error handler using v2 error template."""
    if session.get('logged_in'):
        username = get_username()
        return render_template(
            'error_v2.html',
            username=username,
            active_page=None,
            error_code=404,
        ), 404
    else:
        return redirect(url_for('views.login'))


@views_bp.errorhandler(500)
def internal_error(e):
    """500 error handler using v2 error template."""
    if session.get('logged_in'):
        username = get_username()
        return render_template(
            'error_v2.html',
            username=username,
            active_page=None,
            error_code=500,
            error_message=str(e) if current_app.debug else None,
        ), 500
    else:
        return redirect(url_for('views.login'))
