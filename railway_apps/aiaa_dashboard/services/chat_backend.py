"""Utilities for selecting and resolving the runtime chat backend."""

from __future__ import annotations

import os
from typing import Any, Callable

from services.agent_runner import AgentRunner

CHAT_BACKEND_ENV_VAR = "CHAT_BACKEND"
DEFAULT_CHAT_BACKEND = "sdk"
SUPPORTED_CHAT_BACKENDS = ("sdk", "gateway")


def select_chat_backend(raw_value: str | None = None) -> tuple[str, str | None]:
    """Return (backend, warning). Unsupported values fall back to sdk."""
    configured = raw_value
    if configured is None:
        configured = os.getenv(CHAT_BACKEND_ENV_VAR, "")

    normalized = (configured or "").strip().lower()
    if not normalized:
        return DEFAULT_CHAT_BACKEND, None

    if normalized in SUPPORTED_CHAT_BACKENDS:
        return normalized, None

    supported = ", ".join(SUPPORTED_CHAT_BACKENDS)
    return (
        DEFAULT_CHAT_BACKEND,
        (
            f"Invalid {CHAT_BACKEND_ENV_VAR}='{configured}'. "
            f"Supported values: {supported}. Falling back to {DEFAULT_CHAT_BACKEND}."
        ),
    )


def resolve_chat_backend(backend: str | None = None) -> str:
    """Resolve and validate chat backend, raising on unsupported explicit values."""
    value = backend if backend is not None else os.getenv(CHAT_BACKEND_ENV_VAR)
    selected = (value or DEFAULT_CHAT_BACKEND).strip().lower()
    if selected not in SUPPORTED_CHAT_BACKENDS:
        supported = ", ".join(SUPPORTED_CHAT_BACKENDS)
        raise ValueError(
            f"Unsupported chat backend '{selected}'. Expected one of: {supported}."
        )
    return selected


def _load_gateway_runner():
    from services.gateway_runner import GatewayRunner  # type: ignore

    return GatewayRunner


def resolve_chat_runner(backend: str | None = None):
    """Return the runner class for the selected chat backend."""
    selected = resolve_chat_backend(backend)
    if selected == "sdk":
        return AgentRunner

    try:
        return _load_gateway_runner()
    except ImportError as exc:
        raise RuntimeError(
            "CHAT_BACKEND='gateway' requires services.gateway_runner.GatewayRunner"
        ) from exc


def build_chat_runner(
    *,
    cwd: str,
    token_provider: Callable[[], str],
    session_store: Any | None = None,
    backend: str | None = None,
):
    """Build a chat runner instance for the selected backend."""
    if backend is None:
        backend, _ = select_chat_backend()
    else:
        backend = resolve_chat_backend(backend)

    runner_cls = resolve_chat_runner(backend)
    return runner_cls(
        cwd=cwd,
        token_provider=token_provider,
        session_store=session_store,
    )
