"""HTTP routes for AIAA Gateway."""

from __future__ import annotations

import json
import logging
import hashlib
import os
import secrets
import shutil
import threading
import time
import uuid
from collections import deque
from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests as http_requests
from flask import (
    Blueprint,
    Response,
    current_app,
    g,
    jsonify,
    request,
    stream_with_context,
)

from .redaction import redact_exception_message, redact_token_like_text
from .services.profile_service import (
    normalize_profile_id,
    resolve_stored_profile_token,
    revoke_profile,
    upsert_profile_record,
)
from .services.responses_service import (
    build_anthropic_messages_payload,
    map_anthropic_to_response,
    normalize_gateway_request_fields,
)
from .services.runtime_canary import run_gateway_runtime_canary
from .services.runtime_query import is_setup_token, run_gateway_runtime_query

gateway_bp = Blueprint("gateway", __name__)
_SUPPORTED_PROFILE_VALIDATION_STATES = {
    "valid",
    "expired",
    "invalid",
    "unreachable",
    "unsupported",
}

_PROFILE_STORE_KEY_ENV_VARS = (
    "CHAT_TOKEN_ENCRYPTION_KEY",
    "SETTINGS_ENCRYPTION_KEY",
    "FLASK_SECRET_KEY",
    "SECRET_KEY",
)
_RUNTIME_WORKSPACE_REQUIRED_PATHS = (
    ".claude/skills",
    ".claude/rules",
    ".claude/hooks",
    ".claude/agents",
    "context",
    "clients",
    "execution",
    ".tmp",
)
logger = logging.getLogger(__name__)
CORRELATION_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"
_PUBLIC_ENDPOINTS = frozenset({"/", "/health"})
_PRIVATE_ENDPOINT_PATH_PREFIX = "/v1/"
_auth_failure_lock = threading.RLock()
_auth_failure_windows: dict[str, deque[float]] = {}


def _resolve_correlation_id() -> str:
    incoming = (
        request.headers.get(CORRELATION_HEADER)
        or request.headers.get(REQUEST_ID_HEADER)
        or ""
    ).strip()
    return incoming or uuid.uuid4().hex


def get_correlation_id() -> str:
    return str(getattr(g, "correlation_id", "") or "")


@gateway_bp.before_request
def _assign_correlation_id() -> None:
    g.correlation_id = _resolve_correlation_id()


@gateway_bp.after_request
def _add_correlation_header(response):
    correlation_id = get_correlation_id()
    if correlation_id:
        response.headers[CORRELATION_HEADER] = correlation_id
    return response


def _log_gateway_event(event: str, status: str, **details: Any) -> None:
    payload: dict[str, Any] = {
        "event": event,
        "status": status,
        "path": request.path,
        "method": request.method,
        "correlation_id": get_correlation_id(),
    }
    payload.update(details)
    logger.info(json.dumps(payload, sort_keys=True))


def _json_error(
    message: str,
    status_code: int,
    *,
    error_type: str = "invalid_request_error",
    details: dict[str, Any] | None = None,
):
    safe_message = redact_token_like_text(message)
    payload: dict[str, Any] = {
        "error": {
            "type": error_type,
            "message": safe_message,
        }
    }
    if details:
        payload["error"]["details"] = details
    correlation_id = get_correlation_id()
    if correlation_id:
        payload["correlation_id"] = correlation_id
    return jsonify(payload), status_code


def _resolve_bearer_token() -> str:
    auth_header = (request.headers.get("Authorization") or "").strip()
    if not auth_header.lower().startswith("bearer "):
        return ""
    return auth_header[7:].strip()


def _resolve_internal_bearer_token() -> str:
    configured = (current_app.config.get("GATEWAY_INTERNAL_TOKEN") or "").strip()
    if configured:
        return configured

    fallback = (current_app.config.get("GATEWAY_API_KEY") or "").strip()
    if fallback:
        return fallback

    return (
        os.getenv("GATEWAY_INTERNAL_TOKEN") or os.getenv("GATEWAY_API_KEY") or ""
    ).strip()


