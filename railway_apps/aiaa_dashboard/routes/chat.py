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
from services.chat_runner import ChatRunnerBackend, RunnerError, create_chat_runner
from services.chat_store import ChatStore, InMemoryChatStore, RedisChatStore
from services.gateway_client import GatewayClient, GatewayClientError, GatewayHTTPError


chat_bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)

CLAUDE_TOKEN_SETTING_KEY = "claude_setup_token"
CLAUDE_TOKEN_PROFILE_ID = "default"

_runner_lock = threading.RLock()
_runner: ChatRunnerBackend | None = None
_store_lock = threading.RLock()
_store: ChatStore | None = None
_message_rate_lock = threading.RLock()
_message_rate_windows: dict[str, deque[float]] = {}
_token_rotate_lock = threading.RLock()
GATEWAY_MODE_FLAG = "CHAT_GATEWAY_MODE_ENABLED"
DEFAULT_GATEWAY_PROFILE_ID = "default"
_PROFILE_STATUS_VALUES = {"active", "inactive", "revoked"}
_GATEWAY_VALIDATION_MESSAGES = {
    "valid": "Gateway runtime canary succeeded",
    "invalid": "Gateway runtime canary failed",
    "runtime_unavailable": "Claude runtime is not installed on this host",
    "runtime_error": "Gateway runtime canary crashed",
    "timeout": "Gateway runtime canary timed out",
}


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


def _api_key_authorized() -> bool:
    expected_key = (os.getenv("DASHBOARD_API_KEY") or "").strip()
    if not expected_key:
        return False

    provided_key = (request.headers.get("X-API-Key") or "").strip()
    if provided_key and secrets.compare_digest(provided_key, expected_key):
        return True

    auth_header = (request.headers.get("Authorization") or "").strip()
    if auth_header.lower().startswith("bearer "):
        bearer = auth_header[7:].strip()
        if bearer and secrets.compare_digest(bearer, expected_key):
            return True

    return False


def _login_or_api_key_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("logged_in") or _api_key_authorized():
            return f(*args, **kwargs)
        response = jsonify({"error": {"message": "Authentication required"}})
        response.status_code = 401
        response.headers["WWW-Authenticate"] = "Bearer"
        return response

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


def _gateway_profile_config() -> tuple[str, str]:
    base_url = (
        current_app.config.get("GATEWAY_BASE_URL")
        or os.getenv("GATEWAY_BASE_URL", "")
    ).strip()
    api_key = (
        current_app.config.get("GATEWAY_API_KEY")
        or os.getenv("GATEWAY_API_KEY", "")
    ).strip()
    return base_url.rstrip("/"), api_key


def _should_use_gateway_profile_api() -> bool:
    base_url, api_key = _gateway_profile_config()
    return _chat_backend() == "gateway" and bool(base_url and api_key)


def _build_gateway_client() -> GatewayClient:
    base_url, api_key = _gateway_profile_config()
    if not base_url or not api_key:
        raise RuntimeError(
            "Gateway profile API is unavailable. Set GATEWAY_BASE_URL and GATEWAY_API_KEY."
        )
    return GatewayClient(base_url, api_key=api_key, timeout_seconds=10.0)


def _upsert_gateway_profile(profile_id: str, token: str) -> dict[str, Any]:
    body = _build_gateway_client().post_json(
        "/v1/profiles/upsert",
        payload={"profile_id": profile_id, "token": token},
    )
    if not isinstance(body, dict):
        raise RuntimeError("Gateway upsert response must be a JSON object.")
    return body


def _validate_gateway_profile(profile_id: str, token: str) -> dict[str, Any]:
    body = _build_gateway_client().post_json(
        "/v1/profiles/validate",
        payload={"profile_id": profile_id, "token": token},
    )
    if not isinstance(body, dict):
        raise RuntimeError("Gateway validate response must be a JSON object.")
    return body


def _revoke_gateway_profile(profile_id: str) -> dict[str, Any]:
    body = _build_gateway_client().post_json(
        "/v1/profiles/revoke",
        payload={"profile_id": profile_id},
    )
    if not isinstance(body, dict):
        raise RuntimeError("Gateway revoke response must be a JSON object.")
    status = str(body.get("status") or "").strip().lower()
    if status != "ok" or body.get("revoked") is False:
        raise RuntimeError("Gateway did not confirm profile revoke.")
    return body


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


