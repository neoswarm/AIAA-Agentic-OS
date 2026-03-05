"""
Gateway-backed chat runner implementing the existing runner interface contract.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from typing import Any, Dict, Generator, Mapping, Optional

from services.agent_runner import (
    AgentRunner,
    RunnerError,
    _redact_token_like_text,
    _utc_now_iso,
)
from services.gateway_client import GatewayClient

__all__ = ["GatewayRunner", "RunnerError"]


logger = logging.getLogger(__name__)


class GatewayRunner(AgentRunner):
    """Drop-in runner implementation for gateway-based chat execution."""

    RESPONSES_PATH = "/v1/responses"
    _CHUNK_ID_FIELDS = ("chunk_id", "delta_id", "event_id", "id")
    _CHUNK_SEQUENCE_FIELDS = ("chunk_index", "delta_index", "sequence", "seq", "index")
    _HISTORY_ROLES = frozenset({"user", "assistant"})
    _DEFAULT_HISTORY_LIMIT = 30
    _DEFAULT_HISTORY_MAX_CHARS = 32000
    _DEFAULT_HISTORY_MESSAGE_MAX_CHARS = 4000

    def __init__(
        self,
        cwd: str | None,
        token_provider,
        allowed_tools: Optional[list[str]] = None,
        permission_mode: str = "acceptEdits",
        session_store: Any | None = None,
        cwd_allowlist: Optional[list[str]] = None,
        gateway_client: GatewayClient | None = None,
        gateway_base_url: str | None = None,
        gateway_api_key: str | None = None,
        gateway_timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(
            cwd=cwd,
            token_provider=token_provider,
            allowed_tools=allowed_tools,
            permission_mode=permission_mode,
            session_store=session_store,
            cwd_allowlist=cwd_allowlist,
        )
        self._gateway_base_url = (gateway_base_url or os.getenv("GATEWAY_BASE_URL", "")).strip()
        self._gateway_api_key = (gateway_api_key or os.getenv("GATEWAY_API_KEY", "")).strip()
        timeout_raw = (
            gateway_timeout_seconds
            if gateway_timeout_seconds is not None
            else os.getenv("GATEWAY_REQUEST_TIMEOUT_SECONDS", "360")
        )
        try:
            self._gateway_timeout_seconds = max(1.0, float(timeout_raw))
        except (TypeError, ValueError):
            self._gateway_timeout_seconds = 120.0
        self._gateway_client = gateway_client
        self._session_aliases: Dict[str, str] = {}
        self._correlation_aliases: Dict[str, str] = {}
        self._runtime_session_ids: Dict[str, str] = {}
        self._send_guard_lock = threading.RLock()
        self._inflight_sends: set[str] = set()

    def create_session(self, title: Optional[str] = None) -> Dict[str, Any]:
        session = super().create_session(title=title)
        session_id = self._normalize_identifier(session.get("id"))
        if session_id:
            self._register_session_alias(session_id, session_id)
        return session

    def ensure_session(
        self,
        session_id: str,
        *,
        title: str | None = None,
        sdk_session_id: str | None = None,
    ) -> Dict[str, Any]:
        session = super().ensure_session(
            session_id,
            title=title,
            sdk_session_id=sdk_session_id,
        )
        self._register_session_alias(session_id, session_id)
        self._register_session_alias(session_id, sdk_session_id)
        return session

    def has_session(self, session_id: str) -> bool:
        return super().has_session(self._resolve_session_id(session_id))

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return super().get_session(self._resolve_session_id(session_id))

    def send_message(self, session_id: str, user_message: str) -> None:
        resolved_session_id = self._resolve_session_id(session_id)
        with self._send_guard_lock:
            if resolved_session_id in self._inflight_sends:
                raise RunnerError("Session is already running")
            self._inflight_sends.add(resolved_session_id)

        try:
            super().send_message(resolved_session_id, user_message)
        except Exception:
            with self._send_guard_lock:
                self._inflight_sends.discard(resolved_session_id)
            raise

    def get_stream(
        self, session_id: str, keepalive_seconds: int = 20
    ) -> Generator[str, None, None]:
        """
        Filter reconnect replay artifacts for gateway text streams.

        Gateway reconnects may replay already-delivered chunks or emit delayed
        chunks out of order. When chunk identifiers or sequence metadata are
        present, suppress duplicates and stale chunks.
        """
        seen_chunk_ids: Dict[str, set[str]] = {"text": set(), "result": set()}
        highest_sequence: Dict[str, int] = {}

        for raw_chunk in super().get_stream(
            self._resolve_session_id(session_id),
            keepalive_seconds=keepalive_seconds,
        ):
            event = self._parse_sse_payload(raw_chunk)
            if not event:
                yield raw_chunk
                continue

            event_type = str(event.get("type") or "").strip().lower()
            if event_type not in seen_chunk_ids:
                yield raw_chunk
                continue

            chunk_id = self._extract_chunk_id(event)
            if chunk_id:
                known_ids = seen_chunk_ids[event_type]
                if chunk_id in known_ids:
                    continue
                known_ids.add(chunk_id)

            chunk_sequence = self._extract_chunk_sequence(event)
            if chunk_sequence is not None:
                latest = highest_sequence.get(event_type)
                if latest is not None and chunk_sequence <= latest:
                    continue
                highest_sequence[event_type] = chunk_sequence

            yield raw_chunk

    @staticmethod
    def _parse_sse_payload(raw_chunk: str) -> dict[str, Any] | None:
        for line in (raw_chunk or "").splitlines():
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

    @classmethod
    def _extract_chunk_id(cls, event: dict[str, Any]) -> str | None:
        for source in cls._event_metadata_sources(event):
            for key in cls._CHUNK_ID_FIELDS:
                raw_value = source.get(key)
                if raw_value is None:
                    continue
                candidate = str(raw_value).strip()
                if candidate:
                    return candidate
        return None

    @classmethod
    def _extract_chunk_sequence(cls, event: dict[str, Any]) -> int | None:
        for source in cls._event_metadata_sources(event):
            for key in cls._CHUNK_SEQUENCE_FIELDS:
                candidate = cls._coerce_non_negative_int(source.get(key))
                if candidate is not None:
                    return candidate
        return None

    @staticmethod
    def _event_metadata_sources(event: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        sources: list[dict[str, Any]] = [event]
        payload = event.get("payload")
        if isinstance(payload, dict):
            sources.append(payload)
            metadata = payload.get("metadata")
            if isinstance(metadata, dict):
                sources.append(metadata)
        return tuple(sources)

    @staticmethod
    def _coerce_non_negative_int(value: Any) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value if value >= 0 else None
        if isinstance(value, float):
            if value.is_integer() and value >= 0:
                return int(value)
            return None
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                parsed = int(text)
            except ValueError:
                return None
            return parsed if parsed >= 0 else None
        return None

    def _message_payload(self, message: Any) -> Dict[str, Any]:
        payload = super()._message_payload(message)
        if payload.get("correlation_id"):
            return payload

        correlation_id = self._extract_correlation_id(payload, raw_message=message)
        if correlation_id:
            payload["correlation_id"] = correlation_id
        return payload

    def _capture_sdk_session_id(
        self, session_id: str, raw_message: Any, payload: Dict[str, Any]
    ) -> None:
        remote_session_id = self._extract_session_id(payload, raw_message=raw_message)
        correlation_id = self._extract_correlation_id(payload, raw_message=raw_message)

        self._register_session_alias(session_id, remote_session_id)
        self._register_correlation_alias(session_id, correlation_id)
        super()._capture_sdk_session_id(session_id, raw_message, payload)

    def _parse_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event = super()._parse_message(payload)
        if not event:
            return None

        remote_session_id = self._extract_session_id(payload)
        correlation_id = self._extract_correlation_id(payload)
        mapped_session_id = self._resolve_session_id(
            remote_session_id or correlation_id or ""
        )

        with self._lock:
            if mapped_session_id in self._sessions:
                event["session_id"] = mapped_session_id
                if remote_session_id:
                    self._session_aliases[remote_session_id] = mapped_session_id
                if correlation_id:
                    self._correlation_aliases[correlation_id] = mapped_session_id

        if correlation_id:
            event["correlation_id"] = correlation_id

        return event

    def _resolve_gateway_client(self) -> GatewayClient:
        if self._gateway_client is not None:
            return self._gateway_client
        if not self._gateway_base_url:
            raise RunnerError("GATEWAY_BASE_URL is not configured")
        self._gateway_client = GatewayClient(
            self._gateway_base_url,
            api_key=self._gateway_api_key or None,
            timeout_seconds=self._gateway_timeout_seconds,
        )
        return self._gateway_client

    def _resolve_runtime_session_id(self, session_id: str) -> str:
        normalized = self._normalize_identifier(session_id)
        if not normalized:
            return str(uuid.uuid4())

        with self._lock:
            existing = self._runtime_session_ids.get(normalized)
            if existing:
                return existing
            generated = str(uuid.uuid5(uuid.NAMESPACE_URL, f"aiaa-gateway:{normalized}"))
            self._runtime_session_ids[normalized] = generated
            return generated

    @staticmethod
    def _pin_runtime_session_enabled() -> bool:
        raw = (os.getenv("CHAT_GATEWAY_PIN_RUNTIME_SESSION") or "").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    @staticmethod
    def _extract_gateway_error(payload: Mapping[str, Any]) -> str:
        error_obj = payload.get("error")
        if isinstance(error_obj, Mapping):
            message = error_obj.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()

        status = str(payload.get("status") or "").strip().lower()
        if status in {"failed", "error"}:
            return "Gateway response reported failure"
        return ""

    @staticmethod
    def _extract_gateway_text(payload: Mapping[str, Any]) -> str:
        output_text = payload.get("output_text")
        if isinstance(output_text, str):
            return output_text

        output = payload.get("output")
        if not isinstance(output, list):
            return ""

        chunks: list[str] = []
        for item in output:
            if not isinstance(item, Mapping):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, Mapping):
                    continue
                if str(block.get("type", "")).strip().lower() not in {
                    "output_text",
                    "text",
                }:
                    continue
                text = block.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "".join(chunks)

    @classmethod
    def _history_limit(cls) -> int:
        raw_value = os.getenv("CHAT_GATEWAY_HISTORY_LIMIT", str(cls._DEFAULT_HISTORY_LIMIT))
        try:
            return max(1, int(raw_value))
        except (TypeError, ValueError):
            return cls._DEFAULT_HISTORY_LIMIT

    @classmethod
    def _history_max_chars(cls) -> int:
        raw_value = os.getenv(
            "CHAT_GATEWAY_HISTORY_MAX_CHARS",
            str(cls._DEFAULT_HISTORY_MAX_CHARS),
        )
        try:
            return max(1000, int(raw_value))
        except (TypeError, ValueError):
            return cls._DEFAULT_HISTORY_MAX_CHARS

    @classmethod
    def _history_message_max_chars(cls) -> int:
        raw_value = os.getenv(
            "CHAT_GATEWAY_HISTORY_MESSAGE_MAX_CHARS",
            str(cls._DEFAULT_HISTORY_MESSAGE_MAX_CHARS),
        )
        try:
            return max(100, int(raw_value))
        except (TypeError, ValueError):
            return cls._DEFAULT_HISTORY_MESSAGE_MAX_CHARS

    def _load_message_history(self, session_id: str) -> list[dict[str, str]]:
        store = self._session_store
        if store is None:
            return []

        get_messages = getattr(store, "get_messages", None)
        if not callable(get_messages):
            return []

        history_limit = self._history_limit()
        try:
            raw_messages = get_messages(session_id)
        except TypeError:
            raw_messages = get_messages(session_id, limit=None)
        except Exception:
            logger.exception("Failed to load chat history for session %s", session_id)
            return []

        if not isinstance(raw_messages, list):
            return []
        if len(raw_messages) > history_limit:
            raw_messages = raw_messages[-history_limit:]

        message_limit = self._history_limit()
        message_max_chars = self._history_message_max_chars()
        total_max_chars = self._history_max_chars()

        collected_reversed: list[dict[str, str]] = []
        used_chars = 0
        for raw_message in reversed(raw_messages):
            if len(collected_reversed) >= message_limit:
                break
            if not isinstance(raw_message, Mapping):
                continue

            role = str(raw_message.get("role") or "").strip().lower()
            if role not in self._HISTORY_ROLES:
                continue

            content = self._stringify(raw_message.get("content")).strip()
            if not content:
                continue

            if len(content) > message_max_chars:
                content = content[-message_max_chars:]

            remaining = total_max_chars - used_chars
            if remaining <= 0:
                break
            if len(content) > remaining:
                content = content[-remaining:]
            if not content:
                continue

            used_chars += len(content)
            collected_reversed.append({"role": role, "content": content})

        collected_reversed.reverse()
        return collected_reversed

    def _build_gateway_input(self, session_id: str, user_message: str) -> str | list[dict[str, str]]:
        history = self._load_message_history(session_id)
        latest_user_message = (user_message or "").strip()
        if latest_user_message:
            needs_append = (
                not history
                or history[-1].get("role") != "user"
                or history[-1].get("content", "").strip() != latest_user_message
            )
            if needs_append:
                history.append({"role": "user", "content": latest_user_message})

        if not history:
            return latest_user_message
        if len(history) == 1 and history[0].get("role") == "user":
            return history[0].get("content", "")
        return history

    @staticmethod
    def _as_mapping(value: Any) -> Mapping[str, Any]:
        return value if isinstance(value, Mapping) else {}

    @staticmethod
    def _first_non_empty_string(*values: Any) -> str:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""

    def _extract_stream_error_message(self, event: Mapping[str, Any]) -> str:
        response_obj = self._as_mapping(event.get("response"))
        response_error = self._as_mapping(response_obj.get("error"))
        event_error = self._as_mapping(event.get("error"))
        message = self._first_non_empty_string(
            event.get("message"),
            event.get("content"),
            response_error.get("message"),
            event_error.get("message"),
        )
        return message or "Gateway execution failed"

    def _translate_gateway_stream_event(
        self, event: Mapping[str, Any]
    ) -> Optional[dict[str, Any]]:
        event_type = str(event.get("type") or "").strip().lower()
        if not event_type:
            return None

        timestamp = self._first_non_empty_string(event.get("timestamp")) or _utc_now_iso()

        if event_type == "response.output_text.done":
            # `response.output_text.done` carries the full final text. Streaming this as a
            # regular text delta duplicates already-streamed content and breaks incremental
            # markdown rendering behavior in the chat UI.
            return None

        if event_type == "response.output_text.delta":
            content = ""
            for key in ("delta", "text", "content"):
                value = event.get(key)
                if isinstance(value, str) and value != "":
                    content = value
                    break
            if not content:
                return None
            return {"type": "text", "content": content, "timestamp": timestamp}

        if event_type in ("response.output_item.added", "response.output_item.done"):
            item = self._as_mapping(event.get("item"))
            item_type = str(item.get("type") or "").strip().lower()
            if not item_type:
                return None

            if item_type in ("function_call", "tool_call"):
                if event_type == "response.output_item.done":
                    return None
                tool = self._first_non_empty_string(
                    item.get("name"),
                    item.get("tool_name"),
                ) or "Tool"
                tool_input: Any = item.get("arguments")
                if tool_input is None:
                    tool_input = item.get("input")
                if isinstance(tool_input, (dict, list)):
                    tool_input = json.dumps(tool_input, ensure_ascii=False)
                return {
                    "type": "tool_use",
                    "tool": tool,
                    "input": self._truncate(self._stringify(tool_input), 800),
                    "timestamp": timestamp,
                }

            if item_type in ("function_call_output", "tool_result"):
                if event_type == "response.output_item.done":
                    return None
                content: Any = item.get("output")
                if content is None:
                    content = item.get("content")
                return {
                    "type": "tool_result",
                    "content": self._truncate(self._stringify(content), 800),
                    "timestamp": timestamp,
                }

            if item_type == "message":
                content = self._extract_gateway_text({"output": [dict(item)]})
                if not content:
                    return None
                return {"type": "text", "content": content, "timestamp": timestamp}

            return None

        if event_type == "response.completed":
            response = self._as_mapping(event.get("response"))
            content = self._extract_gateway_text(response)
            if not content:
                return None
            return {"type": "result", "content": content, "timestamp": timestamp}

        if event_type in (
            "response.created",
            "response.in_progress",
            "response.content_part.added",
            "response.content_part.done",
        ):
            return None

        if event_type in ("response.failed", "error"):
            return {
                "type": "error",
                "content": self._extract_stream_error_message(event),
                "timestamp": timestamp,
            }

        return None

    def _run_agent(self, session_id: str, user_message: str) -> None:
        local_session_id = self._resolve_session_id(session_id)
        q = self._get_queue_or_raise(local_session_id)
        emitted_error_event = False

        try:
            self._record_run_started(local_session_id)
            token = (self._token_provider() or "").strip()
            if not token:
                raise RunnerError("Claude token is not configured")

            client = self._resolve_gateway_client()
            gateway_input = self._build_gateway_input(local_session_id, user_message)
            payload: dict[str, Any] = {
                "input": gateway_input,
                "stream": True,
                "cwd": self.cwd,
                "tools_profile": "full",
            }
            if self._pin_runtime_session_enabled():
                payload["session_id"] = self._resolve_runtime_session_id(local_session_id)
            stream_events = client.post_stream(
                self.RESPONSES_PATH,
                payload=payload,
                headers={"X-Anthropic-Api-Key": token},
                timeout_seconds=self._gateway_timeout_seconds,
            )

            assistant_chunks: list[str] = []
            saw_text_delta = False
            for response_event in stream_events:
                if not isinstance(response_event, dict):
                    continue

                self._capture_sdk_session_id(
                    local_session_id,
                    response_event,
                    response_event,
                )

                translated = self._translate_gateway_stream_event(response_event)
                if translated is None:
                    continue

                event_type = str(translated.get("type") or "").strip().lower()
                content = str(translated.get("content") or "")

                if event_type == "text" and content:
                    assistant_chunks.append(content)
                    saw_text_delta = True
                elif event_type == "result" and content:
                    if not saw_text_delta:
                        assistant_chunks.append(content)
                    else:
                        # Completed payload often repeats already-streamed text.
                        continue

                self._record_first_event_latency(local_session_id)
                q.put(translated)
                self._persist_event(local_session_id, translated)

                if event_type == "error":
                    emitted_error_event = True
                    raise RunnerError(content or "Gateway execution failed")

            assistant_text = "".join(assistant_chunks).strip()
            if assistant_text:
                self._append_assistant_message(local_session_id, assistant_text)

            self._set_session_state(local_session_id, status="idle", last_error=None)
            q.put(
                {
                    "type": "done",
                    "timestamp": _utc_now_iso(),
                    "metrics": self._record_total_runtime(local_session_id),
                }
            )
        except Exception as exc:  # pragma: no cover - runtime safety path
            message = _redact_token_like_text(str(exc) or "Gateway execution failed")
            logger.exception("Gateway run failed for session %s: %s", local_session_id, message)
            self._set_session_state(local_session_id, status="error", last_error=message)
            if not emitted_error_event:
                q.put(
                    {
                        "type": "error",
                        "content": message,
                        "timestamp": _utc_now_iso(),
                        "metrics": self._record_total_runtime(local_session_id),
                    }
                )
        finally:
            with self._send_guard_lock:
                self._inflight_sends.discard(local_session_id)

    def _resolve_session_id(self, session_id: str) -> str:
        candidate = self._normalize_identifier(session_id)
        if not candidate:
            return session_id

        with self._lock:
            if candidate in self._sessions:
                return candidate
            mapped = self._session_aliases.get(candidate)
            if mapped:
                return mapped
            mapped = self._correlation_aliases.get(candidate)
            if mapped:
                return mapped
        return candidate

    def _register_session_alias(
        self, local_session_id: str, alias_session_id: str | None
    ) -> None:
        local_id = self._normalize_identifier(local_session_id)
        alias_id = self._normalize_identifier(alias_session_id)
        if not local_id or not alias_id:
            return
        with self._lock:
            self._session_aliases[alias_id] = local_id

    def _register_correlation_alias(
        self, local_session_id: str, correlation_id: str | None
    ) -> None:
        local_id = self._normalize_identifier(local_session_id)
        correlation = self._normalize_identifier(correlation_id)
        if not local_id or not correlation:
            return
        with self._lock:
            self._correlation_aliases[correlation] = local_id

    def _extract_session_id(
        self,
        payload: Dict[str, Any],
        *,
        raw_message: Any | None = None,
    ) -> str | None:
        for key in ("session_id", "sdk_session_id", "gateway_session_id"):
            candidate = self._normalize_identifier(payload.get(key))
            if candidate:
                return candidate

        if raw_message is not None:
            for key in ("session_id", "sdk_session_id", "gateway_session_id"):
                candidate = self._normalize_identifier(getattr(raw_message, key, None))
                if candidate:
                    return candidate

        return None

    def _extract_correlation_id(
        self,
        payload: Dict[str, Any],
        *,
        raw_message: Any | None = None,
    ) -> str | None:
        for key in ("correlation_id", "request_id"):
            candidate = self._normalize_identifier(payload.get(key))
            if candidate:
                return candidate

        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            for key in ("correlation_id", "request_id"):
                candidate = self._normalize_identifier(metadata.get(key))
                if candidate:
                    return candidate

        if raw_message is not None:
            for key in ("correlation_id", "request_id"):
                candidate = self._normalize_identifier(getattr(raw_message, key, None))
                if candidate:
                    return candidate

        return None

    @staticmethod
    def _normalize_identifier(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def set_runtime_auth_context(
        self,
        *,
        session_id: str,
        auth_context: dict[str, str] | None = None,
    ) -> None:
        """Attach request auth context for a delegated gateway runtime session."""
        if not session_id:
            return

        with self._lock:
            contexts = getattr(self, "_runtime_auth_contexts", {})
            contexts[session_id] = dict(auth_context or {})
            self._runtime_auth_contexts = contexts