def _resolve_anthropic_api_key() -> str:
    header_key = (request.headers.get("X-Anthropic-Api-Key") or "").strip()
    if header_key:
        return header_key

    gateway_api_key = (current_app.config.get("GATEWAY_API_KEY") or "").strip()
    internal_token = (current_app.config.get("GATEWAY_INTERNAL_TOKEN") or "").strip()
    auth_header = (request.headers.get("Authorization") or "").strip()
    if (
        not gateway_api_key
        and not internal_token
        and auth_header.lower().startswith("bearer ")
    ):
        return auth_header[7:].strip()

    configured = (current_app.config.get("ANTHROPIC_API_KEY") or "").strip()
    if configured:
        return configured
    return (os.getenv("ANTHROPIC_API_KEY") or "").strip()


def _get_auth_failure_limit() -> int:
    raw_value = current_app.config.get("GATEWAY_AUTH_FAILURE_MAX_ATTEMPTS", 5)
    try:
        return max(1, int(raw_value))
    except (TypeError, ValueError):
        return 5


def _get_auth_failure_window_seconds() -> int:
    raw_value = current_app.config.get("GATEWAY_AUTH_FAILURE_WINDOW_SECONDS", 60)
    try:
        return max(1, int(raw_value))
    except (TypeError, ValueError):
        return 60


def _auth_failure_bucket_key(token: str) -> str:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    client = (request.remote_addr or "unknown").strip() or "unknown"
    return f"{client}:{token_hash}"


def _is_auth_failure_throttled(token: str) -> tuple[bool, int, int, int]:
    limit = _get_auth_failure_limit()
    window_seconds = _get_auth_failure_window_seconds()
    now = time.monotonic()
    cutoff = now - window_seconds
    bucket_key = _auth_failure_bucket_key(token)

    with _auth_failure_lock:
        history = _auth_failure_windows.setdefault(bucket_key, deque())
        while history and history[0] <= cutoff:
            history.popleft()
        if len(history) >= limit:
            retry_after = max(1, int(history[0] + window_seconds - now))
            return True, retry_after, limit, window_seconds
    return False, 0, limit, window_seconds


def _record_auth_failure(token: str) -> None:
    window_seconds = _get_auth_failure_window_seconds()
    now = time.monotonic()
    cutoff = now - window_seconds
    bucket_key = _auth_failure_bucket_key(token)

    with _auth_failure_lock:
        history = _auth_failure_windows.setdefault(bucket_key, deque())
        while history and history[0] <= cutoff:
            history.popleft()
        history.append(now)


def _reset_auth_failure_throttle_state() -> None:
    """Testing helper to clear in-memory auth throttle state."""
    with _auth_failure_lock:
        _auth_failure_windows.clear()


@gateway_bp.before_request
def require_internal_bearer_auth():
    if request.path in _PUBLIC_ENDPOINTS:
        return None
    if not request.path.startswith(_PRIVATE_ENDPOINT_PATH_PREFIX):
        return None

    expected_token = _resolve_internal_bearer_token()
    if not expected_token:
        return _json_error(
            "Gateway internal bearer token is not configured.",
            503,
            error_type="configuration_error",
        )

    bearer_token = _resolve_bearer_token()
    if not bearer_token:
        response, status_code = _json_error(
            "Missing internal bearer token.",
            401,
            error_type="authentication_error",
        )
        response.headers["WWW-Authenticate"] = "Bearer"
        return response, status_code

    throttled, retry_after, limit, window_seconds = _is_auth_failure_throttled(
        bearer_token
    )
    if throttled:
        response, status_code = _json_error(
            "Too many invalid internal bearer token attempts.",
            429,
            error_type="rate_limit_error",
            details={
                "retry_after_seconds": retry_after,
                "limit": limit,
                "window_seconds": window_seconds,
            },
        )
        response.headers["Retry-After"] = str(retry_after)
        return response, status_code

    if not secrets.compare_digest(bearer_token, expected_token):
        _record_auth_failure(bearer_token)
        throttled, retry_after, limit, window_seconds = _is_auth_failure_throttled(
            bearer_token
        )
        if throttled:
            response, status_code = _json_error(
                "Too many invalid internal bearer token attempts.",
                429,
                error_type="rate_limit_error",
                details={
                    "retry_after_seconds": retry_after,
                    "limit": limit,
                    "window_seconds": window_seconds,
                },
            )
            response.headers["Retry-After"] = str(retry_after)
            return response, status_code

        response, status_code = _json_error(
            "Invalid internal bearer token.",
            401,
            error_type="authentication_error",
        )
        response.headers["WWW-Authenticate"] = "Bearer"
        return response, status_code

    return None


