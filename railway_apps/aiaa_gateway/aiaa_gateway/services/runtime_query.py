"""Claude runtime query helpers for setup-token gateway execution."""

from __future__ import annotations

import asyncio
import os
import re
from asyncio.subprocess import PIPE
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from .runtime_canary import build_runtime_auth_env

CreateSubprocessExec = Callable[..., Awaitable[asyncio.subprocess.Process]]

_MAX_ERROR_LEN = 1500
_SESSION_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_AUTH_ENV_KEYS = (
    "CLAUDE_SETUP_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "CLAUDE_API_KEY",
)


def is_setup_token(token: str | None) -> bool:
    candidate = (token or "").strip().lower()
    return candidate.startswith("sk-ant-oat")


def _sanitize_session_id(session_id: str | None) -> str | None:
    candidate = (session_id or "").strip()
    if not candidate:
        return None
    return candidate if _SESSION_ID_PATTERN.fullmatch(candidate) else None


def _normalize_cli_model(model: str | None) -> str | None:
    candidate = (model or "").strip()
    if not candidate:
        return None
    if "/" in candidate:
        _, _, suffix = candidate.partition("/")
        candidate = suffix.strip()
    return candidate or None


def _build_prompt(
    messages: list[dict[str, str]],
) -> str:
    if not messages:
        return ""
    if len(messages) == 1 and messages[0].get("role") == "user":
        return str(messages[0].get("content") or "").strip()

    lines: list[str] = []
    for message in messages:
        role = str(message.get("role") or "user").strip().lower()
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        prefix = "Assistant" if role == "assistant" else "User"
        lines.append(f"{prefix}: {content}")
    if not lines:
        return ""
    lines.append("Assistant:")
    return "\n\n".join(lines)


async def _run_runtime_query(
    *,
    token: str,
    messages: list[dict[str, str]],
    cwd: str,
    timeout_seconds: float,
    model: str | None,
    system_prompt: str | None,
    session_id: str | None,
    create_subprocess_exec: CreateSubprocessExec,
) -> dict[str, Any]:
    prompt = _build_prompt(messages)
    if not prompt:
        return {"status": "invalid_request", "message": "input must contain text content"}

    env = dict(os.environ)
    for key in _AUTH_ENV_KEYS:
        env.pop(key, None)
    env.update(build_runtime_auth_env(token))

    args: list[str] = [
        "claude",
        "--print",
        "--output-format",
        "text",
        "--permission-mode",
        "acceptEdits",
        "--setting-sources",
        "project",
        "--tools",
        "default",
    ]

    normalized_model = _normalize_cli_model(model)
    if normalized_model:
        args.extend(["--model", normalized_model])

    if system_prompt and system_prompt.strip():
        args.extend(["--append-system-prompt", system_prompt.strip()])

    safe_session_id = _sanitize_session_id(session_id)
    if safe_session_id:
        args.extend(["--session-id", safe_session_id])

    args.append(prompt)

    process = await create_subprocess_exec(
        *args,
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
            "message": f"Claude runtime timed out after {int(timeout_seconds)}s",
        }

    stdout = stdout_raw.decode("utf-8", errors="replace").strip()
    stderr = stderr_raw.decode("utf-8", errors="replace").strip()

    if process.returncode != 0:
        detail = stderr or stdout or "Claude runtime exited with a non-zero status."
        return {
            "status": "runtime_error",
            "message": "Claude runtime execution failed",
            "error": detail[:_MAX_ERROR_LEN],
        }

    if not stdout:
        return {
            "status": "runtime_error",
            "message": "Claude runtime returned empty output",
        }

    return {
        "status": "ok",
        "output_text": stdout,
        "model": normalized_model or "",
    }


def run_gateway_runtime_query(
    *,
    token: str,
    messages: list[dict[str, str]],
    cwd: str,
    timeout_seconds: float,
    model: str | None = None,
    system_prompt: str | None = None,
    session_id: str | None = None,
    create_subprocess_exec: CreateSubprocessExec = asyncio.create_subprocess_exec,
) -> dict[str, Any]:
    candidate = (token or "").strip()
    if not candidate:
        return {"status": "invalid_request", "message": "token is required"}

    if not isinstance(messages, list) or not messages:
        return {"status": "invalid_request", "message": "input must contain messages"}

    safe_cwd = (cwd or "").strip() or "/app"
    if not os.path.isabs(safe_cwd):
        safe_cwd = "/app"

    safe_timeout = max(1.0, float(timeout_seconds))

    try:
        return asyncio.run(
            _run_runtime_query(
                token=candidate,
                messages=messages,
                cwd=safe_cwd,
                timeout_seconds=safe_timeout,
                model=model,
                system_prompt=system_prompt,
                session_id=session_id,
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
            "message": f"Claude runtime execution crashed: {exc}",
        }
