#!/usr/bin/env python3
"""Unit tests for chat backend runner resolution."""

from __future__ import annotations

import pytest

from services.agent_runner import AgentRunner
from services import chat_backend


def test_resolve_chat_backend_defaults_to_sdk(monkeypatch):
    monkeypatch.delenv("CHAT_BACKEND", raising=False)
    assert chat_backend.resolve_chat_backend() == "sdk"


def test_resolve_chat_backend_rejects_unknown_value():
    with pytest.raises(ValueError, match="Unsupported chat backend"):
        chat_backend.resolve_chat_backend("unknown")


def test_resolve_chat_runner_returns_sdk_runner():
    assert chat_backend.resolve_chat_runner("sdk") is AgentRunner


def test_resolve_chat_runner_returns_gateway_runner(monkeypatch):
    class DummyGatewayRunner:
        pass

    monkeypatch.setattr(
        chat_backend, "_load_gateway_runner", lambda: DummyGatewayRunner
    )
    assert chat_backend.resolve_chat_runner("gateway") is DummyGatewayRunner


def test_resolve_chat_runner_gateway_requires_module(monkeypatch):
    def _raise_import_error():
        raise ImportError("missing gateway runner")

    monkeypatch.setattr(chat_backend, "_load_gateway_runner", _raise_import_error)
    with pytest.raises(RuntimeError, match="CHAT_BACKEND='gateway'"):
        chat_backend.resolve_chat_runner("gateway")


def test_build_chat_runner_uses_resolved_runner_class(monkeypatch):
    captured = {}

    class DummyRunner:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(chat_backend, "resolve_chat_runner", lambda *_: DummyRunner)

    token_provider = lambda: "token"
    store = object()
    runner = chat_backend.build_chat_runner(
        cwd="/tmp/project",
        token_provider=token_provider,
        session_store=store,
        backend="gateway",
    )

    assert isinstance(runner, DummyRunner)
    assert captured["cwd"] == "/tmp/project"
    assert captured["token_provider"] is token_provider
    assert captured["session_store"] is store