def _gateway_base_url() -> str:
    if has_app_context():
        configured = (current_app.config.get("GATEWAY_BASE_URL") or "").strip()
        if configured:
            return configured
    return (os.getenv("GATEWAY_BASE_URL", "") or "").strip()


def _gateway_api_key() -> str:
    if has_app_context():
        configured = (current_app.config.get("GATEWAY_API_KEY") or "").strip()
        if configured:
            return configured
    return (os.getenv("GATEWAY_API_KEY", "") or "").strip()


def _normalize_gateway_status(raw_status: Any) -> str | None:
    normalized = str(raw_status or "").strip().lower()
    return normalized or None


def _extract_gateway_profile_status(payload: Dict[str, Any]) -> str | None:
    status = _normalize_gateway_status(payload.get("profile_status"))
    if status:
        return status

    profile_payload = payload.get("profile")
    if isinstance(profile_payload, dict):
        status = _normalize_gateway_status(profile_payload.get("status"))
        if status:
            return status
    return None


def _extract_gateway_token_status(payload: Dict[str, Any]) -> str | None:
    status = _normalize_gateway_status(payload.get("token_status"))
    if status:
        return status
    return _extract_gateway_profile_status(payload)


def _upsert_gateway_setup_token_profile(token: str) -> Dict[str, Any] | None:
    base_url = _gateway_base_url()
    api_key = _gateway_api_key()
    if not base_url or not api_key:
        return None

    client = GatewayClient(base_url, api_key=api_key)
    payload = {
        "profile_id": DEFAULT_GATEWAY_PROFILE_ID,
        "provider": "anthropic",
        "auth_mode": "setup_token",
        "token": token,
        "metadata": {"source": "dashboard", "path": "/api/chat/token"},
    }
    response = client.post_json("/v1/profiles/upsert", payload=payload)
    if not isinstance(response, dict):
        raise GatewayClientError(
            "Gateway profiles/upsert response must be a JSON object"
        )
    return response


def _gateway_validation_message(status: str, last_error: str) -> str:
    if last_error:
        return last_error
    return _GATEWAY_VALIDATION_MESSAGES.get(
        status, "Gateway validation status is available."
    )


def _gateway_validation_detail(
    setting_key: str = CLAUDE_TOKEN_SETTING_KEY,
) -> Dict[str, Any] | None:
    get_setting_metadata = getattr(models, "get_setting_metadata", None)
    if not callable(get_setting_metadata):
        return None

    metadata = get_setting_metadata(setting_key) or {}
    validation_status = str(metadata.get("validation_status") or "").strip()
    if not validation_status:
        return None

    last_error = str(metadata.get("last_error") or "").strip()
    validation: Dict[str, Any] = {
        "status": validation_status,
        "http_status": None,
        "message": _gateway_validation_message(validation_status, last_error),
        "source": "gateway",
        "last_validated_at": metadata.get("last_validated_at"),
    }
    if last_error:
        validation["error"] = last_error
    return validation


def _resolve_token_validation(
    token: str,
    *,
    allow_gateway_metadata: bool = False,
) -> Dict[str, Any]:
    candidate = (token or "").strip()
    if (
        allow_gateway_metadata
        and candidate
        and _looks_like_setup_token(candidate)
        and not _is_setup_token_hard_blocked()
    ):
        gateway_validation = _gateway_validation_detail()
        if gateway_validation is not None:
            return gateway_validation
    return validate_claude_token(candidate)


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


def _gateway_client() -> GatewayClient:
    """Build a configured gateway client for profile lifecycle calls."""
    base_url = (os.getenv("GATEWAY_BASE_URL") or "").strip()
    if not base_url:
        raise RuntimeError("GATEWAY_BASE_URL is not configured")

    api_key = (os.getenv("GATEWAY_API_KEY") or "").strip() or None
    return GatewayClient(base_url=base_url, api_key=api_key)