def _get_profile_store_readiness() -> dict[str, Any]:
    configured_key_env = next(
        (
            env_var
            for env_var in _PROFILE_STORE_KEY_ENV_VARS
            if (os.getenv(env_var) or "").strip()
        ),
        None,
    )
    ready = configured_key_env is not None
    return {
        "ready": ready,
        "status": "ready" if ready else "not_ready",
        "encryption_key_source": configured_key_env,
        "missing_env_vars": [] if ready else list(_PROFILE_STORE_KEY_ENV_VARS),
    }


def _get_runtime_readiness() -> dict[str, Any]:
    workspace_root = (os.getenv("GATEWAY_WORKSPACE_ROOT") or "/app").strip() or "/app"
    workspace_path = Path(workspace_root)
    workspace_accessible = workspace_path.is_dir()
    missing_workspace_paths: list[str] = []
    if workspace_accessible:
        missing_workspace_paths = [
            relative_path
            for relative_path in _RUNTIME_WORKSPACE_REQUIRED_PATHS
            if not (workspace_path / relative_path).exists()
        ]

    claude_cli_path = shutil.which("claude")
    ready = (
        bool(claude_cli_path)
        and workspace_accessible
        and not missing_workspace_paths
    )
    return {
        "ready": ready,
        "status": "ready" if ready else "not_ready",
        "claude_cli_available": bool(claude_cli_path),
        "workspace_root": workspace_root,
        "workspace_accessible": workspace_accessible,
        "missing_workspace_paths": missing_workspace_paths,
    }


def _resolve_profile_store() -> MutableMapping[str, dict[str, Any]]:
    store = current_app.config.get("PROFILE_STORE")
    if isinstance(store, MutableMapping):
        return store

    initialized_store: dict[str, dict[str, Any]] = {}
    current_app.config["PROFILE_STORE"] = initialized_store
    return initialized_store


def _resolve_profile_token_store() -> MutableMapping[str, dict[str, Any]]:
    store = current_app.config.get("PROFILE_TOKEN_STORE")
    if isinstance(store, MutableMapping):
        return store

    initialized_store: dict[str, dict[str, Any]] = {}
    current_app.config["PROFILE_TOKEN_STORE"] = initialized_store
    return initialized_store


def _format_sse_data(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        return f"data: {payload}\n\n"
    return (
        f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"
    )


def _parse_upstream_error_details(upstream_response: Any) -> dict[str, Any]:
    details: dict[str, Any]
    try:
        parsed = upstream_response.json()
        details = parsed if isinstance(parsed, dict) else {"body": parsed}
    except ValueError:
        details = {"body": upstream_response.text.strip() or "Unknown upstream error"}
    return {"upstream_status": upstream_response.status_code, **details}


def _extract_error_message(event: Mapping[str, Any]) -> str:
    nested_error = event.get("error")
    if isinstance(nested_error, Mapping):
        nested_message = nested_error.get("message")
        if isinstance(nested_message, str) and nested_message.strip():
            return nested_message.strip()

    direct_message = event.get("message")
    if isinstance(direct_message, str) and direct_message.strip():
        return direct_message.strip()

    return "Upstream provider stream failed."


def _extract_text_delta(event: Mapping[str, Any]) -> str:
    event_type = str(event.get("type") or "")
    if event_type == "content_block_start":
        block = event.get("content_block")
        if isinstance(block, Mapping) and str(block.get("type") or "") == "text":
            text = block.get("text")
            if isinstance(text, str):
                return text
        return ""

    if event_type != "content_block_delta":
        return ""

    delta = event.get("delta")
    if not isinstance(delta, Mapping) or str(delta.get("type") or "") != "text_delta":
        return ""

    text = delta.get("text")
    return text if isinstance(text, str) else ""


def _stream_openai_response_events(
    upstream_response: Any,
    *,
    requested_model: str,
):
    response_id = f"resp_{uuid.uuid4().hex}"
    created_ts = int(time.time())
    model = requested_model
    input_tokens = 0
    output_tokens = 0
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

    try:
        for raw_line in upstream_response.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip()
            if not line or line.startswith(":") or line.startswith("event:"):
                continue
            if not line.startswith("data:"):
                continue

            data_value = line[5:].strip()
            if not data_value:
                continue

            try:
                event = json.loads(data_value)
            except ValueError:
                continue
            if not isinstance(event, Mapping):
                continue

            event_type = str(event.get("type") or "")
            if event_type == "message_start":
                message = event.get("message")
                if isinstance(message, Mapping):
                    model_value = message.get("model")
                    if isinstance(model_value, str) and model_value.strip():
                        model = model_value.strip()
                    usage = message.get("usage")
                    if isinstance(usage, Mapping):
                        try:
                            input_tokens = int(usage.get("input_tokens") or 0)
                        except (TypeError, ValueError):
                            input_tokens = 0
                continue

            if event_type == "message_delta":
                usage = event.get("usage")
                if isinstance(usage, Mapping):
                    try:
                        output_tokens = int(usage.get("output_tokens") or 0)
                    except (TypeError, ValueError):
                        output_tokens = 0
                continue

            if event_type in {"content_block_start", "content_block_delta"}:
                text_chunk = _extract_text_delta(event)
                if not text_chunk:
                    continue
                text_parts.append(text_chunk)
                yield _format_sse_data(
                    {
                        "type": "response.output_text.delta",
                        "response_id": response_id,
                        "output_index": 0,
                        "content_index": 0,
                        "delta": text_chunk,
                    }
                )
                continue

            if event_type == "error":
                yield _format_sse_data(
                    {
                        "type": "response.failed",
                        "response": {
                            "id": response_id,
                            "object": "response",
                            "created": created_ts,
                            "model": model,
                            "status": "failed",
                            "error": {"message": _extract_error_message(event)},
                        },
                    }
                )
                yield _format_sse_data("[DONE]")
                return

            if event_type == "message_stop":
                break
    except Exception as exc:
        yield _format_sse_data(
            {
                "type": "response.failed",
                "response": {
                    "id": response_id,
                    "object": "response",
                    "created": created_ts,
                    "model": model,
                    "status": "failed",
                    "error": {"message": f"Upstream stream interrupted: {exc}"},
                },
            }
        )
        yield _format_sse_data("[DONE]")
        return
    finally:
        close = getattr(upstream_response, "close", None)
        if callable(close):
            close()

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
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
            },
        }
    )
    yield _format_sse_data("[DONE]")


