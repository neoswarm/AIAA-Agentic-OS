"""
Agent runner service for streaming Claude Agent SDK responses over SSE.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import logging
import os
import queue
import re
import secrets
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, Generator, Optional


logger = logging.getLogger(__name__)

_TOKEN_BEARER_PATTERN = re.compile(r"(?i)\b(bearer)(\s+)([A-Za-z0-9._\-]{8,})\b")
_TOKEN_PREFIX_PATTERN = re.compile(
    r"\b(?:sk-or-|pplx-|sk-ant-|sk-|xox[baprs]-|ghp_|github_pat_)[A-Za-z0-9._\-]{8,}\b",
    re.IGNORECASE,
)
_TOKEN_KEY_VALUE_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|authorization)\b(\s*[:=]\s*)([^\s\"',;]{8,})"
)
_TOKEN_JWT_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9._\-]{5,}\.[A-Za-z0-9._\-]{5,}\b"
)


class RunnerError(RuntimeError):
    """Raised when the chat runner cannot execute a request."""


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _frame_sse_event(event: Dict[str, Any]) -> str:
    """Serialize an event dict into a single SSE data frame."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _frame_sse_ping_event(timestamp: str | None = None) -> str:
    """Frame a keepalive ping SSE event."""
    return _frame_sse_event({"type": "ping", "timestamp": timestamp or _utc_now_iso()})


def _frame_sse_error_event(content: str, timestamp: str | None = None) -> str:
    """Frame a terminal error SSE event."""
    return _frame_sse_event(
        {
            "type": "error",
            "content": content,
            "timestamp": timestamp or _utc_now_iso(),
        }
    )


def _frame_sse_done_event(timestamp: str | None = None) -> str:
    """Frame a terminal done SSE event."""
    return _frame_sse_event({"type": "done", "timestamp": timestamp or _utc_now_iso()})


def _redact_token(token: str) -> str:
    clean = (token or "").strip()
    if not clean:
        return clean
    if len(clean) <= 10:
        return "***"
    return f"{clean[:6]}...{clean[-4:]}"


def _redact_token_like_text(value: str) -> str:
    """Redact common token-like patterns from freeform text."""
    if not isinstance(value, str) or not value:
        return value

    redacted = _TOKEN_BEARER_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{_redact_token(match.group(3))}",
        value,
    )
    redacted = _TOKEN_KEY_VALUE_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{_redact_token(match.group(3))}",
        redacted,
    )
    redacted = _TOKEN_PREFIX_PATTERN.sub(
        lambda match: _redact_token(match.group(0)),
        redacted,
    )
    redacted = _TOKEN_JWT_PATTERN.sub(
        lambda match: _redact_token(match.group(0)),
        redacted,
    )
    return redacted


def _redact_sse_value(value: Any) -> Any:
    """Recursively redact token-like strings in SSE payloads."""
    if isinstance(value, dict):
        return {key: _redact_sse_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_sse_value(item) for item in value]
    if isinstance(value, str):
        return _redact_token_like_text(value)
    return value


