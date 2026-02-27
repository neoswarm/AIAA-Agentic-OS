#!/usr/bin/env python3
"""Unit tests for gateway runtime canary helper."""

from __future__ import annotations

import asyncio

import pytest

from services.gateway_runtime_canary import run_gateway_runtime_canary


class _FakeProcess:
    def __init__(self, returncode=0, stdout=b"OK\n", stderr=b"", delay_seconds=0.0):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self._delay_seconds = delay_seconds
        self.killed = False

    async def communicate(self):
        if self._delay_seconds > 0:
            await asyncio.sleep(self._delay_seconds)
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True


def test_gateway_runtime_canary_success_sets_setup_token_env():
    captured = {}

    async def _fake_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _FakeProcess(returncode=0, stdout=b"OK\n")

    result = run_gateway_runtime_canary(
        "sk-ant-oat01-example-token",
        timeout_seconds=0.2,
        create_subprocess_exec=_fake_exec,
    )

    assert result["status"] == "valid"
    assert captured["args"][0] == "claude"
    assert "--print" in captured["args"]
    env = captured["kwargs"]["env"]
    assert env["CLAUDE_SETUP_TOKEN"] == "sk-ant-oat01-example-token"
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-example-token"
    assert env["ANTHROPIC_AUTH_TOKEN"] == "sk-ant-oat01-example-token"
    assert captured["kwargs"]["cwd"] == "/app"


def test_gateway_runtime_canary_accepts_explicit_app_subdir_cwd():
    captured = {}

    async def _fake_exec(*args, **kwargs):
        captured["kwargs"] = kwargs
        return _FakeProcess(returncode=0, stdout=b"OK\n")

    result = run_gateway_runtime_canary(
        "sk-ant-oat01-example-token",
        timeout_seconds=0.2,
        cwd="/app/workspace/../workspace/demo",
        create_subprocess_exec=_fake_exec,
    )

    assert result["status"] == "valid"
    assert captured["kwargs"]["cwd"] == "/app/workspace/demo"


@pytest.mark.parametrize(
    "cwd_value",
    [
        "../app",
        "app",
        "/tmp",
        "/app/../../etc",
    ],
)
def test_gateway_runtime_canary_rejects_unsafe_cwd(cwd_value):
    called = False

    async def _fake_exec(*args, **kwargs):
        nonlocal called
        called = True
        return _FakeProcess(returncode=0, stdout=b"OK\n")

    result = run_gateway_runtime_canary(
        "sk-ant-oat01-example-token",
        timeout_seconds=0.2,
        cwd=cwd_value,
        create_subprocess_exec=_fake_exec,
    )

    assert result["status"] == "invalid"
    assert "cwd" in result["message"]
    assert called is False


def test_gateway_runtime_canary_maps_nonzero_exit_to_invalid():
    async def _fake_exec(*args, **kwargs):
        return _FakeProcess(returncode=1, stdout=b"", stderr=b"auth failed")

    result = run_gateway_runtime_canary(
        "sk-ant-api01-example-token",
        timeout_seconds=0.2,
        create_subprocess_exec=_fake_exec,
    )

    assert result["status"] == "invalid"
    assert result["message"] == "Gateway runtime canary failed"
    assert "auth failed" in result["error"]


def test_gateway_runtime_canary_reports_runtime_unavailable():
    async def _missing_runtime(*args, **kwargs):
        raise FileNotFoundError("claude not installed")

    result = run_gateway_runtime_canary(
        "sk-ant-api01-example-token",
        timeout_seconds=0.2,
        create_subprocess_exec=_missing_runtime,
    )

    assert result["status"] == "runtime_unavailable"


def test_gateway_runtime_canary_times_out_and_kills_process():
    holder = {}

    async def _fake_exec(*args, **kwargs):
        process = _FakeProcess(delay_seconds=0.05)
        holder["process"] = process
        return process

    result = run_gateway_runtime_canary(
        "sk-ant-api01-example-token",
        timeout_seconds=0.01,
        create_subprocess_exec=_fake_exec,
    )

    assert result["status"] == "timeout"
    assert holder["process"].killed is True