def _gateway_upsert_setup_token(token: str) -> Dict[str, Any]:
    """Upsert the default setup-token profile in gateway."""
    body = _gateway_client().post_json(
        "/v1/profiles/upsert",
        payload={
            "profile_id": DEFAULT_GATEWAY_PROFILE_ID,
            "token": token,
        },
    )
    if not isinstance(body, dict):
        raise RuntimeError("Gateway profile upsert returned an invalid payload")
    if str(body.get("status") or "").lower() != "ok":
        raise RuntimeError(str(body.get("message") or "Gateway profile upsert failed"))
    return body


def _gateway_revoke_setup_token() -> Dict[str, Any]:
    """Revoke the default setup-token profile in gateway."""
    body = _gateway_client().post_json(
        "/v1/profiles/revoke",
        payload={
            "profile_id": DEFAULT_GATEWAY_PROFILE_ID,
            "profile_slug": DEFAULT_GATEWAY_PROFILE_ID,
        },
    )
    if not isinstance(body, dict):
        raise RuntimeError("Gateway profile revoke returned an invalid payload")
    if str(body.get("status") or "").lower() != "ok":
        raise RuntimeError(str(body.get("message") or "Gateway profile revoke failed"))
    return body


def _rollback_gateway_setup_token(previous_token: str) -> tuple[bool, str]:
    """Best-effort rollback for failed local token persistence after gateway update."""
    try:
        if previous_token:
            _gateway_upsert_setup_token(previous_token)
        else:
            _gateway_revoke_setup_token()
        return True, ""
    except Exception as exc:  # pragma: no cover - covered via route tests.
        return False, str(exc)


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


def _extract_response_input_text(raw_input: Any) -> str:
    chunks: list[str] = []

    def _collect(value: Any) -> None:
        if isinstance(value, str):
            text = value.strip()
            if text:
                chunks.append(text)
            return
        if isinstance(value, list):
            for item in value:
                _collect(item)
            return
        if isinstance(value, dict):
            # Responses input may be text blocks or message-like structures.
            for key in ("text", "content", "message", "value"):
                if key in value:
                    _collect(value.get(key))

    _collect(raw_input)
    return "\n".join(chunks).strip()


