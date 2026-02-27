"""HTTP routes for AIAA Gateway."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import time
import uuid
from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests as http_requests
from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    request,
    stream_with_context,
)

from .services.profile_service import revoke_profile
from .services.responses_service import (
    build_anthropic_messages_payload,
    map_anthropic_to_response,
)
from .services.profile_service import normalize_profile_id, resolve_stored_profile_token
from .services.runtime_canary import run_gateway_runtime_canary

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

    auth_header = (request.headers.get("Authorization") or "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    configured = (current_app.config.get("ANTHROPIC_API_KEY") or "").strip()
    if configured:
        return configured
    return (os.getenv("ANTHROPIC_API_KEY") or "").strip()


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


def _resolve_internal_gateway_token() -> str:
    configured = (current_app.config.get("GATEWAY_INTERNAL_TOKEN") or "").strip()
    if configured:
        return configured
    return (os.getenv("GATEWAY_INTERNAL_TOKEN") or "").strip()


def _require_internal_bearer_auth():
    expected_token = _resolve_internal_gateway_token()
    if not expected_token:
        return None

    auth_header = (request.headers.get("Authorization") or "").strip()
    if not auth_header.lower().startswith("bearer "):
        return _json_error(
            "Missing gateway bearer token.",
            401,
            error_type="authentication_error",
        )

    provided_token = auth_header[7:].strip()
    if not provided_token or not secrets.compare_digest(provided_token, expected_token):
        return _json_error(
            "Invalid gateway bearer token.",
            401,
            error_type="authentication_error",
        )
    return None


def _resolve_profile_store() -> MutableMapping[str, dict[str, Any]]:
    store = current_app.config.get("PROFILE_STORE")
    if isinstance(store, MutableMapping):
        return store

    initialized_store: dict[str, dict[str, Any]] = {}
    current_app.config["PROFILE_STORE"] = initialized_store
    return initialized_store


def _format_sse_data(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        return f"data: {payload}\n\n"
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


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

            if event_type == "content_block_delta":
                delta = event.get("delta")
                if not isinstance(delta, Mapping):
                    continue
                if delta.get("type") != "text_delta":
                    continue
                text_chunk = delta.get("text")
                if not isinstance(text_chunk, str) or not text_chunk:
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
    auth_error = _require_internal_bearer_auth()
    if auth_error is not None:
        return auth_error

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
        return _json_error("Request body must be a JSON object.", 400)
    stream_mode = body.get("stream") is True

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
    headers: dict[str, str] = {
        "x-api-key": api_key,
        "anthropic-version": str(current_app.config["ANTHROPIC_API_VERSION"]),
        "content-type": "application/json",
    }
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
            return _json_error(
                f"Upstream provider request failed: {exc}",
                502,
                error_type="upstream_error",
            )

        if upstream_response.status_code >= 400:
            details = _parse_upstream_error_details(upstream_response)
            close = getattr(upstream_response, "close", None)
            if callable(close):
                close()
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
        return _json_error(
            f"Upstream provider request failed: {exc}",
            502,
            error_type="upstream_error",
        )

    if upstream_response.status_code >= 400:
        return _json_error(
            "Upstream provider returned an error.",
            502,
            error_type="upstream_error",
            details=_parse_upstream_error_details(upstream_response),
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
