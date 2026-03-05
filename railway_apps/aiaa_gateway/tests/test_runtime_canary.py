"""Tests for runtime canary authentication and setup-token behavior."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aiaa_gateway.services import runtime_canary


class _FakeProcess:
    def __init__(
        self,
        *,
        stdout: bytes = b"OK",
        stderr: bytes = b"",
        returncode: int = 0,
    ):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self.killed = False

    async def communicate(self):
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True


def test_setup_token_canary_uses_runtime_cli_and_oauth_env(monkeypatch):
    captured: dict[str, Any] = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _FakeProcess(stdout=b"OK", returncode=0)

    result = runtime_canary.run_gateway_runtime_canary(
        "sk-ant-oat01-example-token",
        timeout_seconds=7,
        create_subprocess_exec=fake_create_subprocess_exec,
    )

    assert result["status"] == "valid"
    assert "runtime canary succeeded" in result["message"].lower()
    assert result["output"] == "OK"

    args = list(captured["args"])
    assert args[0] == "claude"
    assert "--print" in args
    assert "--output-format" in args
    assert args[args.index("--output-format") + 1] == "text"

    env = captured["kwargs"]["env"]
    assert env["CLAUDE_SETUP_TOKEN"] == "sk-ant-oat01-example-token"
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat01-example-token"
    assert "ANTHROPIC_AUTH_TOKEN" not in env


def test_setup_token_canary_maps_nonzero_exit_to_invalid():
    async def fake_create_subprocess_exec(*args, **kwargs):
        del args, kwargs
        return _FakeProcess(
            stdout=b"",
            stderr=b"Failed to authenticate. API Error: 401",
            returncode=1,
        )

    result = runtime_canary.run_gateway_runtime_canary(
        "sk-ant-oat01-bad-token",
        timeout_seconds=5,
        create_subprocess_exec=fake_create_subprocess_exec,
    )

    assert result["status"] == "invalid"
    assert "runtime canary failed" in result["message"].lower()
    assert "401" in result["error"]
