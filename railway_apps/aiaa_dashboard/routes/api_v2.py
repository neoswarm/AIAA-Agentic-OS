#!/usr/bin/env python3
"""
AIAA Dashboard API v2 Routes
Skill execution, client management, and settings endpoints.
"""

import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from functools import wraps

from flask import Blueprint, request, jsonify, session

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
import models
from services.skill_execution_service import (
    parse_skill_md,
    list_available_skills,
    execute_skill,
    get_execution_status,
    get_skill_categories,
    search_skills,
    get_skill_count,
    get_recommended_skills,
    SKILLS_DIR,
)


api_v2_bp = Blueprint('api_v2', __name__, url_prefix='/api/v2')
_TOKEN_ROTATION_LOCK = threading.Lock()


# =============================================================================
# Validation Helpers
# =============================================================================

def validation_error(errors, message="Validation failed"):
    """Return a structured 400 response with field-level errors.

    Args:
        errors: dict of {field_name: error_message}
        message: summary message

    Returns:
        JSON response with status 400
    """
    return jsonify({
        "status": "error",
        "message": message,
        "errors": errors,
    }), 400


_SENSITIVE_KEY_PATTERN = re.compile(
    r"(token|api[_-]?key|secret|password|authorization|credential)",
    re.IGNORECASE,
)
_TOKEN_VALUE_PATTERNS = [
    re.compile(r"(?i)bearer\s+([A-Za-z0-9._\-]{8,})"),
    re.compile(r"\b(?:sk-or-|pplx-|sk-ant-|sk-|xox[baprs]-|ghp_|github_pat_)[A-Za-z0-9._\-]{8,}\b"),
]


def _redact_value(value):
    """Redact a potentially sensitive token-like value."""
    if not isinstance(value, str):
        return value

    clean = value.strip()
    if not clean:
        return value
    if len(clean) > 10:
        return f"{clean[:6]}...{clean[-4:]}"
    return "***"


def _redact_embedded_tokens(value):
    """Redact token patterns embedded in freeform strings."""
    if not isinstance(value, str) or not value:
        return value

    redacted = value
    for pattern in _TOKEN_VALUE_PATTERNS:
        redacted = pattern.sub(lambda m: _redact_value(m.group(0)), redacted)
    return redacted


def _redact_sensitive_tokens(payload, key_name="", force_redact=False):
    """Recursively redact sensitive token values from API payloads."""
    key_is_sensitive = force_redact or bool(_SENSITIVE_KEY_PATTERN.search(key_name or ""))

    if isinstance(payload, dict):
        return {
            key: _redact_sensitive_tokens(value, key, key_is_sensitive)
            for key, value in payload.items()
        }

    if isinstance(payload, list):
        return [
            _redact_sensitive_tokens(item, key_name, key_is_sensitive)
            for item in payload
        ]

    if isinstance(payload, str):
        if key_is_sensitive:
            return _redact_value(payload)
        return _redact_embedded_tokens(payload)

    return payload


# =============================================================================
# Authentication
# =============================================================================