class AgentRunner:
    """Runs Claude Agent SDK queries in a background thread and streams events."""

    DEFAULT_CWD = "/app"
    DEFAULT_ALLOWED_TOOLS = [
        "Read",
        "Write",
        "Edit",
        "Bash",
        "Glob",
        "Grep",
        "WebSearch",
        "WebFetch",
        "Task",
    ]

    def __init__(
        self,
        cwd: str | None,
        token_provider: Callable[[], str],
        allowed_tools: Optional[list[str]] = None,
        permission_mode: str = "acceptEdits",
        session_store: Any | None = None,
        cwd_allowlist: Optional[list[str]] = None,
    ):
        self.cwd_allowlist = self._build_cwd_allowlist(cwd_allowlist)
        self._cwd = self.DEFAULT_CWD
        self.cwd = cwd
        self._token_provider = token_provider
        self.allowed_tools = allowed_tools or list(self.DEFAULT_ALLOWED_TOOLS)
        self.permission_mode = permission_mode
        self._session_store = session_store

        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._output_queues: Dict[str, queue.Queue] = {}
        self._run_timing: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    @property
    def cwd(self) -> str:
        return self._cwd

    @cwd.setter
    def cwd(self, value: str | None) -> None:
        self._cwd = self._enforce_cwd(value)

    def _build_cwd_allowlist(
        self, explicit_allowlist: Optional[list[str]] = None
    ) -> list[str]:
        raw_env_allowlist = (os.getenv("AGENT_RUNNER_CWD_ALLOWLIST") or "").strip()
        env_allowlist = [
            item.strip()
            for item in raw_env_allowlist.split(",")
            if item and item.strip()
        ]
        normalized: list[str] = []
        for path in [*(explicit_allowlist or []), *env_allowlist]:
            normalized_path = self._normalize_absolute_path(path)
            if normalized_path and normalized_path not in normalized:
                normalized.append(normalized_path)

        default_cwd = (
            self._normalize_absolute_path(self.DEFAULT_CWD) or self.DEFAULT_CWD
        )
        if default_cwd not in normalized:
            normalized.append(default_cwd)
        return normalized

    def _normalize_absolute_path(self, path_value: str | None) -> str:
        candidate = (path_value or "").strip()
        if not candidate or not os.path.isabs(candidate):
            return ""
        return os.path.normpath(candidate)

    def _is_cwd_allowlisted(self, candidate: str) -> bool:
        for allowed_root in self.cwd_allowlist:
            try:
                if os.path.commonpath([candidate, allowed_root]) == allowed_root:
                    return True
            except ValueError:
                continue
        return False

    def _enforce_cwd(self, path_value: str | None) -> str:
        normalized = self._normalize_absolute_path(path_value)
        if normalized and self._is_cwd_allowlisted(normalized):
            return normalized

        fallback = self._normalize_absolute_path(self.DEFAULT_CWD) or self.DEFAULT_CWD
        if normalized:
            logger.warning(
                "Rejecting non-allowlisted cwd '%s'; falling back to '%s'",
                normalized,
                fallback,
            )
        return fallback

    def create_session(self, title: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chat session."""
        session_id = secrets.token_hex(16)
        now = _utc_now_iso()
        session = {
            "id": session_id,
            "title": title or "New chat",
            "created_at": now,
            "updated_at": now,
            "sdk_session_id": None,
            "status": "idle",
            "messages": [],
            "last_error": None,
            "queue_wait_ms": None,
            "first_event_latency_ms": None,
            "total_runtime_ms": None,
        }
        with self._lock:
            self._sessions[session_id] = session
            self._output_queues[session_id] = queue.Queue()
        return self.get_session(session_id) or {}

    def attach_store(self, session_store: Any | None) -> None:
        """Attach or replace the persistence store used for callbacks."""
        self._session_store = session_store

    def ensure_session(
        self,
        session_id: str,
        *,
        title: str | None = None,
        sdk_session_id: str | None = None,
    ) -> Dict[str, Any]:
        """Ensure runtime session structures exist for a known external session id."""
        with self._lock:
            existing = self._sessions.get(session_id)
            if existing is not None:
                if title:
                    existing["title"] = title
                if sdk_session_id and not existing.get("sdk_session_id"):
                    existing["sdk_session_id"] = sdk_session_id
                return dict(existing)

            now = _utc_now_iso()
            session = {
                "id": session_id,
                "title": title or "New chat",
                "created_at": now,
                "updated_at": now,
                "sdk_session_id": sdk_session_id,
                "status": "idle",
                "messages": [],
                "last_error": None,
                "queue_wait_ms": None,
                "first_event_latency_ms": None,
                "total_runtime_ms": None,
            }
            self._sessions[session_id] = session
            self._output_queues[session_id] = queue.Queue()
            return dict(session)

    def list_sessions(self) -> list[Dict[str, Any]]:
        """Return session summaries sorted by last update time."""
        with self._lock:
            rows = []
            for session in self._sessions.values():
                rows.append(
                    {
                        "id": session["id"],
                        "title": session.get("title") or "New chat",
                        "status": session.get("status", "idle"),
                        "created_at": session.get("created_at"),
                        "updated_at": session.get("updated_at"),
                        "message_count": len(session.get("messages") or []),
                        "last_error": session.get("last_error"),
                        "queue_wait_ms": session.get("queue_wait_ms"),
                        "first_event_latency_ms": session.get("first_event_latency_ms"),
                        "total_runtime_ms": session.get("total_runtime_ms"),
                    }
                )
        rows.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
        return rows

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return {
                "id": session["id"],
                "title": session.get("title") or "New chat",
                "status": session.get("status", "idle"),
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "sdk_session_id": session.get("sdk_session_id"),
                "messages": list(session.get("messages") or []),
                "last_error": session.get("last_error"),
                "queue_wait_ms": session.get("queue_wait_ms"),
                "first_event_latency_ms": session.get("first_event_latency_ms"),
                "total_runtime_ms": session.get("total_runtime_ms"),
            }

    def has_session(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    def send_message(self, session_id: str, user_message: str) -> None:
        """Append user message and start a background run."""
        message = (user_message or "").strip()
        if not message:
            raise ValueError("Message cannot be empty")

        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Session not found: {session_id}")
            if session.get("status") == "running":
                raise RunnerError("Session is already running")

            now = _utc_now_iso()
            session["status"] = "running"
            session["updated_at"] = now
            session["last_error"] = None
            session["queue_wait_ms"] = None
            session["first_event_latency_ms"] = None
            session["total_runtime_ms"] = None
            self._run_timing[session_id] = {
                "enqueued_at": time.perf_counter(),
                "started_at": None,
                "first_event_recorded": False,
            }
            self._persist_session_update(
                session_id,
                {
                    "status": "running",
                    "updated_at": now,
                    "last_error": None,
                    "queue_wait_ms": None,
                    "first_event_latency_ms": None,
                    "total_runtime_ms": None,
                },
            )

        thread = threading.Thread(
            target=self._run_agent,
            args=(session_id, message),
            daemon=True,
        )
        thread.start()

    def get_stream(
        self, session_id: str, keepalive_seconds: int = 20
    ) -> Generator[str, None, None]:
        """Yield Server-Sent Events from the session queue."""
        q = self._get_queue_or_raise(session_id)
        while True:
            try:
                event = q.get(timeout=keepalive_seconds)
            except queue.Empty:
                yield _frame_sse_ping_event()
                continue

            event = _redact_sse_value(event)
            event_type = event.get("type")
            if event_type == "error":
                yield _frame_sse_error_event(
                    content=str(event.get("content") or ""),
                    timestamp=event.get("timestamp"),
                )
                break
            if event_type == "done":
                yield _frame_sse_done_event(timestamp=event.get("timestamp"))
                break

            yield _frame_sse_event(event)

    def _run_agent(self, session_id: str, user_message: str) -> None:
        """Background worker thread for a single agent run."""
        q = self._get_queue_or_raise(session_id)
        assistant_chunks: list[str] = []
        stderr_lines: list[str] = []
        streamed_error: str | None = None
        emitted_error_event = False
        loop: Optional[asyncio.AbstractEventLoop] = None

        try:
            self._record_run_started(session_id)
            token = (self._token_provider() or "").strip()
            if not token:
                raise RunnerError("Claude token is not configured")

            sdk = self._load_sdk()

            with self._lock:
                session = self._sessions.get(session_id) or {}
                resume_id = session.get("sdk_session_id")

            def _stderr_callback(line: str) -> None:
                text = (line or "").strip()
                if not text:
                    return
                text = _redact_token_like_text(text)
                stderr_lines.append(text)
                # Keep bounded memory while preserving most recent context.
                if len(stderr_lines) > 50:
                    del stderr_lines[:-50]

            options = self._build_options(
                options_cls=sdk["options_cls"],
                token=token,
                resume_id=resume_id,
                stderr_callback=_stderr_callback,
            )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def run_query() -> None:
                nonlocal streamed_error, emitted_error_event
                async for message in sdk["query"](prompt=user_message, options=options):
                    payload = self._message_payload(message)
                    self._capture_sdk_session_id(session_id, message, payload)
                    event = self._parse_message(payload)
                    if not event:
                        continue

                    self._record_first_event_latency(session_id)
                    q.put(event)
                    self._persist_event(session_id, event)
                    if event["type"] in ("text", "result"):
                        content = (event.get("content") or "").strip()
                        if content:
                            assistant_chunks.append(content)
                    if event["type"] == "error":
                        content = (event.get("content") or "").strip()
                        if content:
                            streamed_error = content
                        emitted_error_event = True

            loop.run_until_complete(run_query())

            if assistant_chunks:
                self._append_assistant_message(session_id, "\n".join(assistant_chunks))

            self._set_session_state(session_id, status="idle", last_error=None)
            q.put(
                {
                    "type": "done",
                    "timestamp": _utc_now_iso(),
                    "metrics": self._record_total_runtime(session_id),
                }
            )
        except Exception as exc:  # pragma: no cover - runtime safety path
            message = str(exc) or "Agent execution failed"
            if stderr_lines:
                message = f"{message}\nCLI stderr: {' | '.join(stderr_lines[-10:])}"

            # Prefer meaningful streamed errors over generic SDK process tail errors.
            if streamed_error and (
                "Check stderr output for details" in message
                or "Command failed with exit code" in message
            ):
                if stderr_lines:
                    message = f"{streamed_error}\nCLI stderr: {' | '.join(stderr_lines[-10:])}"
                else:
                    message = streamed_error

            message = _redact_token_like_text(message)
            logger.exception("Agent run failed for session %s: %s", session_id, message)
            self._set_session_state(session_id, status="error", last_error=message)
            metrics = self._record_total_runtime(session_id)
            if emitted_error_event and streamed_error:
                return
            q.put(
                {
                    "type": "error",
                    "content": message,
                    "timestamp": _utc_now_iso(),
                    "metrics": metrics,
                }
            )
        finally:
            if loop is not None:
                try:
                    loop.close()
                except Exception:
                    pass
                asyncio.set_event_loop(None)

    def _load_sdk(self) -> Dict[str, Any]:
        """Load Claude Agent SDK lazily to avoid crashing app startup."""
        last_error: Optional[Exception] = None
        for module_name in ("claude_agent_sdk", "claude_code_sdk"):
            try:
                module = importlib.import_module(module_name)
                query = getattr(module, "query", None)
                options_cls = getattr(module, "ClaudeAgentOptions", None)
                if query is None or options_cls is None:
                    raise RunnerError(
                        f"{module_name} is missing required symbols (query, ClaudeAgentOptions)"
                    )
                return {
                    "module_name": module_name,
                    "query": query,
                    "options_cls": options_cls,
                }
            except Exception as exc:
                last_error = exc
                continue
        raise RunnerError(
            "Claude Agent SDK is not installed. Add 'claude-agent-sdk' to dependencies."
        ) from last_error

    def _build_options(
        self,
        options_cls: Any,
        token: str,
        resume_id: Optional[str],
        stderr_callback: Optional[Callable[[str], None]] = None,
    ) -> Any:
        """Build options compatible with multiple SDK versions."""
        params = inspect.signature(options_cls).parameters
        options_kwargs: dict[str, Any] = {}

        # Tool + runtime controls.
        if "allowed_tools" in params:
            options_kwargs["allowed_tools"] = list(self.allowed_tools)
        elif "tools" in params:
            options_kwargs["tools"] = list(self.allowed_tools)
        if "permission_mode" in params:
            options_kwargs["permission_mode"] = self.permission_mode
        if "setting_sources" in params:
            options_kwargs["setting_sources"] = ["project"]
        if "workspace" in params:
            options_kwargs["workspace"] = self.cwd
        if "cwd" in params:
            options_kwargs["cwd"] = self.cwd
        if resume_id and "resume" in params:
            options_kwargs["resume"] = resume_id

        # Prefer explicit auth options when available, and always provide env auth
        # for newer SDKs that read credentials from process environment.
        auth_set = False
        for auth_key in ("auth_token", "api_key", "token"):
            if auth_key in params:
                options_kwargs[auth_key] = token
                auth_set = True
                break
        auth_env = self._build_auth_env(token)
        runtime_launcher = self._build_runtime_launcher(token)
        if auth_env and "env" in params:
            options_kwargs["env"] = auth_env
        for runtime_key in ("runtime_launcher", "runtime"):
            if runtime_key in params:
                options_kwargs[runtime_key] = runtime_launcher
                break
        if stderr_callback and "stderr" in params:
            options_kwargs["stderr"] = stderr_callback
        if "extra_args" in params:
            # Request verbose CLI stderr so runtime auth/config errors are visible.
            options_kwargs["extra_args"] = {"debug-to-stderr": None}

        try:
            return options_cls(**options_kwargs)
        except TypeError:
            # Last-ditch fallback with minimal options for older SDK variants.
            fallback_kwargs: dict[str, Any] = {}
            for key in (
                "workspace",
                "cwd",
                "allowed_tools",
                "tools",
                "resume",
                "runtime_launcher",
                "runtime",
            ):
                if key in options_kwargs:
                    fallback_kwargs[key] = options_kwargs[key]
            if not auth_set:
                for auth_key in ("auth_token", "api_key", "token"):
                    if auth_key in params:
                        fallback_kwargs[auth_key] = token
                        break
            if auth_env and "env" in params:
                fallback_kwargs["env"] = auth_env
            if stderr_callback and "stderr" in params:
                fallback_kwargs["stderr"] = stderr_callback
            if "extra_args" in params:
                fallback_kwargs["extra_args"] = {"debug-to-stderr": None}
            return options_cls(**fallback_kwargs)

    def _build_runtime_launcher(self, token: str) -> Callable[..., Any]:
        """Create a runtime launcher that injects dashboard token auth env."""
        auth_env = self._build_auth_env(token)

        async def _runtime_launcher(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
            runtime_args = list(args)
            if len(runtime_args) == 1 and isinstance(runtime_args[0], (list, tuple)):
                runtime_args = list(runtime_args[0])
            if not runtime_args or str(runtime_args[0]).strip() != "claude":
                runtime_args.insert(0, "claude")

            merged_env = dict(os.environ)
            provided_env = kwargs.pop("env", None)
            if isinstance(provided_env, dict):
                merged_env.update({str(k): str(v) for k, v in provided_env.items()})
            merged_env.update(auth_env)

            return await asyncio.create_subprocess_exec(
                *[str(arg) for arg in runtime_args],
                env=merged_env,
                **kwargs,
            )

        return _runtime_launcher

    def _build_auth_env(self, token: str) -> Dict[str, str]:
        """Map dashboard token into auth env vars recognized by Claude CLI/SDK."""
        candidate = (token or "").strip()
        if not candidate:
            return {}

        env = {"CLAUDE_SETUP_TOKEN": candidate}

        # setup-token OAuth artifact
        if candidate.startswith("sk-ant-oat"):
            env["CLAUDE_CODE_OAUTH_TOKEN"] = candidate
            env["ANTHROPIC_AUTH_TOKEN"] = candidate
            return env

        # standard Anthropic API key
        if candidate.startswith("sk-ant-"):
            env["ANTHROPIC_API_KEY"] = candidate
            env["CLAUDE_API_KEY"] = candidate
            return env

        # Fallback for opaque token formats
        env["CLAUDE_CODE_OAUTH_TOKEN"] = candidate
        env["ANTHROPIC_AUTH_TOKEN"] = candidate
        return env

    def _capture_sdk_session_id(
        self, session_id: str, raw_message: Any, payload: Dict[str, Any]
    ) -> None:
        sdk_session_id = payload.get("session_id") or getattr(
            raw_message, "session_id", None
        )
        if not sdk_session_id:
            return
        with self._lock:
            session = self._sessions.get(session_id)
            if session and not session.get("sdk_session_id"):
                session["sdk_session_id"] = sdk_session_id
                session["updated_at"] = _utc_now_iso()
                self._persist_session_update(
                    session_id,
                    {
                        "sdk_session_id": sdk_session_id,
                        "updated_at": session["updated_at"],
                    },
                )

    def _message_payload(self, message: Any) -> Dict[str, Any]:
        if isinstance(message, dict):
            return dict(message)

        payload: Dict[str, Any] = {}
        for key in (
            "type",
            "subtype",
            "role",
            "session_id",
            "content",
            "text",
            "delta",
            "tool_name",
            "tool_input",
            "tool_result",
            "result",
            "is_error",
            "error",
            "message",
        ):
            if hasattr(message, key):
                payload[key] = getattr(message, key)
        return payload

    def _parse_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_type = str(payload.get("type", "")).lower()
        role = str(payload.get("role", "")).lower()

        if payload.get("tool_name"):
            return {
                "type": "tool_use",
                "tool": str(payload.get("tool_name")),
                "input": self._summarize_tool_input(
                    payload.get("tool_name"), payload.get("tool_input")
                ),
                "timestamp": _utc_now_iso(),
            }

        if payload.get("tool_result") is not None:
            tool_result = _redact_token_like_text(
                self._stringify(payload.get("tool_result"))
            )
            return {
                "type": "tool_result",
                "content": self._truncate(tool_result, 600),
                "timestamp": _utc_now_iso(),
            }

        if payload.get("result") is not None:
            result_content = _redact_token_like_text(
                self._stringify(payload.get("result"))
            )
            if bool(payload.get("is_error")):
                return {
                    "type": "error",
                    "content": result_content,
                    "timestamp": _utc_now_iso(),
                }
            return {
                "type": "result",
                "content": result_content,
                "timestamp": _utc_now_iso(),
            }

        text = self._extract_text(payload)
        if text:
            text = _redact_token_like_text(text)
            if msg_type in ("assistant", "assistant_message") or role == "assistant":
                return {"type": "text", "content": text, "timestamp": _utc_now_iso()}
            if msg_type in ("system", "status"):
                return {"type": "system", "content": text, "timestamp": _utc_now_iso()}

        if msg_type in ("error", "exception"):
            content = text or self._truncate(
                _redact_token_like_text(self._stringify(payload)),
                500,
            )
            content = _redact_token_like_text(content)
            return {"type": "error", "content": content, "timestamp": _utc_now_iso()}

        return None

    def _summarize_tool_input(self, tool_name: str, tool_input: Any) -> str:
        tool = str(tool_name or "").strip()
        if not isinstance(tool_input, dict):
            return _redact_token_like_text(
                self._truncate(self._stringify(tool_input), 180)
            )

        if tool == "Read":
            return f"Reading {tool_input.get('file_path', '?')}"
        if tool == "Bash":
            command = self._truncate(tool_input.get("command", ""), 120)
            return f"Running: {_redact_token_like_text(command)}"
        if tool == "Glob":
            return f"Searching for {tool_input.get('pattern', '?')}"
        if tool == "Grep":
            return f"Searching for '{tool_input.get('pattern', '?')}'"
        if tool == "Write":
            return f"Writing {tool_input.get('file_path', '?')}"
        if tool == "Edit":
            return f"Editing {tool_input.get('file_path', '?')}"
        if tool == "Task":
            return f"Spawning subagent: {tool_input.get('description', '?')}"
        if tool == "WebSearch":
            return f"Searching web: {tool_input.get('query', '?')}"
        if tool == "WebFetch":
            return f"Fetching URL: {tool_input.get('url', '?')}"
        input_summary = self._truncate(self._stringify(tool_input), 120)
        return f"{tool}: {_redact_token_like_text(input_summary)}"

    def _extract_text(self, payload: Dict[str, Any]) -> str:
        content = payload.get("content")
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, str):
                    chunks.append(item)
                elif isinstance(item, dict):
                    if isinstance(item.get("text"), str):
                        chunks.append(item["text"])
                    elif isinstance(item.get("content"), str):
                        chunks.append(item["content"])
            return "".join(chunks)

        for key in ("text", "delta", "message"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
        return ""

    def _append_assistant_message(self, session_id: str, content: str) -> None:
        now = _utc_now_iso()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            session["messages"].append(
                {
                    "role": "assistant",
                    "content": content,
                    "timestamp": now,
                }
            )
            session["updated_at"] = now
        self._persist_message(
            session_id,
            {
                "role": "assistant",
                "content": content,
                "timestamp": now,
                "type": "message",
                "metadata": {},
            },
        )

    def _set_session_state(
        self, session_id: str, status: str, last_error: Optional[str]
    ) -> None:
        now = _utc_now_iso()
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            session["status"] = status
            session["last_error"] = last_error
            session["updated_at"] = now
        self._persist_session_update(
            session_id,
            {"status": status, "last_error": last_error, "updated_at": now},
        )

    def _record_run_started(self, session_id: str) -> None:
        updates: Dict[str, Any] = {}
        now_iso = _utc_now_iso()

        with self._lock:
            state = self._run_timing.get(session_id)
            if not state:
                state = {
                    "enqueued_at": time.perf_counter(),
                    "started_at": None,
                    "first_event_recorded": False,
                }
                self._run_timing[session_id] = state
            if state.get("started_at") is not None:
                return

            started_at = time.perf_counter()
            state["started_at"] = started_at
            enqueued_at = state.get("enqueued_at")
            queue_wait_ms: Optional[int]
            if isinstance(enqueued_at, (int, float)):
                queue_wait_ms = max(0, int((started_at - enqueued_at) * 1000))
            else:
                queue_wait_ms = 0

            session = self._sessions.get(session_id)
            if session is not None:
                session["queue_wait_ms"] = queue_wait_ms
                session["updated_at"] = now_iso
                updates = {"queue_wait_ms": queue_wait_ms, "updated_at": now_iso}

        if updates:
            self._persist_session_update(session_id, updates)

    def _record_first_event_latency(self, session_id: str) -> None:
        updates: Dict[str, Any] = {}
        now_iso = _utc_now_iso()

        with self._lock:
            state = self._run_timing.get(session_id)
            if not state or bool(state.get("first_event_recorded")):
                return
            state["first_event_recorded"] = True

            enqueued_at = state.get("enqueued_at")
            first_event_latency_ms: Optional[int] = None
            if isinstance(enqueued_at, (int, float)):
                first_event_latency_ms = max(
                    0, int((time.perf_counter() - enqueued_at) * 1000)
                )

            session = self._sessions.get(session_id)
            if session is not None:
                session["first_event_latency_ms"] = first_event_latency_ms
                session["updated_at"] = now_iso
                updates = {
                    "first_event_latency_ms": first_event_latency_ms,
                    "updated_at": now_iso,
                }

        if updates:
            self._persist_session_update(session_id, updates)

    def _record_total_runtime(self, session_id: str) -> Dict[str, Optional[int]]:
        updates: Dict[str, Any] = {}
        now_iso = _utc_now_iso()
        metrics: Dict[str, Optional[int]] = {
            "queue_wait_ms": None,
            "first_event_latency_ms": None,
            "total_runtime_ms": None,
        }

        with self._lock:
            state = self._run_timing.get(session_id)
            started_at = state.get("started_at") if state else None
            total_runtime_ms: Optional[int] = None
            if isinstance(started_at, (int, float)):
                total_runtime_ms = max(0, int((time.perf_counter() - started_at) * 1000))

            session = self._sessions.get(session_id)
            if session is not None:
                if total_runtime_ms is not None:
                    session["total_runtime_ms"] = total_runtime_ms
                    updates = {"total_runtime_ms": total_runtime_ms, "updated_at": now_iso}
                    session["updated_at"] = now_iso
                metrics = {
                    "queue_wait_ms": session.get("queue_wait_ms"),
                    "first_event_latency_ms": session.get("first_event_latency_ms"),
                    "total_runtime_ms": session.get("total_runtime_ms"),
                }

            self._run_timing.pop(session_id, None)

        if updates:
            self._persist_session_update(session_id, updates)

        return metrics

    def _persist_session_update(self, session_id: str, updates: Dict[str, Any]) -> None:
        store = self._session_store
        if store is None:
            return
        try:
            store.update_session(session_id, updates)
        except Exception:
            logger.exception("Failed to persist session update for %s", session_id)

    def _persist_message(self, session_id: str, message: Dict[str, Any]) -> None:
        store = self._session_store
        if store is None:
            return
        try:
            store.append_message(session_id, message)
        except Exception:
            logger.exception("Failed to persist message for %s", session_id)

    def _persist_event(self, session_id: str, event: Dict[str, Any]) -> None:
        store = self._session_store
        if store is None:
            return

        raw_type = str(event.get("type", "")).strip().lower()
        if not raw_type:
            return

        event_type = raw_type
        payload: Dict[str, Any] = {}
        if raw_type == "tool_use":
            payload = {
                "kind": "tool_use",
                "tool": event.get("tool"),
                "input": event.get("input"),
            }
        elif raw_type == "tool_result":
            payload = {
                "kind": "tool_result",
                "content": event.get("content"),
            }
        elif raw_type in ("text", "result", "error", "system"):
            payload = {"content": event.get("content"), "kind": raw_type}
        elif raw_type == "done":
            payload = {"kind": "done"}
        else:
            return

        try:
            store.append_event(
                session_id,
                {
                    "type": event_type,
                    "payload": payload,
                    "timestamp": event.get("timestamp") or _utc_now_iso(),
                },
            )
        except Exception:
            logger.exception("Failed to persist event for %s", session_id)

    def _get_queue_or_raise(self, session_id: str) -> queue.Queue:
        with self._lock:
            q = self._output_queues.get(session_id)
        if q is None:
            raise KeyError(f"Session not found: {session_id}")
        return q

    @staticmethod
    def _derive_title(message: str) -> str:
        first_line = (message or "").strip().splitlines()[0] if message else "New chat"
        return (first_line[:57] + "...") if len(first_line) > 60 else first_line

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)

    @staticmethod
    def _truncate(value: Any, limit: int) -> str:
        text = AgentRunner._stringify(value)
        if len(text) <= limit:
            return text
        return text[: max(limit - 3, 0)] + "..."
