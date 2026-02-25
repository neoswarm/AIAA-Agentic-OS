"""
Agent runner service for streaming Claude Agent SDK responses over SSE.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import queue
import secrets
import threading
from datetime import datetime
from typing import Any, Callable, Dict, Generator, Optional


logger = logging.getLogger(__name__)


class RunnerError(RuntimeError):
    """Raised when the chat runner cannot execute a request."""


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


class AgentRunner:
    """Runs Claude Agent SDK queries in a background thread and streams events."""

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
        cwd: str,
        token_provider: Callable[[], str],
        allowed_tools: Optional[list[str]] = None,
        permission_mode: str = "acceptEdits",
    ):
        self.cwd = cwd
        self._token_provider = token_provider
        self.allowed_tools = allowed_tools or list(self.DEFAULT_ALLOWED_TOOLS)
        self.permission_mode = permission_mode

        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._output_queues: Dict[str, queue.Queue] = {}
        self._lock = threading.RLock()

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
        }
        with self._lock:
            self._sessions[session_id] = session
            self._output_queues[session_id] = queue.Queue()
        return self.get_session(session_id) or {}

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
            session["messages"].append(
                {
                    "role": "user",
                    "content": message,
                    "timestamp": now,
                }
            )
            if (session.get("title") or "New chat") == "New chat":
                session["title"] = self._derive_title(message)

        thread = threading.Thread(
            target=self._run_agent,
            args=(session_id, message),
            daemon=True,
        )
        thread.start()

    def get_stream(self, session_id: str, keepalive_seconds: int = 20) -> Generator[str, None, None]:
        """Yield Server-Sent Events from the session queue."""
        q = self._get_queue_or_raise(session_id)
        while True:
            try:
                event = q.get(timeout=keepalive_seconds)
            except queue.Empty:
                event = {"type": "ping", "timestamp": _utc_now_iso()}
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            if event.get("type") in ("done", "error"):
                break

    def _run_agent(self, session_id: str, user_message: str) -> None:
        """Background worker thread for a single agent run."""
        q = self._get_queue_or_raise(session_id)
        assistant_chunks: list[str] = []
        loop: Optional[asyncio.AbstractEventLoop] = None

        try:
            token = (self._token_provider() or "").strip()
            if not token:
                raise RunnerError("Claude token is not configured")

            sdk = self._load_sdk()

            with self._lock:
                session = self._sessions.get(session_id) or {}
                resume_id = session.get("sdk_session_id")

            options = self._build_options(
                options_cls=sdk["options_cls"],
                token=token,
                resume_id=resume_id,
            )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def run_query() -> None:
                async for message in sdk["query"](prompt=user_message, options=options):
                    payload = self._message_payload(message)
                    self._capture_sdk_session_id(session_id, message, payload)
                    event = self._parse_message(payload)
                    if not event:
                        continue

                    q.put(event)
                    if event["type"] in ("text", "result"):
                        content = (event.get("content") or "").strip()
                        if content:
                            assistant_chunks.append(content)

            loop.run_until_complete(run_query())

            if assistant_chunks:
                self._append_assistant_message(session_id, "\n".join(assistant_chunks))

            self._set_session_state(session_id, status="idle", last_error=None)
            q.put({"type": "done", "timestamp": _utc_now_iso()})
        except Exception as exc:  # pragma: no cover - runtime safety path
            message = str(exc) or "Agent execution failed"
            logger.exception("Agent run failed for session %s: %s", session_id, message)
            self._set_session_state(session_id, status="error", last_error=message)
            q.put({"type": "error", "content": message, "timestamp": _utc_now_iso()})
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
                return {"module_name": module_name, "query": query, "options_cls": options_cls}
            except Exception as exc:
                last_error = exc
                continue
        raise RunnerError(
            "Claude Agent SDK is not installed. Add 'claude-agent-sdk' to dependencies."
        ) from last_error

    def _build_options(self, options_cls: Any, token: str, resume_id: Optional[str]) -> Any:
        """Build options compatible with current SDK version."""
        options_kwargs = {
            "auth_token": token,
            "allowed_tools": list(self.allowed_tools),
            "permission_mode": self.permission_mode,
            "setting_sources": ["project"],
            "cwd": self.cwd,
        }
        if resume_id:
            options_kwargs["resume"] = resume_id

        try:
            return options_cls(**options_kwargs)
        except TypeError:
            fallback_kwargs = {
                "auth_token": token,
                "cwd": self.cwd,
                "allowed_tools": list(self.allowed_tools),
            }
            if resume_id:
                fallback_kwargs["resume"] = resume_id
            return options_cls(**fallback_kwargs)

    def _capture_sdk_session_id(self, session_id: str, raw_message: Any, payload: Dict[str, Any]) -> None:
        sdk_session_id = payload.get("session_id") or getattr(raw_message, "session_id", None)
        if not sdk_session_id:
            return
        with self._lock:
            session = self._sessions.get(session_id)
            if session and not session.get("sdk_session_id"):
                session["sdk_session_id"] = sdk_session_id
                session["updated_at"] = _utc_now_iso()

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
                "input": self._summarize_tool_input(payload.get("tool_name"), payload.get("tool_input")),
                "timestamp": _utc_now_iso(),
            }

        if payload.get("tool_result") is not None:
            return {
                "type": "tool_result",
                "content": self._truncate(self._stringify(payload.get("tool_result")), 600),
                "timestamp": _utc_now_iso(),
            }

        if payload.get("result") is not None:
            return {
                "type": "result",
                "content": self._stringify(payload.get("result")),
                "timestamp": _utc_now_iso(),
            }

        text = self._extract_text(payload)
        if text:
            if msg_type in ("assistant", "assistant_message") or role == "assistant":
                return {"type": "text", "content": text, "timestamp": _utc_now_iso()}
            if msg_type in ("system", "status"):
                return {"type": "system", "content": text, "timestamp": _utc_now_iso()}

        if msg_type in ("error", "exception"):
            content = text or self._truncate(self._stringify(payload), 500)
            return {"type": "error", "content": content, "timestamp": _utc_now_iso()}

        return None

    def _summarize_tool_input(self, tool_name: str, tool_input: Any) -> str:
        tool = str(tool_name or "").strip()
        if not isinstance(tool_input, dict):
            return self._truncate(self._stringify(tool_input), 180)

        if tool == "Read":
            return f"Reading {tool_input.get('file_path', '?')}"
        if tool == "Bash":
            return f"Running: {self._truncate(tool_input.get('command', ''), 120)}"
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
        return f"{tool}: {self._truncate(self._stringify(tool_input), 120)}"

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
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            session["messages"].append(
                {
                    "role": "assistant",
                    "content": content,
                    "timestamp": _utc_now_iso(),
                }
            )
            session["updated_at"] = _utc_now_iso()

    def _set_session_state(self, session_id: str, status: str, last_error: Optional[str]) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            session["status"] = status
            session["last_error"] = last_error
            session["updated_at"] = _utc_now_iso()

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