def login_required(f):
    """Require session login or API key for access."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Session auth
        if session.get('logged_in'):
            return f(*args, **kwargs)
        # API key auth
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == os.getenv('DASHBOARD_API_KEY'):
            return f(*args, **kwargs)
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    return decorated


# =============================================================================
# Skill Endpoints
# =============================================================================

@api_v2_bp.route('/skills', methods=['GET'])
def api_list_skills():
    """List all available skills with parsed metadata."""
    try:
        skills = list_available_skills()
        return jsonify({
            "status": "ok",
            "total": len(skills),
            "skills": skills,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/skills/search', methods=['GET'])
def api_search_skills():
    """Fuzzy search skills by name and description."""
    q = request.args.get('q', '').strip()
    try:
        results = search_skills(q)
        return jsonify({
            "status": "ok",
            "query": q,
            "total": len(results),
            "skills": results,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/skills/categories', methods=['GET'])
def api_skill_categories():
    """Get skills grouped by category."""
    try:
        categories = get_skill_categories()
        return jsonify({
            "status": "ok",
            "categories": categories,
            "total_skills": get_skill_count(),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/skills/recommended', methods=['GET'])
def api_recommended_skills():
    """Get role-based skill recommendations."""
    role = request.args.get('role', '').strip()
    limit = request.args.get('limit', 8, type=int)
    try:
        if not role:
            # Try to get role from user preferences
            try:
                prefs = models.get_settings_by_prefix("pref.")
                role = prefs.get("pref.role", "")
            except Exception:
                role = ""

        skills = get_recommended_skills(role, min(limit, 20))
        return jsonify({
            "status": "ok",
            "role": role,
            "total": len(skills),
            "skills": skills,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/skills/<skill_name>', methods=['GET'])
def api_get_skill(skill_name):
    """Get full detail for a single skill including input spec."""
    try:
        skill = parse_skill_md(skill_name)
        if skill is None:
            return jsonify({"status": "error", "message": f"Skill not found: {skill_name}"}), 404
        return jsonify({"status": "ok", "skill": skill})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/skills/<skill_name>/execute', methods=['POST'])
@login_required
def api_execute_skill(skill_name):
    """Execute a skill with JSON body params. Returns execution ID."""
    data = request.get_json(silent=True) or {}
    params = data.get('params', data)

    # Remove non-param keys if they snuck in
    params.pop('status', None)
    params.pop('skill_name', None)

    # Validate required params against skill metadata
    skill = parse_skill_md(skill_name)
    if skill is None:
        return jsonify({"status": "error", "message": f"Skill not found: {skill_name}"}), 404

    required_inputs = [i for i in (skill.get('inputs') or []) if i.get('required')]
    errors = {}
    for inp in required_inputs:
        field_name = inp.get('name', '')
        if not field_name:
            continue
        value = params.get(field_name)
        # Check if the value is missing or empty
        if value is None or (isinstance(value, str) and not value.strip()):
            label = inp.get('label') or inp.get('display_name') or field_name.replace('-', ' ').replace('_', ' ').title()
            errors[field_name] = f'{label} is required'

    if errors:
        return validation_error(errors, "Missing required fields")

    try:
        execution_id = execute_skill(skill_name, params)
        return jsonify({
            "status": "ok",
            "execution_id": execution_id,
            "message": f"Skill '{skill_name}' execution started",
        }), 202
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/skills/<skill_name>/estimate', methods=['GET'])
@login_required
def api_estimate_skill(skill_name):
    """Get time/cost estimate for a skill (if available)."""
    try:
        skill = parse_skill_md(skill_name)
        if skill is None:
            return jsonify({"status": "error", "message": f"Skill not found: {skill_name}"}), 404

        # Estimate based on number of process steps and known averages
        steps = len(skill.get("process_steps", []))
        estimated_seconds = max(steps * 30, 60)  # ~30s per step, minimum 60s
        estimated_cost = round(steps * 0.05, 2)  # rough estimate

        return jsonify({
            "status": "ok",
            "skill_name": skill_name,
            "estimated_seconds": estimated_seconds,
            "estimated_cost_usd": estimated_cost,
            "steps": steps,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# =============================================================================
# Execution Endpoints
# =============================================================================

@api_v2_bp.route('/executions/<execution_id>/status', methods=['GET'])
@login_required
def api_execution_status(execution_id):
    """Get execution status and partial output."""
    try:
        execution = get_execution_status(execution_id)
        if execution is None:
            return jsonify({"status": "error", "message": "Execution not found"}), 404
        return jsonify({
            "status": "ok",
            "execution": _redact_sensitive_tokens(execution),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/executions/<execution_id>/output', methods=['GET'])
@login_required
def api_execution_output(execution_id):
    """Get full output content by reading the output file."""
    try:
        execution = get_execution_status(execution_id)
        if execution is None:
            return jsonify({"status": "error", "message": "Execution not found"}), 404

        output_content = None
        output_path = execution.get("output_path")

        if output_path:
            # Resolve relative to project root
            full_path = Path(output_path)
            if not full_path.is_absolute():
                project_root = SKILLS_DIR.parent.parent
                full_path = project_root / output_path

            if full_path.exists():
                output_content = full_path.read_text(encoding="utf-8")
        response_payload = {
            "status": "ok",
            "execution": execution,
            "execution_id": execution_id,
            "execution_status": execution.get("status"),
            "skill_name": execution.get("skill_name"),
            "params": execution.get("params"),
            "output_path": output_path,
            "output_content": output_content,
            "output_preview": execution.get("output_preview"),
        }
        return jsonify(_redact_sensitive_tokens(response_payload))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/executions/<execution_id>/deliver/gdocs', methods=['POST'])
@login_required
def api_deliver_gdocs(execution_id):
    """Send execution output to Google Docs via the google-doc-delivery skill."""
    try:
        execution = get_execution_status(execution_id)
        if execution is None:
            return jsonify({"status": "error", "message": "Execution not found"}), 404

        output_path = execution.get("output_path")
        if not output_path:
            return jsonify({"status": "error", "message": "No output file for this execution"}), 400

        # Resolve relative paths to project root (same pattern as api_execution_output)
        full_path = Path(output_path)
        if not full_path.is_absolute():
            project_root = SKILLS_DIR.parent.parent
            full_path = project_root / output_path

        if not full_path.exists():
            return jsonify({"status": "error", "message": "Output file not found"}), 404

        # Call the Google Docs delivery skill
        skill_script = SKILLS_DIR / "google-doc-delivery" / "create_google_doc.py"
        skill_name = execution.get("skill_name", "output")
        result = subprocess.run(
            [sys.executable, str(skill_script),
             "--file", str(full_path),
             "--title", f"{skill_name} - {execution_id[:8]}"],
            capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            return jsonify({
                "status": "error",
                "message": "Google Docs delivery failed",
                "detail": result.stderr[:500],
            }), 500

        # Extract Google Docs URL from stdout
        url = None
        for line in result.stdout.splitlines():
            if 'docs.google.com' in line:
                url = line.strip()
                break

        return jsonify({
            "status": "ok",
            "message": "Delivered to Google Docs",
            "url": url,
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            "status": "error",
            "message": "Google Docs delivery timed out",
        }), 504
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/executions/<execution_id>/cancel', methods=['POST'])
@login_required
def api_cancel_execution(execution_id):
    """Cancel a running or queued execution."""
    try:
        rows = models.cancel_skill_execution(execution_id)
        if rows == 0:
            return jsonify({
                "status": "error",
                "message": "Execution not found or not cancellable",
            }), 404
        return jsonify({
            "status": "ok",
            "message": "Execution cancelled",
            "execution_id": execution_id,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/executions/<execution_id>/retry', methods=['POST'])
@login_required
def api_retry_execution(execution_id):
    """Retry an existing execution using the same skill and parameters."""
    try:
        execution = get_execution_status(execution_id)
        if execution is None:
            return jsonify({"status": "error", "message": "Execution not found"}), 404

        skill_name = execution.get("skill_name")
        if not skill_name:
            return jsonify({"status": "error", "message": "Execution cannot be retried"}), 400

        params = execution.get("params")
        if not isinstance(params, dict):
            params = {}

        new_execution_id = execute_skill(skill_name, params)
        return jsonify({
            "status": "ok",
            "execution_id": new_execution_id,
            "message": "Execution retried",
        }), 202
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/executions', methods=['GET'])
@login_required
def api_list_executions():
    """List recent executions with optional filters."""
    skill_name = request.args.get('skill')
    status = request.args.get('status')
    limit = request.args.get('limit', 50, type=int)

    try:
        executions = models.get_skill_executions(
            skill_name=skill_name,
            status=status,
            limit=min(limit, 200),
        )
        return jsonify({
            "status": "ok",
            "total": len(executions),
            "executions": _redact_sensitive_tokens(executions),
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/executions/stats', methods=['GET'])
@login_required
def api_execution_stats():
    """Get execution statistics."""
    try:
        stats = models.get_skill_execution_stats()
        return jsonify({"status": "ok", "stats": stats})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# =============================================================================
# Settings Endpoints
# =============================================================================

_API_KEY_NAMES = {
    "openrouter": "OPENROUTER_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "slack": "SLACK_WEBHOOK_URL",
    "google": "GOOGLE_APPLICATION_CREDENTIALS",
    "fal": "FAL_KEY",
}

_KEY_PREFIXES = {
    "OPENROUTER_API_KEY": "sk-or-",
    "PERPLEXITY_API_KEY": "pplx-",
    "ANTHROPIC_API_KEY": "sk-ant-",
    "OPENAI_API_KEY": "sk-",
    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/",
    "FAL_KEY": "",
}

_TOKEN_ALIASES = {
    "runner": "DASHBOARD_API_KEY",
    "runner_token": "DASHBOARD_API_KEY",
    "dashboard": "DASHBOARD_API_KEY",
    "dashboard_api_key": "DASHBOARD_API_KEY",
}


def _resolve_env_var(key_name: str) -> str:
    """Resolve a friendly key name to an environment variable."""
    normalized = key_name.lower()
    if normalized in _TOKEN_ALIASES:
        return _TOKEN_ALIASES[normalized]
    return _API_KEY_NAMES.get(normalized, key_name.upper())


def _clear_stored_api_key(env_var: str) -> None:
    """Remove a stored API key/token from settings storage."""
    setting_key = f"api_key.{env_var}"
    delete_setting = getattr(models, "delete_setting", None)
    if callable(delete_setting):
        delete_setting(setting_key)
        return

    # Backward compatibility for older models without delete_setting.
    set_setting = getattr(models, "set_setting", None)
    if callable(set_setting):
        set_setting(setting_key, "")


def _redact_token(token: str) -> str:
    """Redact sensitive token values for API responses."""
    if not token:
        return ""
    if len(token) <= 8:
        return "*" * len(token)
    return f"{token[:4]}...{token[-4:]}"


def _log_token_audit(action: str, status: str, key_name: str, **details) -> None:
    """Best-effort audit logging for token mutations."""
    try:
        data = {"action": action, "key_name": key_name}
        data.update(details)
        models.log_event(
            event_type="token",
            status=status,
            data=data,
            source="api",
        )
    except Exception:
        # Audit logging must not break core token actions.
        pass


@api_v2_bp.route('/settings/api-keys', methods=['POST'])
@login_required
def api_save_api_key():
    """Save an API key to user_settings and set in environment."""
    data = request.get_json(silent=True) or {}
    key_name = data.get('key_name', '').strip()
    key_value = data.get('key_value', '').strip()
    action = (data.get('action') or '').strip().lower()

    # Field-level validation
    errors = {}
    if not key_name:
        errors['key_name'] = 'Key name is required'
    if not key_value and action not in {"validate", "test"}:
        errors['key_value'] = 'API key value is required'

    if errors:
        return validation_error(errors)

    # Resolve env var name
    env_var = _resolve_env_var(key_name)

    # Prefix format validation
    expected_prefix = _KEY_PREFIXES.get(env_var, "")
    if expected_prefix and not key_value.startswith(expected_prefix):
        _log_token_audit(
            action="save",
            status="error",
            key_name=env_var,
            reason="invalid_prefix",
        )
        return validation_error(
            {'key_value': f'Invalid format. {env_var} keys should start with "{expected_prefix}"'},
            "Invalid key format"
        )

    try:
        # Save to user_settings table
        models.set_setting(
            f"api_key.{env_var}",
            key_value,
            validation_status="valid",
            last_error=None,
        )
        # Set in current process environment
        os.environ[env_var] = key_value
        _log_token_audit(
            action="save",
            status="success",
            key_name=env_var,
        )

        return jsonify({
            "status": "ok",
            "message": f"{env_var} saved successfully",
            "key_name": env_var,
        })
    except Exception as e:
        _log_token_audit(
            action="save",
            status="error",
            key_name=env_var,
            reason="exception",
        )
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/settings/api-keys/revoke', methods=['POST'])
@api_v2_bp.route('/settings/api-keys/clear', methods=['POST'])
@api_v2_bp.route('/settings/api-keys/<key_name>', methods=['DELETE'])
@login_required
def api_revoke_api_key(key_name=None):
    """Clear a stored API key/token and remove it from runner environment."""
    data = request.get_json(silent=True) or {}
    requested_key_name = (key_name or data.get('key_name', '')).strip()

    if not requested_key_name:
        return validation_error({'key_name': 'Key name is required'})

    env_var = _resolve_env_var(requested_key_name)

    try:
        _clear_stored_api_key(env_var)
        os.environ.pop(env_var, None)
        _log_token_audit(
            action="revoke",
            status="success",
            key_name=env_var,
        )
        return jsonify({
            "status": "ok",
            "message": f"{env_var} revoked successfully",
            "key_name": env_var,
        })
    except Exception as e:
        _log_token_audit(
            action="revoke",
            status="error",
            key_name=env_var,
            reason="exception",
        )
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/settings/api-keys/<key_name>/rotate', methods=['POST'])
@login_required
def api_rotate_api_key(key_name):
    """Rotate an existing API key/token value."""
    friendly_name = (key_name or '').strip().lower()
    if friendly_name not in _API_KEY_NAMES:
        return validation_error({'key_name': 'Unknown API key name'})

    data = request.get_json(silent=True) or {}
    key_value = data.get('key_value', '').strip()
    if not key_value:
        return validation_error({'key_value': 'API key value is required'})

    env_var = _resolve_api_env_var(friendly_name)
    prefix_error = _validate_api_key_prefix(env_var, key_value)
    if prefix_error:
        return prefix_error

    try:
        models.set_setting(f"api_key.{env_var}", key_value)
        os.environ[env_var] = key_value
        return jsonify({
            "status": "ok",
            "message": f"{env_var} rotated successfully",
            "key_name": env_var,
            "action": "rotate",
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/settings/api-keys/<key_name>/revoke', methods=['POST'])
@login_required
def api_revoke_api_key(key_name):
    """Revoke (remove) an API key/token value."""
    friendly_name = (key_name or '').strip().lower()
    if friendly_name not in _API_KEY_NAMES:
        return validation_error({'key_name': 'Unknown API key name'})

    env_var = _resolve_api_env_var(friendly_name)

    try:
        models.delete_setting(f"api_key.{env_var}")
        os.environ.pop(env_var, None)
        return jsonify({
            "status": "ok",
            "message": f"{env_var} revoked successfully",
            "key_name": env_var,
            "action": "revoke",
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/settings/api-keys/status', methods=['GET'])
@login_required
def api_key_status():
    """Check which API keys are configured and valid."""
    try:
        keys_status = {}
        for friendly_name, env_var in _API_KEY_NAMES.items():
            value = os.getenv(env_var, "") or (models.get_setting(f"api_key.{env_var}", "") or "")
            configured = bool(value)
            metadata = models.get_setting_metadata(setting_key)
            # Redact value for display
            redacted = ""
            if value:
                if len(value) > 10:
                    redacted = f"{value[:6]}...{value[-4:]}"
                else:
                    redacted = "***"

            keys_status[friendly_name] = {
                "env_var": env_var,
                "configured": configured,
                "redacted_value": redacted,
                "last_validated_at": metadata.get("last_validated_at"),
                "validation_status": metadata.get("validation_status"),
                "last_error": metadata.get("last_error"),
            }

        payload = {"status": "ok", "keys": keys_status}
        payload.update(keys_status)
        return jsonify(payload)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/settings/auth-token/rotate', methods=['POST'])
@login_required
def api_rotate_auth_token():
    """Atomically replace DASHBOARD_API_KEY."""
    data = request.get_json(silent=True) or {}
    new_token = data.get('new_token')
    current_token = data.get('current_token')

    errors = {}
    if not isinstance(new_token, str) or not new_token.strip():
        errors['new_token'] = 'New token is required'
    if current_token is not None and not isinstance(current_token, str):
        errors['current_token'] = 'Current token must be a string'

    if errors:
        return validation_error(errors)

    new_token = new_token.strip()
    if current_token is not None:
        current_token = current_token.strip()

    with _TOKEN_ROTATION_LOCK:
        existing_token = os.getenv('DASHBOARD_API_KEY', '')

        # Compare-and-swap check for safe concurrent rotations.
        if current_token is not None and current_token != existing_token:
            _log_token_audit(
                action="rotate",
                status="error",
                key_name="DASHBOARD_API_KEY",
                reason="current_token_mismatch",
            )
            return jsonify({
                "status": "error",
                "message": "Current token does not match",
            }), 409

        if existing_token and existing_token == new_token:
            _log_token_audit(
                action="rotate",
                status="error",
                key_name="DASHBOARD_API_KEY",
                reason="token_unchanged",
            )
            return validation_error(
                {'new_token': 'New token must be different from current token'},
                "Invalid token rotation request"
            )

        os.environ['DASHBOARD_API_KEY'] = new_token

    try:
        set_setting = getattr(models, "set_setting", None)
        if callable(set_setting):
            set_setting("api_key.DASHBOARD_API_KEY", new_token)
    except Exception:
        # Persist failure should not block in-memory rotation.
        pass

    _log_token_audit(
        action="rotate",
        status="success",
        key_name="DASHBOARD_API_KEY",
    )
    return jsonify({
        "status": "ok",
        "message": "DASHBOARD_API_KEY rotated successfully",
        "previous_token": _redact_token(existing_token),
        "active_token": _redact_token(new_token),
    })


@api_v2_bp.route('/settings/preferences', methods=['GET'])
@login_required
def api_get_preferences():
    """Get user preferences."""
    try:
        prefs = models.get_settings_by_prefix("pref.")
        return jsonify({"status": "ok", "preferences": prefs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/settings/preferences', methods=['POST'])
@login_required
def api_save_preferences():
    """Save user preferences."""
    data = request.get_json(silent=True) or {}

    if not isinstance(data, dict):
        return validation_error({'body': 'Request body must be a JSON object'})

    try:
        for key, value in data.items():
            models.set_setting(f"pref.{key}", str(value))
        return jsonify({"status": "ok", "message": "Preferences saved"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/settings/profile', methods=['GET'])
@login_required
def api_get_profile():
    """Get user profile settings."""
    try:
        profile = models.get_settings_by_prefix("profile.")
        return jsonify({"status": "ok", "profile": profile})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/settings/profile', methods=['POST'])
@login_required
def api_save_profile():
    """Save user profile settings."""
    data = request.get_json(silent=True) or {}

    if not isinstance(data, dict):
        return validation_error({'body': 'Request body must be a JSON object'})

    try:
        for key, value in data.items():
            models.set_setting(f"profile.{key}", str(value))
        return jsonify({"status": "ok", "message": "Profile saved"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# =============================================================================
# Client Endpoints
# =============================================================================

def _slugify(name: str) -> str:
    """Convert a name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


