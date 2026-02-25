#!/usr/bin/env python3
"""
AIAA Dashboard - Chat Blueprint
Chat UI and streaming agent endpoints powered by Claude Agent SDK auth.
"""

from __future__ import annotations

import os
import secrets
import threading
import time
import base64
import json
import logging
from collections import deque
from functools import wraps
from pathlib import Path
from typing import Any, Dict

import requests as http_requests
from flask import (
    Blueprint,
    Response,
    current_app,
    has_app_context,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)

import models
from services.agent_runner import RunnerError
from services.chat_backend import build_chat_runner
from services.chat_store import ChatStore, InMemoryChatStore, RedisChatStore


chat_bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)

CLAUDE_TOKEN_SETTING_KEY = "claude_setup_token"

_runner_lock = threading.RLock()
_runner: Any | None = None
_store_lock = threading.RLock()
_store: ChatStore | None = None
_message_rate_lock = threading.RLock()
_message_rate_windows: dict[str, deque[float]] = {}
GATEWAY_MODE_FLAG = "CHAT_GATEWAY_MODE_ENABLED"


def _get_message_rate_limit_per_minute() -> int:
    raw_value = current_app.config.get(
        "CHAT_MESSAGE_RATE_LIMIT_PER_MINUTE",
        os.getenv("CHAT_MESSAGE_RATE_LIMIT_PER_MINUTE", "20"),
    )
    try:
        return max(1, int(raw_value))
    except (TypeError, ValueError):
        return 20


def _get_message_rate_limit_window_seconds() -> int:
    raw_value = current_app.config.get(
        "CHAT_MESSAGE_RATE_LIMIT_WINDOW_SECONDS",
        os.getenv("CHAT_MESSAGE_RATE_LIMIT_WINDOW_SECONDS", "60"),
    )
    try:
        return max(1, int(raw_value))
    except (TypeError, ValueError):
        return 60


def _get_rate_limit_user_key() -> str:
    username = (session.get("username") or "").strip()
    if username:
        return f"user:{username}"
    if request.remote_addr:
        return f"ip:{request.remote_addr}"
    return "ip:unknown"


def _check_user_message_rate_limit() -> tuple[bool, int, int, int]:
    """Return (allowed, retry_after_seconds, limit, window_seconds)."""
    limit = _get_message_rate_limit_per_minute()
    window_seconds = _get_message_rate_limit_window_seconds()
    now = time.monotonic()
    user_key = _get_rate_limit_user_key()

    with _message_rate_lock:
        history = _message_rate_windows.setdefault(user_key, deque())
        cutoff = now - window_seconds
        while history and history[0] <= cutoff:
            history.popleft()

        if len(history) >= limit:
            retry_after = max(1, int(history[0] + window_seconds - now))
            return False, retry_after, limit, window_seconds

        history.append(now)

    return True, 0, limit, window_seconds


def _reset_message_rate_limits() -> None:
    """Testing helper to clear in-memory rate-limit state."""
    with _message_rate_lock:
        _message_rate_windows.clear()


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
            return (
                jsonify({"status": "error", "message": "Authentication required"}),
                401,
            )
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
    """Resolve Claude auth token from env first, then user settings."""
    token = (os.getenv("CLAUDE_SETUP_TOKEN", "") or "").strip()
    if token:
        return token

    stored = (models.get_setting(CLAUDE_TOKEN_SETTING_KEY) or "").strip()
    if stored:
        os.environ["CLAUDE_SETUP_TOKEN"] = stored
    return stored


