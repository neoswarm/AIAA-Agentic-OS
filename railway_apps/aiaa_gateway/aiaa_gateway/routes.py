"""HTTP routes for AIAA Gateway."""

from __future__ import annotations

import hashlib
import os
import secrets
import threading
import time
from collections import deque
from datetime import UTC, datetime
from typing import Any

import requests as http_requests
from flask import Blueprint, current_app, jsonify, request

from .services.responses_service import (
    build_anthropic_messages_payload,
    map_anthropic_to_response,
)

gateway_bp = Blueprint("gateway", __name__)
_auth_failure_lock = threading.RLock()
_auth_failure_windows: dict[str, deque[float]] = {}


def _json_error(
    message: str,
    status_code: int,
    *,
    error_type: str = "invalid_request_error",
    details: dict[str, Any] | None = None,
):
    payload: dict[str, Any] = {
        "error": {
            "type": error_type,
            "message": message,
        }
    }
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status_code


def _resolve_anthropic_api_key() -> str:
    header_key = (request.headers.get("X-Anthropic-Api-Key") or "").strip()
    if header_key:
        return header_key

    gateway_api_key = (current_app.config.get("GATEWAY_API_KEY") or "").strip()
    auth_header = (request.headers.get("Authorization") or "").strip()
    if not gateway_api_key and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    configured = (current_app.config.get("ANTHROPIC_API_KEY") or "").strip()
    if configured:
        return configured
    return (os.getenv("ANTHROPIC_API_KEY") or "").strip()


def _extract_bearer_token() -> str:
    auth_header = (request.headers.get("Authorization") or "").strip()
    if not auth_header.lower().startswith("bearer "):
        return ""
    return auth_header[7:].strip()


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


def _require_gateway_bearer_auth():
    expected_token = (current_app.config.get("GATEWAY_API_KEY") or "").strip()
    if not expected_token:
        return None

    provided_token = _extract_bearer_token()
    if not provided_token:
        response, status_code = _json_error(
            "Missing gateway bearer token.",
            401,
            error_type="authentication_error",
        )
        response.headers["WWW-Authenticate"] = "Bearer"
        return response, status_code

    throttled, retry_after, limit, window_seconds = _is_auth_failure_throttled(
        provided_token
    )
    if throttled:
        response, status_code = _json_error(
            "Too many invalid gateway bearer token attempts.",
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

    if not secrets.compare_digest(provided_token, expected_token):
        _record_auth_failure(provided_token)
        throttled, retry_after, limit, window_seconds = _is_auth_failure_throttled(
            provided_token
        )
        if throttled:
            response, status_code = _json_error(
                "Too many invalid gateway bearer token attempts.",
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
            "Invalid gateway bearer token.",
            401,
            error_type="authentication_error",
        )
        response.headers["WWW-Authenticate"] = "Bearer"
        return response, status_code

    return None


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
    return jsonify(
        {
            "service": current_app.config["SERVICE_NAME"],
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )


@gateway_bp.post("/v1/responses")
def create_response():
    """OpenAI-compatible responses endpoint (non-stream mode only)."""
    auth_failure = _require_gateway_bearer_auth()
    if auth_failure is not None:
        return auth_failure

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _json_error("Request body must be a JSON object.", 400)

    if body.get("stream") is True:
        return _json_error(
            "stream=true is not supported on POST /v1/responses in non-stream mode.",
            400,
        )

    try:
        upstream_payload = build_anthropic_messages_payload(
            body,
            default_model=str(current_app.config["DEFAULT_ANTHROPIC_MODEL"]),
            default_max_tokens=int(current_app.config["DEFAULT_MAX_OUTPUT_TOKENS"]),
        )
    except ValueError as exc:
        return _json_error(str(exc), 400)

    api_key = _resolve_anthropic_api_key()
    if not api_key:
        return _json_error(
            "Missing Anthropic API key.",
            401,
            error_type="authentication_error",
        )

    base_url = str(current_app.config["ANTHROPIC_BASE_URL"]).rstrip("/")
    timeout_seconds = float(current_app.config["UPSTREAM_REQUEST_TIMEOUT_SECONDS"])
    headers = {
        "x-api-key": api_key,
        "anthropic-version": str(current_app.config["ANTHROPIC_API_VERSION"]),
        "content-type": "application/json",
        "accept": "application/json",
    }

    try:
        upstream_response = http_requests.post(
            f"{base_url}/v1/messages",
            json=upstream_payload,
            headers=headers,
            timeout=timeout_seconds,
        )
    except http_requests.RequestException as exc:
        return _json_error(
            f"Upstream provider request failed: {exc}",
            502,
            error_type="upstream_error",
        )

    if upstream_response.status_code >= 400:
        details: dict[str, Any]
        try:
            parsed = upstream_response.json()
            details = parsed if isinstance(parsed, dict) else {"body": parsed}
        except ValueError:
            details = {
                "body": upstream_response.text.strip() or "Unknown upstream error"
            }
        return _json_error(
            "Upstream provider returned an error.",
            502,
            error_type="upstream_error",
            details={"upstream_status": upstream_response.status_code, **details},
        )

    try:
        upstream_json = upstream_response.json()
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
    return jsonify(response_payload)
