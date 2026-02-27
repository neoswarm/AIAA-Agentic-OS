"""Unit tests for backend-aware chat runner factory."""

from __future__ import annotations

from services.agent_runner import AgentRunner
from services.chat_runner import create_chat_runner
from services.gateway_runner import GatewayRunner


def test_create_chat_runner_defaults_to_agent_runner(monkeypatch):
    monkeypatch.delenv("CHAT_BACKEND", raising=False)

    runner = create_chat_runner(cwd="/tmp/project", token_provider=lambda: "token")

    assert type(runner) is AgentRunner


def test_create_chat_runner_uses_gateway_runner_when_gateway_backend(monkeypatch):
    monkeypatch.setenv("CHAT_BACKEND", " gateway ")

    runner = create_chat_runner(cwd="/tmp/project", token_provider=lambda: "token")

    assert type(runner) is GatewayRunner