def _decode_base64url_json(segment: str) -> dict[str, Any] | None:
    """Decode a base64url segment to JSON object, returning None on failure."""
    try:
        padded = segment + ("=" * ((4 - len(segment) % 4) % 4))
        raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
        payload = json.loads(raw.decode("utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        return None
    return None


def _looks_like_setup_token(token: str) -> bool:
    """Heuristic for Claude setup tokens from CLI setup/auth flows."""
    normalized = (token or "").strip()
    # Claude setup-token values currently use an oat prefix.
    if normalized.startswith("sk-ant-oat"):
        return True

    parts = token.split(".")
    if len(parts) != 3:
        return False

    header = _decode_base64url_json(parts[0])
    claims = _decode_base64url_json(parts[1])
    if not header or not claims:
        return False
    return True


def _unsupported_setup_token_message() -> str:
    return "Gateway mode is disabled. Use an Anthropic API key (sk-ant-...) instead."


def _is_gateway_mode_enabled() -> bool:
    """Return whether setup-token gateway mode is enabled via feature flag."""
    raw_value = (os.getenv(GATEWAY_MODE_FLAG, "false") or "").strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def _chat_backend() -> str:
    if has_app_context():
        configured = (current_app.config.get("CHAT_BACKEND") or "").strip()
        if configured:
            return configured.lower()
    return (os.getenv("CHAT_BACKEND", "") or "").strip().lower()


def _is_setup_token_hard_blocked() -> bool:
    if _is_gateway_mode_enabled():
        return False
    return _chat_backend() != "gateway"


def validate_claude_token(token: str) -> Dict[str, Any]:
    """Validate Claude token with compatible checks.

    setup-token / OAuth artifacts are only accepted when gateway mode is enabled,
    either via feature flag or gateway backend.
    """
    candidate = (token or "").strip()
    if not candidate:
        return {"status": "invalid", "http_status": None, "message": "Missing token"}

    if _looks_like_setup_token(candidate) and _is_setup_token_hard_blocked():
        return {
            "status": "unsupported",
            "http_status": None,
            "message": _unsupported_setup_token_message(),
        }
    if _looks_like_setup_token(candidate):
        return {
            "status": "unknown",
            "http_status": None,
            "message": "Setup token accepted for gateway mode; direct Anthropic validation skipped.",
        }

    headers = {"Accept": "application/json"}
    if candidate.startswith("sk-ant-"):
        headers["x-api-key"] = candidate
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["Authorization"] = f"Bearer {candidate}"

    try:
        resp = http_requests.get(
            "https://api.anthropic.com/v1/models",
            headers=headers,
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
        return {
            "status": "expired",
            "http_status": 401,
            "message": "Token is expired or unauthorized",
        }
    if resp.status_code == 429:
        return {
            "status": "rate_limited",
            "http_status": 429,
            "message": "Token is valid but currently rate-limited",
        }
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
            http_requests.post(endpoint, json=payload, headers=headers, timeout=15)
        except Exception:
            pass


def _persist_to_railway_async(variables: Dict[str, str]) -> bool:
    if not os.getenv("RAILWAY_API_TOKEN") or not os.getenv("RAILWAY_SERVICE_ID"):
        return False
    thread = threading.Thread(
        target=_persist_to_railway, args=(variables,), daemon=True
    )
    thread.start()
    return True


def _derive_title(message: str) -> str:
    first_line = (message or "").strip().splitlines()[0] if message else "New chat"
    return (first_line[:57] + "...") if len(first_line) > 60 else first_line


def _request_ip_address() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or ""


def _log_token_lifecycle(action: str, status: str, **details: Any) -> None:
    payload: Dict[str, Any] = {
        "event": "token_lifecycle",
        "action": action,
        "status": status,
        "username": session.get("username", "unknown"),
        "ip": _request_ip_address(),
        "method": request.method,
        "path": request.path,
    }
    payload.update(details)
    logger.info(json.dumps(payload, sort_keys=True))


def _log_chat_session_lifecycle(
    action: str, status: str, session_id: str = "", **details: Any
) -> None:
    payload: Dict[str, Any] = {
        "event": "chat_session_lifecycle",
        "action": action,
        "status": status,
        "session_id": session_id,
        "username": session.get("username", "unknown"),
        "ip": _request_ip_address(),
        "method": request.method,
        "path": request.path,
    }
    payload.update(details)
    logger.info(json.dumps(payload, sort_keys=True))


def init_chat_store(app=None) -> ChatStore:
    """Initialize singleton chat store once per process."""
    del app
    global _store
    with _store_lock:
        if _store is not None:
            return _store

        redis_url = (os.getenv("REDIS_URL") or "").strip()
        key_prefix = (os.getenv("CHAT_STORE_PREFIX") or "aiaa:dashboard:chat").strip()
        if not key_prefix:
            key_prefix = "aiaa:dashboard:chat"

        if redis_url:
            try:
                _store = RedisChatStore.from_url(redis_url, key_prefix=key_prefix)
            except Exception:
                _store = InMemoryChatStore()
        else:
            _store = InMemoryChatStore()
    return _store


def _get_chat_store() -> ChatStore:
    global _store
    if _store is None:
        return init_chat_store()
    return _store


def init_chat_runner(app=None):
    """Initialize singleton runner once per process."""
    del app  # app is optional; current_app provides config context.
    global _runner
    store = _get_chat_store()
    with _runner_lock:
        if _runner is None:
            _runner = build_chat_runner(
                cwd=_project_root(),
                token_provider=get_claude_token,
                session_store=store,
            )
        else:
            if hasattr(_runner, "cwd"):
                _runner.cwd = _project_root()
            if hasattr(_runner, "attach_store"):
                _runner.attach_store(store)
    return _runner


def _get_runner():
    global _runner
    if _runner is None:
        return init_chat_runner()
    return _runner


@chat_bp.route("/chat")
@_login_required_page
def chat_page():
    """Render chat UI page."""
    store = _get_chat_store()
    return render_template(
        "chat.html",
        username=session.get("username", "Admin"),
        active_page="chat",
        has_token=bool(get_claude_token()),
        sessions=store.list_sessions(),
    )


@chat_bp.route("/api/chat/sessions", methods=["GET"])
@_login_required_api
def list_sessions():
    """List current chat sessions from store."""
    store = _get_chat_store()
    return jsonify({"status": "ok", "sessions": store.list_sessions()})


@chat_bp.route("/api/chat/sessions/<session_id>", methods=["GET"])
@_login_required_api
def get_session(session_id: str):
    """Get a single session including message history."""
    store = _get_chat_store()
    session_obj = store.get_session(session_id)
    if session_obj is None:
        return jsonify({"status": "error", "message": "Session not found"}), 404
    session_obj = dict(session_obj)
    session_obj["messages"] = store.get_messages(session_id)
    return jsonify({"status": "ok", "session": session_obj})


@chat_bp.route("/api/chat/sessions", methods=["POST"])
@chat_bp.route("/api/chat/sessions/new", methods=["POST"])
@_login_required_api
def create_session():
    """Create a new chat session."""
    token = get_claude_token()
    if not token:
        _log_chat_session_lifecycle(
            action="create",
            status="error",
            reason="token_missing",
        )
        return (
            jsonify({"status": "error", "message": "Claude token not configured"}),
            400,
        )
    if _looks_like_setup_token(token) and _is_setup_token_hard_blocked():
        _log_chat_session_lifecycle(
            action="create",
            status="error",
            reason="token_unsupported",
        )
        return (
            jsonify({"status": "error", "message": _unsupported_setup_token_message()}),
            400,
        )

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip() or "New chat"
    session_id = secrets.token_hex(16)
    store = _get_chat_store()
    session_obj = store.create_session(session_id, title=title, status="idle")
    runner = _get_runner()
    runner.ensure_session(
        session_obj["id"],
        title=session_obj.get("title"),
        sdk_session_id=session_obj.get("sdk_session_id"),
    )
    _log_chat_session_lifecycle(
        action="create",
        status="success",
        session_id=session_obj["id"],
    )
    return (
        jsonify(
            {"status": "ok", "session_id": session_obj["id"], "session": session_obj}
        ),
        201,
    )


@chat_bp.route("/api/chat/message", methods=["POST"])
@_login_required_api
def send_message():
    """Send a message into an existing chat session."""
    token = get_claude_token()
    if not token:
        _log_chat_session_lifecycle(
            action="send_message",
            status="error",
            reason="token_missing",
        )
        return (
            jsonify({"status": "error", "message": "Claude token not configured"}),
            400,
        )
    if _looks_like_setup_token(token) and _is_setup_token_hard_blocked():
        _log_chat_session_lifecycle(
            action="send_message",
            status="error",
            reason="token_unsupported",
        )
        return (
            jsonify({"status": "error", "message": _unsupported_setup_token_message()}),
            400,
        )

    payload = request.get_json(silent=True) or {}
    session_id = (payload.get("session_id") or "").strip()
    message = (payload.get("message") or "").strip()

    errors = {}
    if not session_id:
        errors["session_id"] = "session_id is required"
    if not message:
        errors["message"] = "message is required"
    if errors:
        _log_chat_session_lifecycle(
            action="send_message",
            status="error",
            session_id=session_id,
            reason="validation_failed",
        )
        return (
            jsonify(
                {"status": "error", "message": "Validation failed", "errors": errors}
            ),
            400,
        )

    store = _get_chat_store()
    session_obj = store.get_session(session_id)
    if session_obj is None:
        _log_chat_session_lifecycle(
            action="send_message",
            status="error",
            session_id=session_id,
            reason="session_not_found",
        )
        return jsonify({"status": "error", "message": "Session not found"}), 404

    allowed, retry_after, limit, window_seconds = _check_user_message_rate_limit()
    if not allowed:
        _log_chat_session_lifecycle(
            action="send_message",
            status="rate_limited",
            session_id=session_id,
            retry_after_seconds=retry_after,
        )
        response = jsonify(
            {
                "status": "error",
                "error_code": "rate_limited",
                "message": "Too many messages. Please wait before sending another message.",
                "retry_after_seconds": retry_after,
                "limit": limit,
                "window_seconds": window_seconds,
            }
        )
        response.headers["Retry-After"] = str(retry_after)
        return response, 429

    session_updates: Dict[str, Any] = {"status": "running", "last_error": None}
    if (session_obj.get("title") or "New chat") == "New chat":
        session_updates["title"] = _derive_title(message)

    try:
        store.append_message(
            session_id,
            {
                "role": "user",
                "content": message,
                "type": "message",
                "metadata": {},
            },
            session_updates=session_updates,
        )
        runner = _get_runner()
        runner.ensure_session(
            session_id,
            title=session_updates.get("title") or session_obj.get("title"),
            sdk_session_id=session_obj.get("sdk_session_id"),
        )
        runner.send_message(session_id=session_id, user_message=message)
    except ValueError as exc:
        store.update_session(session_id, {"status": "idle", "last_error": str(exc)})
        _log_chat_session_lifecycle(
            action="send_message",
            status="error",
            session_id=session_id,
            reason="validation_error",
        )
        return jsonify({"status": "error", "message": str(exc)}), 400
    except RunnerError as exc:
        store.update_session(session_id, {"status": "error", "last_error": str(exc)})
        _log_chat_session_lifecycle(
            action="send_message",
            status="error",
            session_id=session_id,
            reason="runner_error",
        )
        return jsonify({"status": "error", "message": str(exc)}), 409
    except Exception as exc:
        store.update_session(
            session_id,
            {"status": "error", "last_error": f"Failed to send message: {exc}"},
        )
        _log_chat_session_lifecycle(
            action="send_message",
            status="error",
            session_id=session_id,
            reason="unexpected_error",
        )
        return (
            jsonify({"status": "error", "message": f"Failed to send message: {exc}"}),
            500,
        )

    _log_chat_session_lifecycle(
        action="send_message",
        status="accepted",
        session_id=session_id,
        message_length=len(message),
    )
    return jsonify({"status": "ok"}), 202


@chat_bp.route("/api/chat/stream/<session_id>", methods=["GET"])
@_login_required_api
def stream_response(session_id: str):
    """Stream SSE events for a session."""
    store = _get_chat_store()
    session_obj = store.get_session(session_id)
    if session_obj is None:
        _log_chat_session_lifecycle(
            action="stream",
            status="error",
            session_id=session_id,
            reason="session_not_found",
        )
        return jsonify({"status": "error", "message": "Invalid session"}), 404

    runner = _get_runner()
    if not runner.has_session(session_id):
        runner.ensure_session(
            session_id,
            title=session_obj.get("title"),
            sdk_session_id=session_obj.get("sdk_session_id"),
        )
    _log_chat_session_lifecycle(action="stream", status="opened", session_id=session_id)

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
        _log_token_lifecycle(
            action="status",
            status="missing",
            configured=False,
            validation="missing",
            redacted="",
        )
        return jsonify(
            {
                "status": "ok",
                "configured": False,
                "validation": "missing",
                "redacted": "",
            }
        )

    validation = validate_claude_token(token)
    _log_token_lifecycle(
        action="status",
        status="success",
        configured=True,
        validation=validation["status"],
        redacted=_redact_token(token),
    )
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
    """Save Claude auth token for chat runner usage."""
    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()

    if not token:
        _log_token_lifecycle(
            action="save",
            status="error",
            reason="missing_token",
            validation="missing",
            redacted="",
        )
        return jsonify({"status": "error", "message": "token is required"}), 400

    validation = validate_claude_token(token)
    if validation["status"] in ("invalid", "expired", "unsupported"):
        _log_token_lifecycle(
            action="save",
            status="error",
            reason="validation_failed",
            validation=validation["status"],
            redacted=_redact_token(token),
        )
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Claude token validation failed",
                    "validation": validation,
                }
            ),
            400,
        )

    os.environ["CLAUDE_SETUP_TOKEN"] = token
    models.set_setting(CLAUDE_TOKEN_SETTING_KEY, token)
    persisted = _persist_to_railway_async({"CLAUDE_SETUP_TOKEN": token})

    init_chat_runner()

    _log_token_lifecycle(
        action="save",
        status="success",
        validation=validation["status"],
        persisted_to_railway=persisted,
        redacted=_redact_token(token),
    )

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
        _log_token_lifecycle(
            action="validate",
            status="missing",
            configured=False,
            validation="missing",
            redacted="",
        )
        return jsonify(
            {
                "status": "ok",
                "configured": False,
                "validation": "missing",
                "validation_detail": {
                    "status": "missing",
                    "message": "No token provided",
                },
            }
        )

    validation = validate_claude_token(token)
    _log_token_lifecycle(
        action="validate",
        status="success",
        configured=True,
        validation=validation["status"],
        redacted=_redact_token(token),
    )
    return jsonify(
        {
            "status": "ok",
            "configured": True,
            "validation": validation["status"],
            "validation_detail": validation,
            "redacted": _redact_token(token),
        }
    )
