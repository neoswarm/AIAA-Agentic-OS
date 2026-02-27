"""
Gateway-backed chat runner implementing the existing runner interface contract.
"""

from __future__ import annotations

from typing import Any, Dict, Generator, Optional

from services.agent_runner import AgentRunner, RunnerError

__all__ = ["GatewayRunner", "RunnerError"]


class GatewayRunner(AgentRunner):
    """Drop-in runner implementation for gateway-based chat execution."""

    def __init__(
        self,
        cwd: str | None,
        token_provider,
        allowed_tools: Optional[list[str]] = None,
        permission_mode: str = "acceptEdits",
        session_store: Any | None = None,
        cwd_allowlist: Optional[list[str]] = None,
    ):
        super().__init__(
            cwd=cwd,
            token_provider=token_provider,
            allowed_tools=allowed_tools,
            permission_mode=permission_mode,
            session_store=session_store,
            cwd_allowlist=cwd_allowlist,
        )
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
