"""Gateway runtime canary validation helpers for setup-token profiles."""

from __future__ import annotations

import asyncio
import json
import os
from asyncio.subprocess import PIPE
from collections.abc import Awaitable, Callable
from typing import Any

import requests as http_requests


CreateSubprocessExec = Callable[..., Awaitable[asyncio.subprocess.Process]]

_CANARY_PROMPT = "Reply with the single word OK."
_MAX_ERROR_LEN = 500
_AUTH_ENV_KEYS = (
    "CLAUDE_SETUP_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "CLAUDE_API_KEY",
)
_OAUTH_ANTHROPIC_BETA_HEADER = (
    "claude-code-20250219,"
    "oauth-2025-04-20,"
    "fine-grained-tool-streaming-2025-05-14,"
    "interleaved-thinking-2025-05-14"
)


def build_runtime_auth_env(token: str) -> dict[str, str]:
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


def _is_setup_token(token: str) -> bool:
    return (token or "").strip().lower().startswith("sk-ant-oat")


def _run_oauth_canary(token: str, *, timeout_seconds: float) -> dict[str, Any]:
    headers = {
        "authorization": f"Bearer {token}",
        "anthropic-version": "2023-06-01",
        "anthropic-beta": _OAUTH_ANTHROPIC_BETA_HEADER,
        "content-type": "application/json",
        "accept": "application/json",
    }
    payload = {
        "model": os.getenv("DEFAULT_ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        "max_tokens": 8,
        "messages": [{"role": "user", "content": _CANARY_PROMPT}],
    }
    try:
        response = http_requests.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers,
            timeout=timeout_seconds,
        )
    except http_requests.RequestException as exc:
        return {
            "status": "runtime_unavailable",
            "message": "Gateway OAuth canary request failed",
            "error": str(exc)[:_MAX_ERROR_LEN],
        }

    try:
        body = response.json()
    except ValueError:
        body = {"raw_body": response.text[:_MAX_ERROR_LEN]}

    if response.status_code == 200:
        text = ""
        if isinstance(body, dict):
            content = body.get("content")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if str(block.get("type") or "").lower() != "text":
                        continue
                    candidate = block.get("text")
                    if isinstance(candidate, str) and candidate.strip():
                        text = candidate.strip()
                        break
        return {
            "status": "valid",
            "message": "Gateway OAuth canary succeeded",
            "output": text or "OK",
        }

    if response.status_code == 429:
        return {
            "status": "valid",
            "message": "Gateway OAuth canary is rate limited",
            "error": json.dumps(body)[:_MAX_ERROR_LEN],
        }

    return {
        "status": "invalid",
        "message": "Gateway OAuth canary failed",
        "error": json.dumps(body)[:_MAX_ERROR_LEN],
    }


async def _run_canary(
    token: str,
    *,
    timeout_seconds: float,
    create_subprocess_exec: CreateSubprocessExec,
) -> dict[str, Any]:
    env = dict(os.environ)
    for key in _AUTH_ENV_KEYS:
        env.pop(key, None)
    env.update(build_runtime_auth_env(token))

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

    if _is_setup_token(candidate):
        return _run_oauth_canary(candidate, timeout_seconds=timeout)

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
