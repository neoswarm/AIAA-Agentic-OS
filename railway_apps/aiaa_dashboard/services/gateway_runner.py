"""
Gateway-backed chat runner implementing the existing runner interface contract.
"""

from __future__ import annotations

import threading

from services.agent_runner import AgentRunner, RunnerError

__all__ = ["GatewayRunner", "RunnerError"]


class GatewayRunner(AgentRunner):
    """Drop-in runner implementation for gateway-based chat execution."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._send_guard_lock = threading.RLock()
        self._inflight_sends: set[str] = set()

    def send_message(self, session_id: str, user_message: str) -> None:
        """
        Prevent overlapping sends per session even if external state drifts.

        Gateway mode can span multiple layers that may transiently report stale
        session status, so keep an explicit local in-flight guard.
        """
        with self._send_guard_lock:
            if session_id in self._inflight_sends:
                raise RunnerError("Session is already running")
            self._inflight_sends.add(session_id)

        try:
            super().send_message(session_id, user_message)
        except Exception:
            with self._send_guard_lock:
                self._inflight_sends.discard(session_id)
            raise

    def _run_agent(self, session_id: str, user_message: str) -> None:
        try:
            super()._run_agent(session_id, user_message)
        finally:
            with self._send_guard_lock:
                self._inflight_sends.discard(session_id)
