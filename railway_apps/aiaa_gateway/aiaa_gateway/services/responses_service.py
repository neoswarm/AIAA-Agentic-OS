"""Helpers for OpenAI Responses compatibility on top of Anthropic Messages."""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from typing import Any


_TEXT_BLOCK_TYPES = {"text", "input_text", "output_text"}


def _coerce_content_to_text(content: Any) -> tuple[str, bool]:
    if isinstance(content, str):
        return content.strip(), False

    if isinstance(content, Mapping):
        block_type = content.get("type")
        if block_type is not None:
            normalized_type = str(block_type).strip().lower()
            if normalized_type and normalized_type not in _TEXT_BLOCK_TYPES:
                return "", True

        text = content.get("text")
        if isinstance(text, str):
            return text.strip(), False
        value = content.get("content")
        if isinstance(value, str):
            return value.strip(), False
        return "", False

    if isinstance(content, list):
        parts: list[str] = []
        saw_unsupported = False
        for item in content:
            if isinstance(item, str):
                value = item.strip()
                if value:
                    parts.append(value)
                continue
            if isinstance(item, Mapping):
                text, unsupported = _coerce_content_to_text(item)
                if text:
                    parts.append(text)
                saw_unsupported = saw_unsupported or unsupported
                continue
            if item is not None:
                saw_unsupported = True
        return "\n".join(parts).strip(), saw_unsupported

    if content is None:
        return "", False

    return "", True


def _normalize_input_to_messages(
    request_input: Any,
) -> tuple[list[dict[str, str]], bool]:
    if isinstance(request_input, str):
        text = request_input.strip()
        return ([{"role": "user", "content": text}] if text else []), False

    if not isinstance(request_input, list):
        return [], request_input is not None

    messages: list[dict[str, str]] = []
    saw_unsupported = False
    for item in request_input:
        if isinstance(item, str):
            text_value = item.strip()
            if text_value:
                messages.append({"role": "user", "content": text_value})
            continue
        if not isinstance(item, Mapping):
            if item is not None:
                saw_unsupported = True
            continue

        role_value = item.get("role")
        role = str(role_value).strip().lower() if role_value is not None else "user"
        if role not in {"user", "assistant"}:
            role = "user"

        text_value, unsupported = _coerce_content_to_text(item.get("content"))
        saw_unsupported = saw_unsupported or unsupported
        if not text_value:
            text_value, unsupported = _coerce_content_to_text(item.get("input_text"))
            saw_unsupported = saw_unsupported or unsupported
        if not text_value and "text" in item:
            text_value, unsupported = _coerce_content_to_text(item.get("text"))
            saw_unsupported = saw_unsupported or unsupported
        if not text_value:
            if not any(key in item for key in ("content", "input_text", "text")):
                saw_unsupported = True
            continue

        messages.append({"role": role, "content": text_value})

    return messages, saw_unsupported


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

    messages, saw_unsupported = _normalize_input_to_messages(body.get("input"))
    if saw_unsupported:
        raise ValueError(
            "input contains unsupported content. Only text input is supported."
        )
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


def map_anthropic_to_response(
    *,
    upstream_payload: Mapping[str, Any],
    requested_model: str,
) -> dict[str, Any]:
    """Map Anthropic Messages output into OpenAI Responses schema."""
    output_text = _extract_output_text(upstream_payload.get("content"))
    usage_raw = upstream_payload.get("usage")
    usage = usage_raw if isinstance(usage_raw, Mapping) else {}

    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)

    response_id = str(upstream_payload.get("id") or f"resp_{uuid.uuid4().hex}")
    message_id = f"msg_{uuid.uuid4().hex}"

    return {
        "id": response_id,
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "model": str(upstream_payload.get("model") or requested_model),
        "output": [
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
        ],
        "output_text": output_text,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    }