def _runtime_text_to_response_payload(text: str, *, model: str) -> dict[str, Any]:
    response_id = f"resp_{uuid.uuid4().hex}"
    created_at = int(time.time())
    output = [
        {
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": text,
                    "annotations": [],
                }
            ],
        }
    ]
    return {
        "id": response_id,
        "object": "response",
        "created_at": created_at,
        "status": "completed",
        "model": model,
        "output": output,
        "output_text": text,
        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    }


def _stream_runtime_response_events(text: str, *, model: str):
    response_id = f"resp_{uuid.uuid4().hex}"
    created_ts = int(time.time())
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
    if text:
        yield _format_sse_data(
            {
                "type": "response.output_text.delta",
                "response_id": response_id,
                "output_index": 0,
                "content_index": 0,
                "delta": text,
            }
        )
        yield _format_sse_data(
            {
                "type": "response.output_text.done",
                "response_id": response_id,
                "output_index": 0,
                "content_index": 0,
                "text": text,
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
                                "text": text,
                                "annotations": [],
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            },
        }
    )
    yield _format_sse_data("[DONE]")


@gateway_bp.get("/")
def index():
    return jsonify(
        {
            "service": current_app.config["SERVICE_NAME"],
            "status": "ok",
        }
    )


@gateway_bp.get("/health")
def health():
    profile_store = _get_profile_store_readiness()
    runtime = _get_runtime_readiness()
    ready = bool(profile_store["ready"] and runtime["ready"])
    _log_gateway_event("gateway.health", "success", ready=ready)
    return jsonify(
        {
            "service": current_app.config["SERVICE_NAME"],
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "ready": ready,
            "profile_store_ready": profile_store["ready"],
            "runtime_ready": runtime["ready"],
            "profile_store": profile_store,
            "runtime": runtime,
        }
    )


