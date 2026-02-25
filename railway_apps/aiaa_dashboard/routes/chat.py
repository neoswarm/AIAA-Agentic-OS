#!/usr/bin/env python3
"""
AIAA Dashboard - Chat Blueprint
Chat UI and streaming agent endpoints powered by Claude setup token auth.
"""

from __future__ import annotations

import os
import threading
from functools import wraps
from pathlib import Path
from typing import Any, Dict

import requests as http_requests
from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)

import models
from services.agent_runner import AgentRunner, RunnerError


chat_bp = Blueprint("chat", __name__)

CLAUDE_TOKEN_SETTING_KEY = "claude_setup_token"

_runner_lock = threading.RLock()
_runner: AgentRunner | None = None


def _login_required_page(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("views.login"))
        return f(*args, **kwargs)

    return decorated


def _login_required_api(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return jsonify({"status": "error", "message": "Authentication required"}), 401
        return f(*args, **kwargs)

    return decorated


def _project_root() -> str:
    configured = current_app.config.get("PROJECT_ROOT")
    if configured:
        return str(configured)
    return str(Path(__file__).resolve().parents[3])


def _redact_token(token: str) -> str:
    if not token:
        return ""
    if len(token) <= 10:
        return "***"
    return f"{token[:6]}...{token[-4:]}"


def get_claude_token() -> str:
    """Resolve Claude setup token from env first, then user settings."""
    token = (os.getenv("CLAUDE_SETUP_TOKEN", "") or "").strip()
    if token:
        return token

    stored = (models.get_setting(CLAUDE_TOKEN_SETTING_KEY) or "").strip()
    if stored:
        os.environ["CLAUDE_SETUP_TOKEN"] = stored
    return stored


def validate_claude_token(token: str) -> Dict[str, Any]:
    """Validate token against Anthropic models endpoint."""
    candidate = (token or "").strip()
    if not candidate:
        return {"status": "invalid", "http_status": None, "message": "Missing token"}

    try:
        resp = http_requests.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "Authorization": f"Bearer {candidate}",
                "Accept": "application/json",
            },
            timeout=8,
        )
    except Exception as exc:
        return {
            "status": "unreachable",
            "http_status": None,
            "message": f"Validation check failed: {exc}",
        }

    if resp.status_code == 200:
        return {"status": "valid", "http_status": 200, "message": "Token is valid"}
    if resp.status_code == 401:
        return {"status": "expired", "http_status": 401, "message": "Token is expired or unauthorized"}
    if resp.status_code == 429:
        return {"status": "rate_limited", "http_status": 429, "message": "Token is valid but currently rate-limited"}
    if resp.status_code in (403, 404, 405):
        return {
            "status": "unknown",
            "http_status": resp.status_code,
            "message": "Token could not be conclusively validated on this endpoint",
        }
    return {
        "status": "invalid",
        "http_status": resp.status_code,
        "message": f"Token rejected by validation endpoint ({resp.status_code})",
    }


def _persist_to_railway(variables: Dict[str, str]) -> None:
    """Persist environment variables via Railway GraphQL API."""
    api_token = os.getenv("RAILWAY_API_TOKEN", "")
    service_id = os.getenv("RAILWAY_SERVICE_ID", "")
    environment_id = os.getenv("RAILWAY_ENVIRONMENT_ID", "")
    project_id = os.getenv("RAILWAY_PROJECT_ID", "")

    if not api_token or not service_id:
        return

    endpoint = "https://backboard.railway.app/graphql/v2"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
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
            http_requests.post(endpoint, json=payload, headers=headers, timeout=15)
        except Exception:
            pass


def _persist_to_railway_async(variables: Dict[str, str]) -> bool:
    if not os.getenv("RAILWAY_API_TOKEN") or not os.getenv("RAILWAY_SERVICE_ID"):
        return False
    thread = threading.Thread(target=_persist_to_railway, args=(variables,), daemon=True)
    thread.start()
    return True


def init_chat_runner(app=None) -> AgentRunner:
    """Initialize singleton runner once per process."""
    del app  # app is optional; current_app provides config context.
    global _runner
    with _runner_lock:
        if _runner is None:
            _runner = AgentRunner(
                cwd=_project_root(),
                token_provider=get_claude_token,
            )
        else:
            _runner.cwd = _project_root()
    return _runner


def _get_runner() -> AgentRunner:
    global _runner
    if _runner is None:
        return init_chat_runner()
    return _runner


@chat_bp.route("/chat")
@_login_required_page
def chat_page():
    """Render chat UI page."""
    runner = _get_runner()
    return render_template(
        "chat.html",
        username=session.get("username", "Admin"),
        active_page="chat",
        has_token=bool(get_claude_token()),
        sessions=runner.list_sessions(),
    )