@api_v2_bp.route('/clients', methods=['POST'])
@login_required
def api_create_client():
    """Create a new client profile."""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()

    # Field-level validation
    errors = {}
    if not name:
        errors['name'] = 'Client name is required'
    elif len(name) < 2 or len(name) > 100:
        errors['name'] = 'Client name must be between 2 and 100 characters'

    website = data.get('website', '').strip()
    if website and not re.match(r'^https?://.+\..+', website):
        errors['website'] = 'Website must be a valid URL (e.g. https://example.com)'

    industry = data.get('industry', '').strip() if data.get('industry') else ''
    if industry and len(industry) > 100:
        errors['industry'] = 'Industry must be 100 characters or fewer'

    if errors:
        return validation_error(errors)

    slug = _slugify(name)

    # Check for duplicates
    existing = models.get_client_profile(slug)
    if existing:
        return jsonify({"status": "error", "message": f"Client '{name}' already exists"}), 409

    try:
        # Parse rules and preferences as JSON if strings
        rules = data.get('rules')
        if isinstance(rules, str):
            rules = {"raw": rules}
        preferences = data.get('preferences')
        if isinstance(preferences, str):
            preferences = {"raw": preferences}

        client_id = models.create_client_profile(
            name=name,
            slug=slug,
            industry=data.get('industry'),
            website=data.get('website'),
            description=data.get('description'),
            target_audience=data.get('target_audience'),
            goals=data.get('goals'),
            competitors=data.get('competitors'),
            brand_voice=data.get('brand_voice'),
            rules=rules,
            preferences=preferences,
        )

        return jsonify({
            "status": "ok",
            "message": f"Client '{name}' created",
            "client_id": client_id,
            "slug": slug,
        }), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/clients', methods=['GET'])
