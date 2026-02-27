"""Gateway runtime canary validation helpers for setup-token profiles."""

from __future__ import annotations

import asyncio
import os
from asyncio.subprocess import PIPE
from collections.abc import Awaitable, Callable
from typing import Any


CreateSubprocessExec = Callable[..., Awaitable[asyncio.subprocess.Process]]

_CANARY_PROMPT = "Reply with the single word OK."
_MAX_ERROR_LEN = 500
_DEFAULT_WORKSPACE_CWD = "/app"


def _build_runtime_auth_env(token: str) -> dict[str, str]:
    """Map a token to auth environment variables recognized by Claude runtime."""
    candidate = (token or "").strip()
    if not candidate:
        return {}

    env = {"CLAUDE_SETUP_TOKEN": candidate}
    if candidate.startswith("sk-ant-oat"):
        env["CLAUDE_CODE_OAUTH_TOKEN"] = candidate
        env["ANTHROPIC_AUTH_TOKEN"] = candidate
        return env
    if candidate.startswith("sk-ant-"):
        env["ANTHROPIC_API_KEY"] = candidate
        env["CLAUDE_API_KEY"] = candidate
        return env

    env["CLAUDE_CODE_OAUTH_TOKEN"] = candidate
    env["ANTHROPIC_AUTH_TOKEN"] = candidate
    return env


async def _run_canary(
    token: str,
    *,
    timeout_seconds: float,
    cwd: str,
    create_subprocess_exec: CreateSubprocessExec,
) -> dict[str, Any]:
    env = dict(os.environ)
    env.update(_build_runtime_auth_env(token))

    process = await create_subprocess_exec(
        "claude",
        "--print",
        "--output-format",
        "text",
        _CANARY_PROMPT,
        stdout=PIPE,
        stderr=PIPE,
        env=env,
        cwd=cwd,
    )
    try:
        stdout_raw, stderr_raw = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        return {
            "status": "timeout",
            "message": f"Gateway runtime canary timed out after {timeout_seconds}s",
        }

    stdout = stdout_raw.decode("utf-8", errors="replace").strip()
    stderr = stderr_raw.decode("utf-8", errors="replace").strip()

    if process.returncode != 0:
        detail = stderr or stdout or "Gateway runtime exited with a non-zero status."
        return {
            "status": "invalid",
            "message": "Gateway runtime canary failed",
            "error": detail[:_MAX_ERROR_LEN],
        }

    if not stdout:
        return {
            "status": "invalid",
            "message": "Gateway runtime canary returned empty output",
        }

    return {
        "status": "valid",
        "message": "Gateway runtime canary succeeded",
        "output": stdout,
    }


def _resolve_runtime_cwd(cwd: str | None) -> str:
    normalized_default = os.path.normpath(_DEFAULT_WORKSPACE_CWD)
    candidate = (cwd or "").strip()
    if not candidate:
        return normalized_default
    if not os.path.isabs(candidate):
        raise ValueError("cwd must be an absolute path under /app")

    normalized_candidate = os.path.normpath(candidate)
    try:
        is_allowed = (
            os.path.commonpath([normalized_candidate, normalized_default])
            == normalized_default
        )
    except ValueError:
        is_allowed = False

    if not is_allowed:
        raise ValueError("cwd must stay within /app workspace")
    return normalized_candidate


def run_gateway_runtime_canary(
    token: str,
    *,
    timeout_seconds: float | None = None,
    cwd: str | None = None,
    create_subprocess_exec: CreateSubprocessExec = asyncio.create_subprocess_exec,
) -> dict[str, Any]:
    """Run a small runtime canary with token auth to validate profile readiness."""
    candidate = (token or "").strip()
    if not candidate:
        return {"status": "invalid", "message": "token is required"}

    timeout = timeout_seconds
    if timeout is None:
        raw_timeout = os.getenv("GATEWAY_RUNTIME_CANARY_TIMEOUT_SECONDS", "12")
        try:
            timeout = max(1.0, float(raw_timeout))
        except (TypeError, ValueError):
            timeout = 12.0

    try:
        runtime_cwd = _resolve_runtime_cwd(cwd)
    except ValueError as exc:
        return {"status": "invalid", "message": str(exc)}

    try:
        return asyncio.run(
            _run_canary(
                candidate,
                timeout_seconds=timeout,
                cwd=runtime_cwd,
                create_subprocess_exec=create_subprocess_exec,
            )
        )
    except FileNotFoundError:
        return {
            "status": "runtime_unavailable",
            "message": "Claude runtime is not installed on this host",
        }
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        return {
            "status": "runtime_error",
            "message": f"Gateway runtime canary crashed: {exc}",
        }
