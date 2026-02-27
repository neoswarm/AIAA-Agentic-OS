"""
Gateway-backed chat runner implementing the existing runner interface contract.
"""

from __future__ import annotations

from services.agent_runner import AgentRunner, RunnerError

__all__ = ["GatewayRunner", "RunnerError"]


class GatewayRunner(AgentRunner):
    """Drop-in runner implementation for gateway-based chat execution."""

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
