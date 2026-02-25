"""
Global in-process limiter for concurrent chat runs.

This is intended for single-instance process limits (for example, one Modal
container instance). It is not distributed across multiple instances.
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Iterator


def _read_max_concurrency(default: int = 4) -> int:
    """Read max concurrency from env and fall back to a safe default."""
    raw = os.getenv("MAX_CONCURRENT_CHAT_RUNS", str(default)).strip()
    try:
        value = int(raw)
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


class ChatRunLimitError(RuntimeError):
    """Raised when the instance-level chat run limit is reached."""


class ChatRunLimiter:
    """Thread-safe, non-blocking limiter for concurrent chat runs."""

    def __init__(self, max_concurrent_runs: int):
        self.max_concurrent_runs = max(1, int(max_concurrent_runs))
        self._slots = threading.BoundedSemaphore(self.max_concurrent_runs)
        self._lock = threading.Lock()
        self._active_runs = 0

    @property
    def active_runs(self) -> int:
        with self._lock:
            return self._active_runs

    @contextmanager
    def run_slot(self) -> Iterator[None]:
        """Acquire one chat run slot for the lifetime of the context."""
        acquired = self._slots.acquire(blocking=False)
        if not acquired:
            raise ChatRunLimitError(
                f"Max concurrent chat runs reached ({self.max_concurrent_runs}). "
                "Try again shortly."
            )

        with self._lock:
            self._active_runs += 1

        try:
            yield
        finally:
            with self._lock:
                self._active_runs -= 1
            self._slots.release()


CHAT_RUN_LIMITER = ChatRunLimiter(_read_max_concurrency())
