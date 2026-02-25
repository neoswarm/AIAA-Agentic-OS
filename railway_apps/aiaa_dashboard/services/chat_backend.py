"""Utilities for selecting the runtime chat backend."""

from __future__ import annotations

import os


CHAT_BACKEND_ENV_VAR = "CHAT_BACKEND"
DEFAULT_CHAT_BACKEND = "sdk"
SUPPORTED_CHAT_BACKENDS = {"sdk", "gateway"}


def select_chat_backend(raw_value: str | None = None) -> tuple[str, str | None]:
    """Return (backend, warning). Unsupported values fall back to sdk."""
    configured = raw_value
    if configured is None:
        configured = os.getenv(CHAT_BACKEND_ENV_VAR, "")

    normalized = configured.strip().lower()
    if not normalized:
        return DEFAULT_CHAT_BACKEND, None

    if normalized in SUPPORTED_CHAT_BACKENDS:
        return normalized, None

    return (
        DEFAULT_CHAT_BACKEND,
        (
            f"Invalid {CHAT_BACKEND_ENV_VAR}='{configured}'. "
            f"Supported values: sdk, gateway. Falling back to sdk."
        ),
    )