def _parse_runner_sse_event(raw_event: str) -> dict[str, Any] | None:
    for line in (raw_event or "").splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def _format_sse_data(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


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


def init_chat_runner(app=None) -> ChatRunnerBackend:
    """Initialize singleton runner once per process."""
    del app  # app is optional; current_app provides config context.
    global _runner
    store = _get_chat_store()
    with _runner_lock:
        if _runner is None:
            _runner = create_chat_runner(
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


def _get_runner() -> ChatRunnerBackend:
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


@chat_bp.route("/v1/responses", methods=["POST"])
@_login_or_api_key_required
def create_response():
    """OpenAI-style Responses endpoint with stream mode over SSE."""
    token = get_claude_token()
    if not token:
        return jsonify({"error": {"message": "Claude token not configured"}}), 400
    if _looks_like_setup_token(token) and _is_setup_token_hard_blocked():
        return jsonify({"error": {"message": _unsupported_setup_token_message()}}), 400

    payload = request.get_json(silent=True) or {}
    if not bool(payload.get("stream")):
        return (
            jsonify(
                {
                    "error": {
                        "message": "Only stream=true is currently supported on /v1/responses"
                    }
                }
            ),
            400,
        )

    prompt_text = _extract_response_input_text(payload.get("input"))
    if not prompt_text:
        return jsonify({"error": {"message": "input is required"}}), 400

    model = str(payload.get("model") or "claude-agent")
    store = _get_chat_store()
    runner = _get_runner()
    session_id = secrets.token_hex(16)
    response_id = f"resp_{secrets.token_hex(12)}"
    created_ts = int(time.time())

    session_obj = store.create_session(
        session_id,
        title=_derive_title(prompt_text),
        status="idle",
    )
    store.append_message(
        session_id,
        {
            "role": "user",
            "content": prompt_text,
            "type": "message",
            "metadata": {"source": "v1.responses"},
        },
        session_updates={"status": "running", "last_error": None},
    )
    runner.ensure_session(
        session_id,
        title=session_obj.get("title"),
        sdk_session_id=session_obj.get("sdk_session_id"),
    )

    try:
        runner.send_message(session_id=session_id, user_message=prompt_text)
    except ValueError as exc:
        store.update_session(session_id, {"status": "idle", "last_error": str(exc)})
        return jsonify({"error": {"message": str(exc)}}), 400
    except RunnerError as exc:
        store.update_session(session_id, {"status": "error", "last_error": str(exc)})
        return jsonify({"error": {"message": str(exc)}}), 409
    except Exception as exc:
        message = f"Failed to send message: {exc}"
        store.update_session(session_id, {"status": "error", "last_error": message})
        return jsonify({"error": {"message": message}}), 500

    def responses_sse():
        text_parts: list[str] = []
        yield _format_sse_data(
            {
                "type": "response.created",
                "response": {
                    "id": response_id,
                    "object": "response",
                    "created": created_ts,
                    "model": model,
                    "status": "in_progress",
                    "output": [],
                },
            }
        )

        for raw_event in runner.get_stream(session_id):
            event = _parse_runner_sse_event(raw_event)
            if not event:
                continue

            event_type = str(event.get("type") or "")
            if event_type in ("ping", "tool_use", "tool_result", "system"):
                continue

            if event_type in ("text", "result"):
                chunk = str(event.get("content") or "")
                if not chunk:
                    continue
                text_parts.append(chunk)
                yield _format_sse_data(
                    {
                        "type": "response.output_text.delta",
                        "response_id": response_id,
                        "output_index": 0,
                        "content_index": 0,
                        "delta": chunk,
                    }
                )
                continue

            if event_type == "error":
                message = str(event.get("content") or "Agent execution failed")
                yield _format_sse_data(
                    {
                        "type": "response.failed",
                        "response": {
                            "id": response_id,
                            "object": "response",
                            "created": created_ts,
                            "model": model,
                            "status": "failed",
                            "error": {"message": message},
                        },
                    }
                )
                yield "data: [DONE]\n\n"
                return

            if event_type == "done":
                break

        final_text = "".join(text_parts)
        yield _format_sse_data(
            {
                "type": "response.output_text.done",
                "response_id": response_id,
                "output_index": 0,
                "content_index": 0,
                "text": final_text,
            }
        )
        yield _format_sse_data(
            {
                "type": "response.completed",
                "response": {
                    "id": response_id,
                    "object": "response",
                    "created": created_ts,
                    "model": model,
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": final_text,
                                    "annotations": [],
                                }
                            ],
                        }
                    ],
                },
            }
        )
        yield "data: [DONE]\n\n"

    response = Response(
        stream_with_context(responses_sse()),
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

    validation = _resolve_token_validation(token, allow_gateway_metadata=True)
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

    gateway_profile_status = None
    gateway_token_status = None
    gateway_upserted = False
    try:
        gateway_upsert_payload = _upsert_gateway_setup_token_profile(token)
        if gateway_upsert_payload is not None:
            gateway_upserted = True
            gateway_profile_status = _extract_gateway_profile_status(
                gateway_upsert_payload
            )
            gateway_token_status = _extract_gateway_token_status(gateway_upsert_payload)
    except GatewayHTTPError as exc:
        _log_token_lifecycle(
            action="save",
            status="error",
            reason="gateway_upsert_http_error",
            gateway_http_status=exc.status_code,
            redacted=_redact_token(token),
        )
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Gateway profile upsert failed",
                    "gateway_http_status": exc.status_code,
                }
            ),
            502,
        )
    except GatewayClientError as exc:
        _log_token_lifecycle(
            action="save",
            status="error",
            reason="gateway_upsert_failed",
            gateway_error=str(exc),
            redacted=_redact_token(token),
        )
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Gateway profile upsert failed",
                    "gateway_error": str(exc),
                }
            ),
            502,
        )

    if gateway_upsert_payload:
        gateway_validation = str(gateway_upsert_payload.get("validation") or "").strip().lower()
        if gateway_validation:
            validation = {
                "status": gateway_validation,
                "http_status": None,
                "message": str(
                    gateway_upsert_payload.get("message")
                    or validation.get("message")
                    or "Gateway profile upsert completed"
                ),
            }

    os.environ["CLAUDE_SETUP_TOKEN"] = token
    models.set_setting(CLAUDE_TOKEN_SETTING_KEY, token)

    if gateway_profile_status in _PROFILE_STATUS_VALUES:
        try:
            models.upsert_setup_token_profile(
                DEFAULT_GATEWAY_PROFILE_ID,
                token=token,
                status=gateway_profile_status,
            )
        except Exception:
            pass

    profile_metadata_stored = False
    if gateway_token_status:
        try:
            models.update_setting_metadata(
                CLAUDE_TOKEN_SETTING_KEY,
                validation_status=gateway_token_status,
                last_error=None,
            )
            profile_metadata_stored = True
        except Exception:
            profile_metadata_stored = False

    persisted = _persist_to_railway_async({"CLAUDE_SETUP_TOKEN": token})

    init_chat_runner()

    _log_token_lifecycle(
        action="save",
        status="success",
        validation=validation["status"],
        gateway_upserted=gateway_upserted,
        profile_status=gateway_profile_status,
        token_status=gateway_token_status,
        profile_metadata_stored=profile_metadata_stored,
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
            "gateway_upserted": gateway_upserted,
            "profile_status": gateway_profile_status,
            "token_status": gateway_token_status,
            "profile_metadata_stored": profile_metadata_stored,
            "redacted": _redact_token(token),
        }
    )


