"""HTTP routes for AIAA Gateway."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

import requests as http_requests
from flask import Blueprint, current_app, jsonify, request

from .redaction import redact_exception_message, redact_token_like_text
from .services.responses_service import (
    build_anthropic_messages_payload,
    map_anthropic_to_response,
)

gateway_bp = Blueprint("gateway", __name__)
logger = logging.getLogger(__name__)


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
    return jsonify(payload), status_code


def _resolve_anthropic_api_key() -> str:
    header_key = (request.headers.get("X-Anthropic-Api-Key") or "").strip()
    if header_key:
        return header_key

    auth_header = (request.headers.get("Authorization") or "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    configured = (current_app.config.get("ANTHROPIC_API_KEY") or "").strip()
    if configured:
        return configured
    return (os.getenv("ANTHROPIC_API_KEY") or "").strip()


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
        safe_error = redact_exception_message(exc)
        logger.error("Upstream provider request failed: %s", safe_error)
        return _json_error(
            f"Upstream provider request failed: {safe_error}",
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
