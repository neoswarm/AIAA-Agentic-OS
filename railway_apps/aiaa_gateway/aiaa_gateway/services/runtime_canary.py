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


def _build_runtime_auth_env(token: str) -> dict[str, str]:
    """Map token format to auth env vars recognized by Claude runtime."""
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


def run_gateway_runtime_canary(
    token: str,
    *,
    timeout_seconds: float | None = None,
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
        return asyncio.run(
            _run_canary(
                candidate,
                timeout_seconds=timeout,
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