@chat_bp.route("/api/chat/token/rotate", methods=["POST"])
@_login_required_api
def rotate_token():
    """Rotate Claude setup token with gateway-first, rollback-safe semantics."""
    payload = request.get_json(silent=True) or {}
    token = (payload.get("new_token") or payload.get("token") or "").strip()
    raw_current_token = payload.get("current_token")
    current_token = None

    if raw_current_token is not None:
        if not isinstance(raw_current_token, str):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Validation failed",
                        "errors": {"current_token": "current_token must be a string"},
                    }
                ),
                400,
            )
        current_token = raw_current_token.strip()

    if not token:
        _log_token_lifecycle(
            action="rotate",
            status="error",
            reason="missing_token",
            validation="missing",
            redacted="",
        )
        return jsonify({"status": "error", "message": "token is required"}), 400

    validation = validate_claude_token(token)
    if validation["status"] in ("invalid", "expired", "unsupported"):
        _log_token_lifecycle(
            action="rotate",
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

    with _token_rotate_lock:
        previous_token = get_claude_token().strip()

        if current_token is not None and current_token != previous_token:
            _log_token_lifecycle(
                action="rotate",
                status="error",
                reason="current_token_mismatch",
                redacted=_redact_token(token),
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Current token does not match",
                    }
                ),
                409,
            )

        if previous_token and previous_token == token:
            _log_token_lifecycle(
                action="rotate",
                status="error",
                reason="token_unchanged",
                redacted=_redact_token(token),
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "New token must be different from current token",
                    }
                ),
                400,
            )

        try:
            _gateway_upsert_setup_token(token)
        except GatewayHTTPError as exc:
            _log_token_lifecycle(
                action="rotate",
                status="error",
                reason="gateway_http_error",
                gateway_http_status=exc.status_code,
                redacted=_redact_token(token),
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Gateway profile rotate failed with HTTP {exc.status_code}",
                    }
                ),
                502,
            )
        except (GatewayClientError, RuntimeError) as exc:
            _log_token_lifecycle(
                action="rotate",
                status="error",
                reason="gateway_upsert_failed",
                error=str(exc),
                redacted=_redact_token(token),
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Gateway token update failed",
                        "error": str(exc),
                    }
                ),
                502,
            )

        previous_env_token = os.environ.get("CLAUDE_SETUP_TOKEN")
        os.environ["CLAUDE_SETUP_TOKEN"] = token

        try:
            models.set_setting(CLAUDE_TOKEN_SETTING_KEY, token)
        except Exception as exc:
            if previous_env_token is None:
                os.environ.pop("CLAUDE_SETUP_TOKEN", None)
            else:
                os.environ["CLAUDE_SETUP_TOKEN"] = previous_env_token

            rolled_back, rollback_error = _rollback_gateway_setup_token(previous_token)
            rollback_status = "ok" if rolled_back else "error"

            _log_token_lifecycle(
                action="rotate",
                status="error",
                reason="local_persist_failed",
                rollback=rollback_status,
                error=str(exc),
                rollback_error=rollback_error or None,
                redacted=_redact_token(token),
            )

            response_payload: Dict[str, Any] = {
                "status": "error",
                "message": "Token rotation failed while saving locally",
                "error": str(exc),
                "rollback": {"status": rollback_status},
            }
            if rollback_error:
                response_payload["rollback"]["error"] = rollback_error
            return jsonify(response_payload), 500

    persisted = _persist_to_railway_async({"CLAUDE_SETUP_TOKEN": token})
    init_chat_runner()

    _log_token_lifecycle(
        action="rotate",
        status="success",
        validation=validation["status"],
        persisted_to_railway=persisted,
        redacted=_redact_token(token),
        previous_redacted=_redact_token(previous_token),
    )

    return jsonify(
        {
            "status": "ok",
            "message": "Claude token rotated",
            "validation": validation["status"],
            "validation_detail": validation,
            "persisted_to_railway": persisted,
            "redacted": _redact_token(token),
            "previous_redacted": _redact_token(previous_token),
        }
    )