@gateway_bp.post("/v1/profiles/revoke")
def revoke_gateway_profile():
    """Invalidate a profile and remove any persisted token material."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _json_error("Request body must be a JSON object.", 400)

    profile_id = str(body.get("profile_id") or "").strip()
    if not profile_id:
        return _json_error("profile_id is required.", 400)

    try:
        revoke_profile(_resolve_profile_store(), profile_id)
    except ValueError as exc:
        return _json_error(str(exc), 400)

    return jsonify({"status": "ok", "revoked": True})


def _map_canary_validation(canary_result: dict[str, Any]) -> str:
    raw_status = str(canary_result.get("status") or "").strip().lower()
    if raw_status in _SUPPORTED_PROFILE_VALIDATION_STATES:
        return raw_status
    if raw_status in {"runtime_unavailable", "runtime_error", "timeout"}:
        return "unreachable"

    detail = (
        f"{canary_result.get('error', '')} {canary_result.get('message', '')}"
    ).lower()
    if "expired" in detail:
        return "expired"
    if "unsupported" in detail:
        return "unsupported"
    return "invalid"


@gateway_bp.post("/v1/profiles/upsert")
def upsert_profile():
    """Create or update a gateway profile token and validate it with runtime canary."""
    body = request.get_json(silent=True)
    if body is None:
        body = {}
    if not isinstance(body, dict):
        return _json_error("Request body must be a JSON object.", 400)

    raw_profile_id = str(body.get("profile_id") or "")
    token = str(body.get("token") or "").strip()
    status = str(body.get("status") or "active").strip().lower()

    if not raw_profile_id.strip():
        return _json_error(
            "Validation failed.",
            400,
            details={"profile_id": "profile_id is required"},
        )

    profile_id = normalize_profile_id(raw_profile_id)
    if not profile_id:
        return _json_error(
            "Validation failed.",
            400,
            details={
                "profile_id": (
                    "profile_id must use lowercase letters, numbers, and hyphens only"
                )
            },
        )

    if not token:
        return _json_error(
            "Validation failed.",
            400,
            details={"token": "token is required"},
        )

    existing_token = resolve_stored_profile_token(
        profile_id,
        profile_store=_resolve_profile_token_store(),
    )

    try:
        record = upsert_profile_record(profile_id, token, status=status)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except Exception as exc:
        safe_message = redact_token_like_text(str(exc) or "Profile upsert failed.")
        return _json_error(safe_message, 500, error_type="server_error")

    # Keep in-memory mirrors hot for fast lookups in validate/revoke routes.
    token_store = _resolve_profile_token_store()
    token_store[profile_id] = {
        "profile_id": record.profile_id,
        "encrypted_token": record.encrypted_token,
        "status": record.status,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
    _resolve_profile_store()[profile_id] = {
        "profile_id": record.profile_id,
        "status": record.status,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }

    raw_timeout = current_app.config.get("GATEWAY_RUNTIME_CANARY_TIMEOUT_SECONDS")
    timeout_seconds: float | None = None
    if raw_timeout is not None:
        try:
            timeout_seconds = max(1.0, float(raw_timeout))
        except (TypeError, ValueError):
            timeout_seconds = None

    canary_result = run_gateway_runtime_canary(token, timeout_seconds=timeout_seconds)
    if not isinstance(canary_result, dict):
        canary_result = {"status": "runtime_error", "message": "Invalid canary result"}

    validation = _map_canary_validation(canary_result)
    action = "updated" if existing_token else "created"
    http_status = 200 if action == "updated" else 201

    return (
        jsonify(
            {
                "status": "ok",
                "action": action,
                "profile_id": profile_id,
                "profile": {
                    "profile_id": record.profile_id,
                    "status": record.status,
                    "created_at": record.created_at,
                    "updated_at": record.updated_at,
                },
                "profile_status": record.status,
                "token_status": validation,
                "validation": validation,
                "detail": canary_result,
            }
        ),
        http_status,
    )


@gateway_bp.post("/v1/profiles/validate")
def validate_profile():
    """Validate a stored setup-token profile with a runtime canary."""
    body = request.get_json(silent=True)
    if body is None:
        body = {}
    if not isinstance(body, dict):
        return _json_error("Request body must be a JSON object.", 400)

    raw_profile_id = str(body.get("profile_id") or "")
    if not raw_profile_id.strip():
        return _json_error(
            "Validation failed.",
            400,
            details={"profile_id": "profile_id is required"},
        )

    profile_id = normalize_profile_id(raw_profile_id)
    if not profile_id:
        return _json_error(
            "Validation failed.",
            400,
            details={
                "profile_id": (
                    "profile_id must use lowercase letters, numbers, and hyphens only"
                )
            },
        )

    profile_store = current_app.config.get("PROFILE_TOKEN_STORE")
    token = resolve_stored_profile_token(
        profile_id,
        profile_store=profile_store if isinstance(profile_store, Mapping) else None,
    )
    if not token:
        return _json_error(
            "Validation failed.",
            400,
            details={"token": f"No token configured for profile: {profile_id}"},
        )

    raw_timeout = current_app.config.get("GATEWAY_RUNTIME_CANARY_TIMEOUT_SECONDS")
    timeout_seconds: float | None = None
    if raw_timeout is not None:
        try:
            timeout_seconds = max(1.0, float(raw_timeout))
        except (TypeError, ValueError):
            timeout_seconds = None

    canary_result = run_gateway_runtime_canary(token, timeout_seconds=timeout_seconds)
    if not isinstance(canary_result, dict):
        canary_result = {"status": "runtime_error", "message": "Invalid canary result"}

    return jsonify(
        {
            "status": "ok",
            "profile_id": profile_id,
            "validation": _map_canary_validation(canary_result),
            "detail": canary_result,
        }
    )


@gateway_bp.post("/v1/responses")
def create_response():
    """OpenAI-compatible responses endpoint with stream/non-stream modes."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        _log_gateway_event("gateway.responses", "error", reason="invalid_json_body")
        return _json_error("Request body must be a JSON object.", 400)

    stream_mode = body.get("stream") is True
    _log_gateway_event("gateway.responses", "received", stream=stream_mode)

    try:
        gateway_fields = normalize_gateway_request_fields(body)
    except ValueError as exc:
        return _json_error(str(exc), 400)

    try:
        upstream_payload = build_anthropic_messages_payload(
            body,
            default_model=str(current_app.config["DEFAULT_ANTHROPIC_MODEL"]),
            default_max_tokens=int(current_app.config["DEFAULT_MAX_OUTPUT_TOKENS"]),
        )
    except ValueError as exc:
        _log_gateway_event(
            "gateway.responses", "error", reason="invalid_request", detail=str(exc)
        )
        return _json_error(str(exc), 400)

    runtime_token = (request.headers.get("X-Anthropic-Api-Key") or "").strip()
    normalized_profile_id = normalize_profile_id(str(gateway_fields["profile_id"] or ""))
    if not runtime_token and normalized_profile_id:
        runtime_token = (
            resolve_stored_profile_token(
                normalized_profile_id,
                profile_store=_resolve_profile_token_store(),
            )
            or ""
        ).strip()

    if is_setup_token(runtime_token):
        correlation_id = get_correlation_id()
        base_url = str(current_app.config["ANTHROPIC_BASE_URL"]).rstrip("/")
        timeout_seconds = float(current_app.config["UPSTREAM_REQUEST_TIMEOUT_SECONDS"])
        oauth_headers: dict[str, str] = {
            "authorization": f"Bearer {runtime_token}",
            "anthropic-version": str(current_app.config["ANTHROPIC_API_VERSION"]),
            "anthropic-beta": (
                "claude-code-20250219,"
                "oauth-2025-04-20,"
                "fine-grained-tool-streaming-2025-05-14,"
                "interleaved-thinking-2025-05-14"
            ),
            "content-type": "application/json",
            "accept": "application/json",
            "x-aiaa-cwd": str(gateway_fields["cwd"]),
            "x-aiaa-tools-profile": str(gateway_fields["tools_profile"]),
        }
        if correlation_id:
            oauth_headers[CORRELATION_HEADER] = correlation_id
            oauth_headers[REQUEST_ID_HEADER] = correlation_id
        if gateway_fields["profile_id"]:
            oauth_headers["x-aiaa-profile-id"] = str(gateway_fields["profile_id"])
        if gateway_fields["session_id"]:
            oauth_headers["x-aiaa-session-id"] = str(gateway_fields["session_id"])

        oauth_response: Any | None = None
        oauth_failed_with_unsupported_auth = False
        try:
            if stream_mode:
                oauth_headers["accept"] = "text/event-stream"
                upstream_payload["stream"] = True
                oauth_response = http_requests.post(
                    f"{base_url}/v1/messages",
                    json=upstream_payload,
                    headers=oauth_headers,
                    timeout=timeout_seconds,
                    stream=True,
                )
                if oauth_response.status_code < 400:
                    _log_gateway_event(
                        "gateway.responses",
                        "success",
                        stream=True,
                        backend="anthropic_oauth",
                    )
                    response = Response(
                        stream_with_context(
                            _stream_openai_response_events(
                                oauth_response,
                                requested_model=str(upstream_payload["model"]),
                            )
                        ),
                        mimetype="text/event-stream",
                    )
                    response.headers["Cache-Control"] = "no-cache"
                    response.headers["X-Accel-Buffering"] = "no"
                    response.headers["Connection"] = "keep-alive"
                    return response
            else:
                oauth_response = http_requests.post(
                    f"{base_url}/v1/messages",
                    json=upstream_payload,
                    headers=oauth_headers,
                    timeout=timeout_seconds,
                )
                if oauth_response.status_code < 400:
                    try:
                        upstream_json = oauth_response.json()
                    except ValueError:
                        return _json_error(
                            "Upstream provider returned non-JSON response.",
                            502,
                            error_type="upstream_error",
                        )
                    if not isinstance(upstream_json, dict):
                        return _json_error(
                            "Upstream provider returned invalid payload.",
                            502,
                            error_type="upstream_error",
                        )
                    response_payload = map_anthropic_to_response(
                        upstream_payload=upstream_json,
                        requested_model=str(upstream_payload["model"]),
                    )
                    _log_gateway_event(
                        "gateway.responses",
                        "success",
                        stream=False,
                        backend="anthropic_oauth",
                    )
                    return jsonify(response_payload)
        except http_requests.RequestException as exc:
            safe_error = redact_exception_message(exc)
            _log_gateway_event(
                "gateway.responses",
                "error",
                reason="upstream_request_failed",
                detail=safe_error,
                stream=stream_mode,
                backend="anthropic_oauth",
            )
            return _json_error(
                f"Upstream provider request failed: {safe_error}",
                502,
                error_type="upstream_error",
            )

        details: dict[str, Any] = {}
        if oauth_response is not None:
            details = _parse_upstream_error_details(oauth_response)
            close = getattr(oauth_response, "close", None)
            if callable(close):
                close()
            error_blob = json.dumps(details, ensure_ascii=False).lower()
            oauth_failed_with_unsupported_auth = (
                "oauth authentication is currently not supported" in error_blob
            )

        if not oauth_failed_with_unsupported_auth:
            _log_gateway_event(
                "gateway.responses",
                "error",
                reason="upstream_error",
                upstream_status=(
                    getattr(oauth_response, "status_code", None) if oauth_response else None
                ),
                stream=stream_mode,
                backend="anthropic_oauth",
            )
            return _json_error(
                "Upstream provider returned an error.",
                502,
                error_type="upstream_error",
                details=details,
            )

        runtime_result = run_gateway_runtime_query(
            token=runtime_token,
            messages=list(upstream_payload.get("messages") or []),
            cwd=str(gateway_fields["cwd"]),
            timeout_seconds=timeout_seconds,
            model=str(upstream_payload.get("model") or ""),
            system_prompt=str(upstream_payload.get("system") or "").strip() or None,
            session_id=str(gateway_fields["session_id"] or "").strip() or None,
        )
        runtime_status = str(runtime_result.get("status") or "").strip().lower()
        if runtime_status != "ok":
            detail = redact_token_like_text(
                str(runtime_result.get("error") or runtime_result.get("message") or "").strip()
            )
            reason = runtime_status or "runtime_error"
            if reason == "invalid_request":
                status_code = 400
            elif reason == "runtime_unavailable":
                status_code = 503
            elif reason == "timeout":
                status_code = 504
            else:
                status_code = 502
            _log_gateway_event(
                "gateway.responses",
                "error",
                reason=reason,
                detail=detail,
                stream=stream_mode,
                backend="claude_runtime",
            )
            return _json_error(
                detail or "Claude runtime execution failed.",
                status_code,
                error_type="upstream_error",
            )

        response_text = str(runtime_result.get("output_text") or "").strip()
        response_model = (
            str(runtime_result.get("model") or "").strip()
            or str(upstream_payload.get("model") or "").strip()
            or str(current_app.config["DEFAULT_ANTHROPIC_MODEL"])
        )
        _log_gateway_event(
            "gateway.responses",
            "success",
            stream=stream_mode,
            backend="claude_runtime",
        )
        if stream_mode:
            response = Response(
                stream_with_context(
                    _stream_runtime_response_events(response_text, model=response_model)
                ),
                mimetype="text/event-stream",
            )
            response.headers["Cache-Control"] = "no-cache"
            response.headers["X-Accel-Buffering"] = "no"
            response.headers["Connection"] = "keep-alive"
            return response
        return jsonify(_runtime_text_to_response_payload(response_text, model=response_model))

    api_key = _resolve_anthropic_api_key()
    if not api_key:
        _log_gateway_event("gateway.responses", "error", reason="missing_api_key")
        return _json_error(
            "Missing Anthropic API key.",
            401,
            error_type="authentication_error",
        )

    correlation_id = get_correlation_id()
    base_url = str(current_app.config["ANTHROPIC_BASE_URL"]).rstrip("/")
    timeout_seconds = float(current_app.config["UPSTREAM_REQUEST_TIMEOUT_SECONDS"])
    headers: dict[str, str] = {
        "x-api-key": api_key,
        "anthropic-version": str(current_app.config["ANTHROPIC_API_VERSION"]),
        "content-type": "application/json",
        "accept": "application/json",
        "x-aiaa-cwd": str(gateway_fields["cwd"]),
        "x-aiaa-tools-profile": str(gateway_fields["tools_profile"]),
    }
    if correlation_id:
        headers[CORRELATION_HEADER] = correlation_id
        headers[REQUEST_ID_HEADER] = correlation_id
    if gateway_fields["profile_id"]:
        headers["x-aiaa-profile-id"] = str(gateway_fields["profile_id"])
    if gateway_fields["session_id"]:
        headers["x-aiaa-session-id"] = str(gateway_fields["session_id"])

    if stream_mode:
        headers["accept"] = "text/event-stream"
        upstream_payload["stream"] = True
        try:
            upstream_response = http_requests.post(
                f"{base_url}/v1/messages",
                json=upstream_payload,
                headers=headers,
                timeout=timeout_seconds,
                stream=True,
            )
        except http_requests.RequestException as exc:
            safe_error = redact_exception_message(exc)
            logger.error("Upstream provider request failed: %s", safe_error)
            _log_gateway_event(
                "gateway.responses",
                "error",
                reason="upstream_request_failed",
                detail=safe_error,
                stream=True,
            )
            return _json_error(
                f"Upstream provider request failed: {safe_error}",
                502,
                error_type="upstream_error",
            )

        if upstream_response.status_code >= 400:
            details = _parse_upstream_error_details(upstream_response)
            close = getattr(upstream_response, "close", None)
            if callable(close):
                close()
            _log_gateway_event(
                "gateway.responses",
                "error",
                reason="upstream_error",
                upstream_status=upstream_response.status_code,
                stream=True,
            )
            return _json_error(
                "Upstream provider returned an error.",
                502,
                error_type="upstream_error",
                details=details,
            )

        response = Response(
            stream_with_context(
                _stream_openai_response_events(
                    upstream_response,
                    requested_model=str(upstream_payload["model"]),
                )
            ),
            mimetype="text/event-stream",
        )
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"
        response.headers["Connection"] = "keep-alive"
        _log_gateway_event("gateway.responses", "success", stream=True)
        return response

    headers["accept"] = "application/json"
    try:
        upstream_response = http_requests.post(
            f"{base_url}/v1/messages",
            json=upstream_payload,
            headers=headers,
            timeout=timeout_seconds,
        )
    except http_requests.RequestException as exc:
        safe_error = redact_exception_message(exc)
        logger.error("Upstream provider request failed: %s", safe_error)
        _log_gateway_event(
            "gateway.responses",
            "error",
            reason="upstream_request_failed",
            detail=safe_error,
            stream=False,
        )
        return _json_error(
            f"Upstream provider request failed: {safe_error}",
            502,
            error_type="upstream_error",
        )

    if upstream_response.status_code >= 400:
        _log_gateway_event(
            "gateway.responses",
            "error",
            reason="upstream_error",
            upstream_status=upstream_response.status_code,
            stream=False,
        )
        return _json_error(
            "Upstream provider returned an error.",
            502,
            error_type="upstream_error",
            details=_parse_upstream_error_details(upstream_response),
        )

    try:
        upstream_json = upstream_response.json()
    except ValueError:
        _log_gateway_event(
            "gateway.responses",
            "error",
            reason="upstream_non_json_payload",
            stream=False,
        )
        return _json_error(
            "Upstream provider returned non-JSON response.",
            502,
            error_type="upstream_error",
        )

    if not isinstance(upstream_json, dict):
        _log_gateway_event(
            "gateway.responses",
            "error",
            reason="upstream_invalid_payload_type",
            stream=False,
        )
        return _json_error(
            "Upstream provider returned invalid payload.",
            502,
            error_type="upstream_error",
        )

    response_payload = map_anthropic_to_response(
        upstream_payload=upstream_json,
        requested_model=str(upstream_payload["model"]),
    )
    _log_gateway_event("gateway.responses", "success", stream=False)
    return jsonify(response_payload)
