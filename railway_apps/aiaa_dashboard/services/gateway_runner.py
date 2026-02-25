"""
Gateway-backed chat runner implementing the existing runner interface contract.
"""

from __future__ import annotations

from services.agent_runner import AgentRunner, RunnerError

__all__ = ["GatewayRunner", "RunnerError"]


class GatewayRunner(AgentRunner):
    """Drop-in runner implementation for gateway-based chat execution."""