@chat_bp.route("/api/chat/token/validate", methods=["POST"])
@_login_required_api
def validate_token():
    """Validate a provided token (or the currently stored token) without saving."""
    payload = request.get_json(silent=True) or {}
    provided_token = (payload.get("token") or "").strip()
    stored_token = get_claude_token()
    token = provided_token or stored_token

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

    # For stored setup tokens, prefer cached gateway metadata when available.
    if (
        not provided_token
        and token == stored_token
        and _looks_like_setup_token(token)
        and not _is_setup_token_hard_blocked()
    ):
        cached_validation = _gateway_validation_detail()
        if cached_validation is not None:
            _log_token_lifecycle(
                action="validate",
                status="success",
                configured=True,
                validation=str(cached_validation.get("status") or "unknown"),
                redacted=_redact_token(token),
            )
            return jsonify(
                {
                    "status": "ok",
                    "configured": True,
                    "validation": str(cached_validation.get("status") or "unknown"),
                    "validation_detail": cached_validation,
                    "redacted": _redact_token(token),
                }
            )

    if _should_use_gateway_profile_api():
        try:
            gateway_response = _validate_gateway_profile(CLAUDE_TOKEN_PROFILE_ID, token)
        except GatewayHTTPError as exc:
            _log_token_lifecycle(
                action="validate",
                status="error",
                reason="gateway_http_error",
                profile_id=CLAUDE_TOKEN_PROFILE_ID,
                gateway_http_status=exc.status_code,
                redacted=_redact_token(token),
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "configured": True,
                        "validation": "runtime_error",
                        "message": f"Gateway profile validate failed with HTTP {exc.status_code}",
                        "validation_detail": {"status": "runtime_error"},
                        "redacted": _redact_token(token),
                    }
                ),
                502,
            )
        except (GatewayClientError, RuntimeError) as exc:
            _log_token_lifecycle(
                action="validate",
                status="error",
                reason="gateway_request_failed",
                profile_id=CLAUDE_TOKEN_PROFILE_ID,
                error=str(exc),
                redacted=_redact_token(token),
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "configured": True,
                        "validation": "runtime_error",
                        "message": f"Gateway profile validate failed: {exc}",
                        "validation_detail": {"status": "runtime_error"},
                        "redacted": _redact_token(token),
                    }
                ),
                502,
            )

        validation_detail = gateway_response.get("validation_detail") or gateway_response
        validation_status = str(
            gateway_response.get("validation")
            or (
                validation_detail.get("status")
                if isinstance(validation_detail, dict)
                else ""
            )
            or gateway_response.get("status")
            or "unknown"
        ).strip().lower()

        status_code = (
            502
            if validation_status in {"runtime_unavailable", "runtime_error"}
            else 200
        )
        response_payload = {
            "status": "error" if status_code >= 500 else "ok",
            "configured": True,
            "validation": validation_status,
            "validation_detail": validation_detail,
            "redacted": _redact_token(token),
        }
        if gateway_response.get("message"):
            response_payload["message"] = gateway_response["message"]
        elif status_code >= 500:
            response_payload["message"] = "Gateway runtime canary failed"

        _log_token_lifecycle(
            action="validate",
            status="success" if status_code < 500 else "error",
            configured=True,
            validation=validation_status,
            redacted=_redact_token(token),
        )
        return jsonify(response_payload), status_code

    if _looks_like_setup_token(token):
        from routes.api_v1 import validate_profile_token

        try:
            profile_payload, status_code = validate_profile_token(
                profile_id=CLAUDE_TOKEN_PROFILE_ID,
                token=token,
            )
        except Exception as exc:
            _log_token_lifecycle(
                action="validate",
                status="error",
                reason="gateway_runtime_exception",
                configured=True,
                error=str(exc),
                redacted=_redact_token(token),
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "configured": True,
                        "validation": "runtime_error",
                        "message": f"Gateway runtime canary failed: {exc}",
                        "validation_detail": {
                            "status": "runtime_error",
                            "message": str(exc),
                        },
                        "redacted": _redact_token(token),
                    }
                ),
                502,
            )

        validation = profile_payload.get("validation_detail") or {}
        validation_status = str(
            profile_payload.get("validation")
            or (validation.get("status") if isinstance(validation, dict) else "")
            or "invalid"
        )
        _log_token_lifecycle(
            action="validate",
            status="success" if status_code < 500 else "error",
            configured=True,
            validation=validation_status,
            redacted=_redact_token(token),
        )

        response_payload = {
            "status": profile_payload.get("status", "ok"),
            "configured": True,
            "validation": validation_status,
            "validation_detail": validation,
            "redacted": _redact_token(token),
        }
        if profile_payload.get("message"):
            response_payload["message"] = profile_payload["message"]

        return jsonify(response_payload), status_code

    validation = validate_claude_token(token)
    validation_status = str(validation.get("status") or "unknown").strip().lower()
    _log_token_lifecycle(
        action="validate",
        status="success",
        configured=True,
        validation=validation_status,
        redacted=_redact_token(token),
    )

    response_payload = {
        "status": "ok",
        "configured": True,
        "validation": validation_status,
        "validation_detail": validation,
        "redacted": _redact_token(token),
    }
    if validation.get("message"):
        response_payload["message"] = validation["message"]

    return jsonify(response_payload), 200


