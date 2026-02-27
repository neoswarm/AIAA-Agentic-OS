"""Helpers for OpenAI Responses compatibility on top of Anthropic Messages."""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from typing import Any

DEFAULT_GATEWAY_CWD = "/app"
DEFAULT_TOOLS_PROFILE = "full"


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


def normalize_gateway_request_fields(
    body: Mapping[str, Any],
    *,
    default_cwd: str = DEFAULT_GATEWAY_CWD,
    default_tools_profile: str = DEFAULT_TOOLS_PROFILE,
) -> dict[str, str | None]:
    """Validate and normalize gateway request fields carried by /v1/responses."""
    profile_id_raw = body.get("profile_id")
    if profile_id_raw is None:
        profile_id = None
    elif isinstance(profile_id_raw, str):
        profile_id = profile_id_raw.strip() or None
    else:
        raise ValueError("profile_id must be a string when provided.")

    session_id_raw = body.get("session_id")
    if session_id_raw is None:
        session_id = None
    elif isinstance(session_id_raw, str):
        session_id = session_id_raw.strip() or None
    else:
        raise ValueError("session_id must be a string when provided.")

    cwd_raw = body.get("cwd")
    if cwd_raw is None:
        cwd = default_cwd
    elif isinstance(cwd_raw, str):
        cwd = cwd_raw.strip() or default_cwd
    else:
        raise ValueError("cwd must be a string when provided.")

    tools_profile_raw = body.get("tools_profile")
    if tools_profile_raw is None:
        tools_profile = default_tools_profile
    elif isinstance(tools_profile_raw, str):
        tools_profile = tools_profile_raw.strip() or default_tools_profile
    else:
        raise ValueError("tools_profile must be a string when provided.")

    return {
        "profile_id": profile_id,
        "session_id": session_id,
        "cwd": cwd,
        "tools_profile": tools_profile,
    }


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
