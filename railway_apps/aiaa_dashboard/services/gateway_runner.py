"""
Gateway-backed chat runner implementing the existing runner interface contract.
"""

from __future__ import annotations

import logging
import os
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
        self._gateway_client = gateway_client
        self._session_aliases: Dict[str, str] = {}
        self._correlation_aliases: Dict[str, str] = {}

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
        super().send_message(self._resolve_session_id(session_id), user_message)

    def get_stream(
        self, session_id: str, keepalive_seconds: int = 20
    ) -> Generator[str, None, None]:
        return super().get_stream(
            self._resolve_session_id(session_id),
            keepalive_seconds=keepalive_seconds,
        )

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
        )
        return self._gateway_client

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

    def _run_agent(self, session_id: str, user_message: str) -> None:
        local_session_id = self._resolve_session_id(session_id)
        q = self._get_queue_or_raise(local_session_id)

        try:
            self._record_run_started(local_session_id)
            token = (self._token_provider() or "").strip()
            if not token:
                raise RunnerError("Claude token is not configured")

            client = self._resolve_gateway_client()
            response = client.post_json(
                self.RESPONSES_PATH,
                payload={"input": user_message, "stream": False},
                headers={"X-Anthropic-Api-Key": token},
            )

            if not isinstance(response, dict):
                raise RunnerError("Gateway response body must be a JSON object")

            self._capture_sdk_session_id(local_session_id, response, response)

            error_message = self._extract_gateway_error(response)
            if error_message:
                raise RunnerError(error_message)

            result_text = self._extract_gateway_text(response)
            if result_text:
                event = {
                    "type": "result",
                    "content": result_text,
                    "timestamp": _utc_now_iso(),
                }
                self._record_first_event_latency(local_session_id)
                q.put(event)
                self._persist_event(local_session_id, event)
                self._append_assistant_message(local_session_id, result_text)

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
            q.put(
                {
                    "type": "error",
                    "content": message,
                    "timestamp": _utc_now_iso(),
                    "metrics": self._record_total_runtime(local_session_id),
                }
            )

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