@chat_bp.route("/api/chat/token/revoke", methods=["POST"])
@_login_required_api
def revoke_token():
    """Revoke the default setup-token profile and clear local token state."""
    try:
        gateway_response = _revoke_gateway_profile(CLAUDE_TOKEN_PROFILE_ID)
    except GatewayHTTPError as exc:
        _log_token_lifecycle(
            action="revoke",
            status="error",
            reason="gateway_http_error",
            profile_id=CLAUDE_TOKEN_PROFILE_ID,
            gateway_http_status=exc.status_code,
        )
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Gateway profile revoke failed with HTTP {exc.status_code}",
                }
            ),
            502,
        )
    except (GatewayClientError, RuntimeError) as exc:
        _log_token_lifecycle(
            action="revoke",
            status="error",
            reason="gateway_request_failed",
            profile_id=CLAUDE_TOKEN_PROFILE_ID,
            error=str(exc),
        )
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Gateway profile revoke failed: {exc}",
                }
            ),
            502,
        )

    delete_setting = getattr(models, "delete_setting", None)
    if callable(delete_setting):
        delete_setting(CLAUDE_TOKEN_SETTING_KEY)
    else:
        models.set_setting(CLAUDE_TOKEN_SETTING_KEY, "")

    os.environ.pop("CLAUDE_SETUP_TOKEN", None)
    _log_token_lifecycle(
        action="revoke",
        status="success",
        profile_id=CLAUDE_TOKEN_PROFILE_ID,
    )

    return jsonify(
        {
            "status": "ok",
            "message": "Claude token revoked",
            "profile_id": CLAUDE_TOKEN_PROFILE_ID,
            "revoked": bool(gateway_response.get("revoked", True)),
        }
    )
