"""Helpers for OpenAI Responses compatibility on top of Anthropic Messages."""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from typing import Any


def _coerce_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, Mapping):
        text = content.get("text")
        if isinstance(text, str):
            return text.strip()
        value = content.get("content")
        if isinstance(value, str):
            return value.strip()
        return ""

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                value = item.strip()
                if value:
                    parts.append(value)
                continue
            if not isinstance(item, Mapping):
                continue
            text = item.get("text")
            if not isinstance(text, str):
                text = (
                    item.get("content") if isinstance(item.get("content"), str) else ""
                )
            text = text.strip()
            if text:
                parts.append(text)
        return "\n".join(parts).strip()

    return ""


def _normalize_input_to_messages(request_input: Any) -> list[dict[str, str]]:
    if isinstance(request_input, str):
        text = request_input.strip()
        return [{"role": "user", "content": text}] if text else []

    if not isinstance(request_input, list):
        return []

    messages: list[dict[str, str]] = []
    for item in request_input:
        if isinstance(item, str):
            text_value = item.strip()
            if text_value:
                messages.append({"role": "user", "content": text_value})
            continue
        if not isinstance(item, Mapping):
            continue

        role_value = item.get("role")
        role = str(role_value).strip().lower() if role_value is not None else "user"
        if role not in {"user", "assistant"}:
            role = "user"

        text_value = _coerce_content_to_text(item.get("content"))
        if not text_value:
            text_value = _coerce_content_to_text(item.get("input_text"))
        if not text_value:
            continue

        messages.append({"role": role, "content": text_value})

    return messages


def build_anthropic_messages_payload(
    body: Mapping[str, Any],
    *,
    default_model: str,
    default_max_tokens: int,
) -> dict[str, Any]:
    """Validate and convert /v1/responses payload into Anthropic /v1/messages."""
    model = str(body.get("model") or default_model).strip()
    if not model:
        raise ValueError("model is required.")

    if "input" not in body:
        raise ValueError("input is required.")

    messages = _normalize_input_to_messages(body.get("input"))
    if not messages:
        raise ValueError("input must contain at least one message.")

    raw_max_tokens = body.get(
        "max_output_tokens", body.get("max_tokens", default_max_tokens)
    )
    try:
        max_tokens = int(raw_max_tokens)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_output_tokens must be an integer.") from exc
    if max_tokens <= 0:
        raise ValueError("max_output_tokens must be greater than 0.")

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }

    instructions = body.get("instructions")
    if isinstance(instructions, str) and instructions.strip():
        payload["system"] = instructions.strip()

    temperature = body.get("temperature")
    if temperature is not None:
        try:
            payload["temperature"] = float(temperature)
        except (TypeError, ValueError) as exc:
            raise ValueError("temperature must be a number.") from exc

    return payload


def _extract_output_text(content_blocks: Any) -> str:
    if not isinstance(content_blocks, list):
        return ""

    parts: list[str] = []
    for block in content_blocks:
        if not isinstance(block, Mapping):
            continue
        if block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str):
            text = text.strip()
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def _extract_normalized_output_text(output_blocks: Any) -> str:
    if not isinstance(output_blocks, list):
        return ""

    parts: list[str] = []
    for block in output_blocks:
        if not isinstance(block, Mapping):
            continue

        if block.get("type") == "output_text":
            text = block.get("text")
            if isinstance(text, str):
                text = text.strip()
                if text:
                    parts.append(text)

        content = block.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, Mapping):
                continue
            item_type = item.get("type")
            if item_type not in {"output_text", "text"}:
                continue
            text = item.get("text")
            if isinstance(text, str):
                text = text.strip()
                if text:
                    parts.append(text)

    return "\n".join(parts).strip()


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def map_anthropic_to_response(
    *,
    upstream_payload: Mapping[str, Any],
    requested_model: str,
) -> dict[str, Any]:
    """Map Anthropic Messages output into OpenAI Responses schema."""
    output_text = _extract_output_text(upstream_payload.get("content"))
    if not output_text:
        raw_output_text = upstream_payload.get("output_text")
        if isinstance(raw_output_text, str):
            output_text = raw_output_text.strip()
    if not output_text:
        output_text = _extract_normalized_output_text(upstream_payload.get("output"))

    usage_raw = upstream_payload.get("usage")
    usage = usage_raw if isinstance(usage_raw, Mapping) else {}

    input_tokens = _coerce_int(usage.get("input_tokens"))
    output_tokens = _coerce_int(usage.get("output_tokens"))

    response_id = str(upstream_payload.get("id") or f"resp_{uuid.uuid4().hex}")
    message_id = f"msg_{uuid.uuid4().hex}"
    created_at = _coerce_int(upstream_payload.get("created_at")) or int(time.time())

    output_raw = upstream_payload.get("output")
    if isinstance(output_raw, list) and output_raw:
        output = list(output_raw)
    else:
        output = [
            {
                "id": message_id,
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": output_text,
                        "annotations": [],
                    }
                ],
            }
        ]

    return {
        "id": response_id,
        "object": "response",
        "created_at": created_at,
        "status": str(upstream_payload.get("status") or "completed"),
        "model": str(upstream_payload.get("model") or requested_model),
        "output": output,
        "output_text": output_text,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    }
