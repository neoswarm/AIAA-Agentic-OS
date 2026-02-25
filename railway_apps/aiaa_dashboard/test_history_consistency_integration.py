#!/usr/bin/env python3
"""DB/Redis integration tests for session history consistency."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Make dashboard app modules importable when running pytest from repo root.
sys.path.insert(0, str(Path(__file__).parent))

import database  # noqa: E402
import models  # noqa: E402

try:
    import services.chat_store as chat_store  # noqa: E402
except Exception:
    chat_store = None

_REQUIRED_MODEL_APIS = [
    "upsert_session_history",
    "log_session_history_message",
    "get_session_history_session",
    "get_session_history_messages",
    "count_session_history_messages",
]
_missing_model_apis = [
    name for name in _REQUIRED_MODEL_APIS if not hasattr(models, name)
]
_has_redis_chat_store = bool(chat_store and hasattr(chat_store, "RedisChatStore"))
_has_history_stack = _has_redis_chat_store and not _missing_model_apis
_skip_reason = (
    "RedisChatStore and/or session history model APIs are unavailable in this branch"
)

if _missing_model_apis:
    _skip_reason += f" (missing model APIs: {', '.join(_missing_model_apis)})"
if not _has_redis_chat_store:
    _skip_reason += " (missing services.chat_store.RedisChatStore)"

RedisChatStore = getattr(chat_store, "RedisChatStore", None)

requires_history_stack = pytest.mark.skipif(
    not _has_history_stack,
    reason=_skip_reason,
)


class FakePipeline:
    """Minimal Redis pipeline that commits writes on execute()."""

    def __init__(self, client: "FakeRedis") -> None:
        self._client = client
        self._commands: list[tuple[Any, ...]] = []

    def set(self, key: str, value: str) -> "FakePipeline":
        self._commands.append(("set", key, value))
        return self

    def rpush(self, key: str, value: str) -> "FakePipeline":
        self._commands.append(("rpush", key, value))
        return self

    def expire(self, key: str, ttl_seconds: int) -> "FakePipeline":
        self._commands.append(("expire", key, ttl_seconds))
        return self

    def execute(self) -> list[bool]:
        for command in self._commands:
            op = command[0]
            if op == "set":
                _, key, value = command
                self._client.values[key] = value
            elif op == "rpush":
                _, key, value = command
                self._client.lists.setdefault(key, []).append(value)
            elif op == "expire":
                _, key, ttl = command
                self._client.expiry[key] = ttl
        return [True] * len(self._commands)


class FakeRedis:
    """Minimal in-memory Redis-like client for deterministic tests."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.expiry: dict[str, int] = {}

    def pipeline(self, transaction: bool = True) -> FakePipeline:
        assert transaction is True
        return FakePipeline(self)

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        items = self.lists.get(key, [])
        if end == -1:
            return items[start:]
        return items[start : end + 1]


def _reset_db_connection() -> None:
    """Close and clear thread-local DB connection between tests."""
    conn = getattr(database._thread_local, "connection", None)
    if conn is not None:
        conn.close()
        delattr(database._thread_local, "connection")


@pytest.fixture()
def isolated_db(tmp_path: Path):
    """Initialize a fresh SQLite DB for each integration test."""
    _reset_db_connection()
    database.set_db_path(str(tmp_path / "dashboard.db"))
    database.init_db()

    # Guard for branches where the migration is not yet present.
    history_table = database.query_one(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'session_history_messages'"
    )
    if history_table is None:
        pytest.skip("session_history_messages table is not available")

    yield
    _reset_db_connection()


def _create_redis_store() -> Any:
    """Build a RedisChatStore compatible with current constructor variants."""
    if RedisChatStore is None:
        raise RuntimeError("RedisChatStore is unavailable")

    redis_client = FakeRedis()
    try:
        return RedisChatStore(
            redis_client,
            key_prefix="test:chat:history",
            session_ttl_seconds=3600,
            message_ttl_seconds=3600,
            event_ttl_seconds=600,
        )
    except TypeError:
        return RedisChatStore(
            redis_client,
            key_prefix="test:chat:history",
            session_ttl_seconds=3600,
            message_ttl_seconds=3600,
        )


def _dual_write_messages(
    store: Any, session_id: str, messages: list[dict[str, Any]]
) -> None:
    """Write each message to both Redis history and DB history."""
    models.upsert_session_history(
        session_id,
        metadata={"title": "History Consistency", "status": "active"},
    )

    for message in messages:
        store.append_message(
            session_id,
            message,
            session_updates={"title": "History Consistency", "status": "active"},
        )
        models.log_session_history_message(
            session_id=session_id,
            role=message["role"],
            content=message["content"],
            metadata=message.get("metadata"),
        )


def _metadata_to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def _normalize_messages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "role": row.get("role"),
            "content": row.get("content"),
            "metadata": _metadata_to_dict(row.get("metadata")),
        }
        for row in rows
    ]


@requires_history_stack
def test_history_order_consistency_between_db_and_redis(isolated_db):
    store = _create_redis_store()
    session_id = "hist-consistency-order"
    messages = [
        {"role": "user", "content": "Hi", "metadata": {"turn": 1}},
        {"role": "assistant", "content": "Hello", "metadata": {"turn": 2}},
        {"role": "user", "content": "Summarize this", "metadata": {"turn": 3}},
    ]

    _dual_write_messages(store, session_id, messages)

    redis_history = _normalize_messages(store.get_messages(session_id))
    db_history = _normalize_messages(
        models.get_session_history_messages(session_id, limit=100, offset=0)
    )

    assert db_history == redis_history
    assert models.count_session_history_messages(session_id) == len(messages)


@requires_history_stack
def test_history_pagination_consistency_between_db_and_redis(isolated_db):
    store = _create_redis_store()
    session_id = "hist-consistency-pagination"
    messages = [
        {"role": "user", "content": f"Message {i}", "metadata": {"index": i}}
        for i in range(1, 6)
    ]

    _dual_write_messages(store, session_id, messages)

    limit = 2
    offset = 2

    db_page = models.get_session_history_messages(
        session_id, limit=limit, offset=offset
    )
    redis_page = store.get_messages(session_id)[offset : offset + limit]

    assert _normalize_messages(db_page) == _normalize_messages(redis_page)


@requires_history_stack
def test_session_metadata_consistency_between_db_and_redis(isolated_db):
    store = _create_redis_store()
    session_id = "hist-consistency-session-metadata"

    models.upsert_session_history(
        session_id,
        metadata={"title": "History Consistency", "status": "active"},
    )

    store.append_message(
        session_id,
        {"role": "user", "content": "Persist this", "metadata": {"turn": 1}},
        session_updates={"title": "History Consistency", "status": "active"},
    )
    models.log_session_history_message(
        session_id=session_id,
        role="user",
        content="Persist this",
        metadata={"turn": 1},
    )

    db_session = models.get_session_history_session(session_id)
    redis_session = store.get_session(session_id)

    assert db_session is not None
    assert redis_session is not None
    assert db_session["id"] == redis_session["id"] == session_id

    db_metadata = _metadata_to_dict(db_session.get("metadata"))
    assert db_metadata.get("title") == redis_session.get("title")
    assert db_metadata.get("status") == redis_session.get("status")
