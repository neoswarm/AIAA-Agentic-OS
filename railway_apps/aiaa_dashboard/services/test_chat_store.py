#!/usr/bin/env python3
"""Tests for RedisChatStore."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Add dashboard app directory so `services` is importable when pytest runs
# from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.chat_store import EventSchema, MessageSchema, RedisChatStore


class FakePipeline:
    """Minimal Redis pipeline that commits commands on execute()."""

    def __init__(self, client: "FakeRedis", *, should_fail: bool = False) -> None:
        self._client = client
        self._should_fail = should_fail
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
        if self._should_fail:
            raise RuntimeError("simulated transaction failure")

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
    """Minimal in-memory Redis-like client for testing."""

    def __init__(self, *, fail_execute: bool = False) -> None:
        self.values: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.expiry: dict[str, int] = {}
        self.pipeline_transactions: list[bool] = []
        self._fail_execute = fail_execute

    def pipeline(self, transaction: bool = True) -> FakePipeline:
        self.pipeline_transactions.append(transaction)
        return FakePipeline(self, should_fail=self._fail_execute)

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        items = self.lists.get(key, [])
        if not items:
            return []
        if end == -1:
            return items[start:]
        return items[start : end + 1]


def test_append_message_is_atomic_and_uses_transaction() -> None:
    redis_client = FakeRedis()
    store = RedisChatStore(
        redis_client,
        key_prefix="test-chat",
        session_ttl_seconds=300,
        message_ttl_seconds=600,
    )

    message = store.append_message(
        "session-1",
        {"role": "user", "content": "hello"},
        {"title": "Test Session"},
    )

    assert message["content"] == "hello"
    assert redis_client.pipeline_transactions == [True]

    session_data = json.loads(redis_client.values["test-chat:sessions:session-1"])
    assert session_data["id"] == "session-1"
    assert session_data["title"] == "Test Session"
    assert session_data["status"] == "active"
    assert session_data["updated_at"]

    messages = [
        json.loads(value)
        for value in redis_client.lists["test-chat:messages:session-1"]
    ]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert redis_client.expiry["test-chat:sessions:session-1"] == 300
    assert redis_client.expiry["test-chat:messages:session-1"] == 600


def test_append_message_transaction_failure_has_no_partial_writes() -> None:
    redis_client = FakeRedis(fail_execute=True)
    store = RedisChatStore(redis_client, key_prefix="fail-chat")

    with pytest.raises(RuntimeError, match="simulated transaction failure"):
        store.append_message("session-2", {"role": "user", "content": "boom"})

    assert redis_client.values == {}
    assert redis_client.lists == {}
    assert redis_client.expiry == {}


def test_append_event_is_atomic_and_uses_transaction() -> None:
    redis_client = FakeRedis()
    store = RedisChatStore(
        redis_client,
        key_prefix="event-chat",
        session_ttl_seconds=120,
        event_ttl_seconds=240,
    )

    event = store.append_event(
        "session-ev-1",
        {"type": "tool", "payload": {"name": "search", "status": "ok"}},
        {"status": "running"},
    )

    assert event["type"] == "tool"
    assert redis_client.pipeline_transactions == [True]

    session_data = json.loads(redis_client.values["event-chat:sessions:session-ev-1"])
    assert session_data["status"] == "running"

    events = [
        json.loads(value)
        for value in redis_client.lists["event-chat:events:session-ev-1"]
    ]
    assert len(events) == 1
    assert events[0]["payload"]["name"] == "search"
    assert redis_client.expiry["event-chat:sessions:session-ev-1"] == 120
    assert redis_client.expiry["event-chat:events:session-ev-1"] == 240


def test_append_event_transaction_failure_has_no_partial_writes() -> None:
    redis_client = FakeRedis(fail_execute=True)
    store = RedisChatStore(redis_client, key_prefix="fail-event-chat")

    with pytest.raises(RuntimeError, match="simulated transaction failure"):
        store.append_event("session-ev-2", {"type": "system"})

    assert redis_client.values == {}
    assert redis_client.lists == {}
    assert redis_client.expiry == {}


def test_get_session_and_messages_round_trip() -> None:
    redis_client = FakeRedis()
    store = RedisChatStore(redis_client, key_prefix="roundtrip")

    store.append_message("session-3", {"role": "user", "content": "first"})
    store.append_message(
        "session-3",
        {"role": "assistant", "content": "second", "metadata": {"source": "model"}},
        {"status": "running"},
    )

    session = store.get_session("session-3")
    assert session is not None
    assert session["status"] == "running"
    assert session["id"] == "session-3"

    messages = store.get_messages("session-3")
    assert [msg["content"] for msg in messages] == ["first", "second"]
    assert messages[1]["metadata"]["source"] == "model"

    first_only = store.get_messages("session-3", limit=1)
    assert len(first_only) == 1
    assert first_only[0]["content"] == "first"


def test_get_events_round_trip() -> None:
    redis_client = FakeRedis()
    store = RedisChatStore(redis_client, key_prefix="event-roundtrip")

    store.append_event(
        "session-ev-3",
        {"type": "system", "payload": {"phase": "start"}},
    )
    store.append_event(
        "session-ev-3",
        {"type": "result", "payload": {"status": "done"}},
    )

    events = store.get_events("session-ev-3")
    assert [event["type"] for event in events] == ["system", "result"]
    assert events[1]["payload"]["status"] == "done"

    first_only = store.get_events("session-ev-3", limit=1)
    assert len(first_only) == 1
    assert first_only[0]["type"] == "system"


def test_message_schema_defaults_required_fields() -> None:
    schema = MessageSchema.from_mapping(
        {"content": "hello"}, "2026-02-24T00:00:00+00:00"
    )

    assert schema.to_dict() == {
        "role": "user",
        "content": "hello",
        "timestamp": "2026-02-24T00:00:00+00:00",
        "type": "message",
        "metadata": {},
    }


def test_event_schema_defaults_required_fields() -> None:
    schema = EventSchema.from_mapping({}, "2026-02-24T00:00:00+00:00")

    assert schema.to_dict() == {
        "type": "system",
        "payload": {},
        "timestamp": "2026-02-24T00:00:00+00:00",
    }


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ({"role": ""}, "message.role"),
        ({"content": 123}, "message.content"),
        ({"timestamp": ""}, "message.timestamp"),
        ({"type": ""}, "message.type"),
        ({"metadata": "not-a-dict"}, "message.metadata"),
    ],
)
def test_message_schema_rejects_invalid_fields(
    payload: dict[str, Any], error: str
) -> None:
    with pytest.raises(ValueError, match=error):
        MessageSchema.from_mapping(payload, "2026-02-24T00:00:00+00:00")


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ({"type": ""}, "event.type"),
        ({"type": "unknown"}, "event.type"),
        ({"payload": "not-an-object"}, "event.payload"),
        ({"timestamp": ""}, "event.timestamp"),
    ],
)
def test_event_schema_rejects_invalid_fields(
    payload: dict[str, Any], error: str
) -> None:
    with pytest.raises(ValueError, match=error):
        EventSchema.from_mapping(payload, "2026-02-24T00:00:00+00:00")
