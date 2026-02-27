"""HTTP routes for AIAA Gateway."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import UTC, datetime
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

from .services.responses_service import (
    build_anthropic_messages_payload,
    map_anthropic_to_response,
)

gateway_bp = Blueprint("gateway", __name__)


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


def _format_sse_data(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


def _iter_upstream_sse_events(upstream_response: Any):
    for raw_line in upstream_response.iter_lines(decode_unicode=True):
        if raw_line is None:
            continue
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        data_payload = line[5:].strip()
        if not data_payload or data_payload == "[DONE]":
            continue
        try:
            parsed = json.loads(data_payload)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            yield parsed


def _extract_text_delta(stream_event: dict[str, Any]) -> str:
    event_type = str(stream_event.get("type") or "")
    if event_type == "content_block_delta":
        delta = stream_event.get("delta")
        if isinstance(delta, dict) and str(delta.get("type") or "") == "text_delta":
            text = delta.get("text")
            return text if isinstance(text, str) else ""
        return ""

    if event_type == "content_block_start":
        block = stream_event.get("content_block")
        if isinstance(block, dict) and str(block.get("type") or "") == "text":
            text = block.get("text")
            return text if isinstance(text, str) else ""

    return ""


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
    """OpenAI-compatible responses endpoint."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _json_error("Request body must be a JSON object.", 400)
    stream_requested = body.get("stream") is True

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
        "accept": "text/event-stream" if stream_requested else "application/json",
    }
    request_payload = dict(upstream_payload)
    if stream_requested:
        request_payload["stream"] = True

    try:
        upstream_response = http_requests.post(
            f"{base_url}/v1/messages",
            json=request_payload,
            headers=headers,
            timeout=timeout_seconds,
            stream=stream_requested,
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

    if stream_requested:
        response_id = f"resp_{uuid.uuid4().hex}"
        created_at = int(time.time())
        requested_model = str(upstream_payload["model"])

        def stream_chunks():
            text_parts: list[str] = []
            try:
                yield _format_sse_data(
                    {
                        "type": "response.created",
                        "response": {
                            "id": response_id,
                            "object": "response",
                            "created": created_at,
                            "model": requested_model,
                            "status": "in_progress",
                            "output": [],
                        },
                    }
                )
                for stream_event in _iter_upstream_sse_events(upstream_response):
                    event_type = str(stream_event.get("type") or "")
                    text_delta = _extract_text_delta(stream_event)
                    if text_delta:
                        text_parts.append(text_delta)
                        yield _format_sse_data(
                            {
                                "type": "response.output_text.delta",
                                "response_id": response_id,
                                "output_index": 0,
                                "content_index": 0,
                                "delta": text_delta,
                            }
                        )
                        continue
                    if event_type == "error":
                        message = "Upstream stream failed."
                        error_obj = stream_event.get("error")
                        if isinstance(error_obj, dict):
                            error_message = error_obj.get("message")
                            if (
                                isinstance(error_message, str)
                                and error_message.strip()
                            ):
                                message = error_message.strip()
                        yield _format_sse_data(
                            {
                                "type": "response.failed",
                                "response": {
                                    "id": response_id,
                                    "object": "response",
                                    "created": created_at,
                                    "model": requested_model,
                                    "status": "failed",
                                    "error": {"message": message},
                                },
                            }
                        )
                        yield "data: [DONE]\n\n"
                        return
            except Exception as exc:
                yield _format_sse_data(
                    {
                        "type": "response.failed",
                        "response": {
                            "id": response_id,
                            "object": "response",
                            "created": created_at,
                            "model": requested_model,
                            "status": "failed",
                            "error": {"message": f"Failed to stream response: {exc}"},
                        },
                    }
                )
                yield "data: [DONE]\n\n"
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
                        "created": created_at,
                        "model": requested_model,
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
            stream_with_context(stream_chunks()),
            mimetype="text/event-stream",
        )
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"
        response.headers["Connection"] = "keep-alive"
        return response

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
