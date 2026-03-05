"""Backend-agnostic chat runner interfaces and factory helpers."""

from __future__ import annotations

from typing import Any, Callable, Dict, Generator, Protocol

from services.agent_runner import RunnerError
from services.chat_backend import build_chat_runner


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


def create_chat_runner(
    *,
    cwd: str,
    token_provider: Callable[[], str],
    session_store: Any | None = None,
) -> ChatRunnerBackend:
    """Create the chat runner using the configured backend implementation."""
    return build_chat_runner(
        cwd=cwd,
        token_provider=token_provider,
        session_store=session_store,
    )


__all__ = ["ChatRunnerBackend", "RunnerError", "create_chat_runner"]
