"""Backend-agnostic chat runner interfaces and shared error type."""

from __future__ import annotations

from typing import Any, Dict, Generator, Protocol

from services.agent_runner import RunnerError


class ChatRunnerBackend(Protocol):
    """Interface expected by chat routes regardless of runner backend."""

    cwd: str

    def attach_store(self, session_store: Any | None) -> None: ...

    def ensure_session(
        self,
        session_id: str,
        *,
        title: str | None = None,
        sdk_session_id: str | None = None,
    ) -> Dict[str, Any]: ...

    def has_session(self, session_id: str) -> bool: ...

    def send_message(self, session_id: str, user_message: str) -> None: ...

    def get_stream(
        self, session_id: str, keepalive_seconds: int = 20
    ) -> Generator[str, None, None]: ...


__all__ = ["ChatRunnerBackend", "RunnerError"]