@chat_bp.route("/api/chat/sessions", methods=["GET"])
@_login_required_api
def list_sessions():
    """List current in-memory chat sessions."""
    runner = _get_runner()
    return jsonify({"status": "ok", "sessions": runner.list_sessions()})


@chat_bp.route("/api/chat/sessions/<session_id>", methods=["GET"])
@_login_required_api
def get_session(session_id: str):
    """Get a single session including message history."""
    runner = _get_runner()
    session_obj = runner.get_session(session_id)
    if session_obj is None:
        return jsonify({"status": "error", "message": "Session not found"}), 404
    return jsonify({"status": "ok", "session": session_obj})


@chat_bp.route("/api/chat/sessions", methods=["POST"])
@chat_bp.route("/api/chat/sessions/new", methods=["POST"])
@_login_required_api
def create_session():
    """Create a new chat session."""
    if not get_claude_token():
        return jsonify({"status": "error", "message": "Claude token not configured"}), 400

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip() or None
    runner = _get_runner()
    session_obj = runner.create_session(title=title)
    return jsonify({"status": "ok", "session_id": session_obj["id"], "session": session_obj}), 201


@chat_bp.route("/api/chat/message", methods=["POST"])
@_login_required_api
def send_message():
    """Send a message into an existing chat session."""
    if not get_claude_token():
        return jsonify({"status": "error", "message": "Claude token not configured"}), 400

    payload = request.get_json(silent=True) or {}
    session_id = (payload.get("session_id") or "").strip()
    message = (payload.get("message") or "").strip()

    errors = {}
    if not session_id:
        errors["session_id"] = "session_id is required"
    if not message:
        errors["message"] = "message is required"
    if errors:
        return jsonify({"status": "error", "message": "Validation failed", "errors": errors}), 400

    runner = _get_runner()
    if not runner.has_session(session_id):
        return jsonify({"status": "error", "message": "Session not found"}), 404

    try:
        runner.send_message(session_id=session_id, user_message=message)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except RunnerError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 409
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Failed to send message: {exc}"}), 500

    return jsonify({"status": "ok"}), 202


@chat_bp.route("/api/chat/stream/<session_id>", methods=["GET"])
@_login_required_api
def stream_response(session_id: str):
    """Stream SSE events for a session."""
    runner = _get_runner()
    if not runner.has_session(session_id):
        return jsonify({"status": "error", "message": "Invalid session"}), 404

    response = Response(
        stream_with_context(runner.get_stream(session_id)),
        mimetype="text/event-stream",
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Connection"] = "keep-alive"
    return response


@chat_bp.route("/api/chat/token/status", methods=["GET"])
@_login_required_api
def token_status():
    """Get Claude token configuration state."""
    token = get_claude_token()
    if not token:
        return jsonify(
            {
                "status": "ok",
                "configured": False,
                "validation": "missing",
                "redacted": "",
            }
        )

    validation = validate_claude_token(token)
    return jsonify(
        {
            "status": "ok",
            "configured": True,
            "validation": validation["status"],
            "validation_detail": validation,
            "redacted": _redact_token(token),
        }
    )


@chat_bp.route("/api/chat/token", methods=["POST"])
@_login_required_api
def save_token():
    """Save Claude setup token for chat runner usage."""
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()

    if not token:
        return jsonify({"status": "error", "message": "token is required"}), 400

    validation = validate_claude_token(token)
    if validation["status"] in ("invalid", "expired"):
        return jsonify(
            {
                "status": "error",
                "message": "Claude token validation failed",
                "validation": validation,
            }
        ), 400

    os.environ["CLAUDE_SETUP_TOKEN"] = token
    models.set_setting(CLAUDE_TOKEN_SETTING_KEY, token)
    persisted = _persist_to_railway_async({"CLAUDE_SETUP_TOKEN": token})

    init_chat_runner()

    return jsonify(
        {
            "status": "ok",
            "message": "Claude token saved",
            "validation": validation["status"],
            "validation_detail": validation,
            "persisted_to_railway": persisted,
            "redacted": _redact_token(token),
        }
    )


@chat_bp.route("/api/chat/token/validate", methods=["POST"])
@_login_required_api
def validate_token():
    """Validate a provided token (or the currently stored token) without saving."""
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip() or get_claude_token()

    if not token:
        return jsonify(
            {
                "status": "ok",
                "configured": False,
                "validation": "missing",
                "validation_detail": {"status": "missing", "message": "No token provided"},
            }
        )

    validation = validate_claude_token(token)
    return jsonify(
        {
            "status": "ok",
            "configured": True,
            "validation": validation["status"],
            "validation_detail": validation,
            "redacted": _redact_token(token),
        }
    )
