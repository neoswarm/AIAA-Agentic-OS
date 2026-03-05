"""Unit tests for Claude runtime query execution flags and prompt assembly."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aiaa_gateway.services.runtime_query import run_gateway_runtime_query


class _FakeProcess:
    def __init__(self, *, stdout: bytes = b"ok", stderr: bytes = b"", returncode: int = 0):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self.killed = False

    async def communicate(self):
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True


def test_runtime_query_invokes_claude_with_tools_and_project_settings():
    captured: dict[str, Any] = {}
    token = "sk-ant-oat01-test-runtime-token"
    session_id = "11111111-1111-1111-1111-111111111111"

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _FakeProcess(stdout=b"runtime ok", returncode=0)

    result = run_gateway_runtime_query(
        token=token,
        messages=[{"role": "user", "content": "hello"}],
        cwd="/app",
        timeout_seconds=10,
        model="claude-sonnet-4-6",
        session_id=session_id,
        create_subprocess_exec=fake_create_subprocess_exec,
    )

    assert result["status"] == "ok"
    assert result["output_text"] == "runtime ok"

    args = list(captured["args"])
    assert args[0] == "claude"
    assert "--permission-mode" in args
    assert args[args.index("--permission-mode") + 1] == "bypassPermissions"
    assert "--setting-sources" in args
    assert args[args.index("--setting-sources") + 1] == "project"
    assert "--tools" in args
    assert args[args.index("--tools") + 1] == "default"
    assert "--session-id" in args
    assert args[args.index("--session-id") + 1] == session_id

    kwargs = captured["kwargs"]
    assert kwargs["cwd"] == "/app"
    env = kwargs["env"]
    assert env["CLAUDE_SETUP_TOKEN"] == token
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == token
    assert "ANTHROPIC_AUTH_TOKEN" not in env


def test_runtime_query_builds_multi_turn_prompt_with_roles():
    captured: dict[str, Any] = {}

    async def fake_create_subprocess_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _FakeProcess(stdout=b"ok", returncode=0)

    result = run_gateway_runtime_query(
        token="sk-ant-oat01-test-runtime-token",
        messages=[
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Follow-up"},
        ],
        cwd="/app",
        timeout_seconds=10,
        session_id="22222222-2222-2222-2222-222222222222",
        create_subprocess_exec=fake_create_subprocess_exec,
    )

    assert result["status"] == "ok"
    prompt = str(captured["args"][-1])
    assert "User: First question" in prompt
    assert "Assistant: First answer" in prompt
    assert "User: Follow-up" in prompt
    assert prompt.endswith("Assistant:")


def test_runtime_query_nonzero_exit_with_stdout_is_still_error():
    async def fake_create_subprocess_exec(*args, **kwargs):
        del args, kwargs
        return _FakeProcess(
            stdout=b"partial output",
            stderr=b"permission denied",
            returncode=1,
        )

    result = run_gateway_runtime_query(
        token="sk-ant-oat01-test-runtime-token",
        messages=[{"role": "user", "content": "hello"}],
        cwd="/app",
        timeout_seconds=10,
        create_subprocess_exec=fake_create_subprocess_exec,
    )

    assert result["status"] == "runtime_error"
    assert "permission denied" in str(result.get("error") or "")