@login_required
def api_list_clients():
    """List all client profiles."""
    try:
        q = request.args.get('q', '').strip()
        if q:
            clients = models.search_client_profiles(q)
        else:
            clients = models.get_all_client_profiles()
        return jsonify({
            "status": "ok",
            "total": len(clients),
            "clients": clients,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/clients/<slug>', methods=['GET'])
@login_required
def api_get_client(slug):
    """Get a single client profile by slug."""
    try:
        client = models.get_client_profile(slug)
        if client is None:
            return jsonify({"status": "error", "message": f"Client not found: {slug}"}), 404
        payload = {"status": "ok", "client": client}
        payload.update(client)
        return jsonify(payload)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/clients/<slug>', methods=['PUT'])
@login_required
def api_update_client(slug):
    """Update an existing client profile."""
    data = request.get_json(silent=True) or {}

    existing = models.get_client_profile(slug)
    if existing is None:
        return jsonify({"status": "error", "message": f"Client not found: {slug}"}), 404

    # Field-level validation (name is optional on update)
    errors = {}
    name = data.get('name', '').strip()
    if 'name' in data and not name:
        errors['name'] = 'Client name cannot be empty'
    elif name and (len(name) < 2 or len(name) > 100):
        errors['name'] = 'Client name must be between 2 and 100 characters'

    website = data.get('website', '').strip()
    if website and not re.match(r'^https?://.+\..+', website):
        errors['website'] = 'Website must be a valid URL (e.g. https://example.com)'

    industry = data.get('industry', '').strip() if data.get('industry') else ''
    if industry and len(industry) > 100:
        errors['industry'] = 'Industry must be 100 characters or fewer'

    if errors:
        return validation_error(errors)

    try:
        # Parse rules and preferences
        if 'rules' in data and isinstance(data['rules'], str):
            data['rules'] = {"raw": data['rules']}
        if 'preferences' in data and isinstance(data['preferences'], str):
            data['preferences'] = {"raw": data['preferences']}

        models.update_client_profile(slug, **data)
        return jsonify({"status": "ok", "message": f"Client '{slug}' updated"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# =============================================================================
# Error Handlers
# =============================================================================

@api_v2_bp.errorhandler(404)
def api_v2_not_found(e):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404


@api_v2_bp.errorhandler(500)
def api_v2_internal_error(e):
    return jsonify({"status": "error", "message": "Internal server error"}), 500
