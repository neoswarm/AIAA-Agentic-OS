"""
Chat storage backends for dashboard chat sessions, messages, and events.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


def _utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp string."""
    return datetime.now(tz=timezone.utc).isoformat()


ALLOWED_STREAM_EVENT_TYPES = {"tool", "system", "result"}


@dataclass(frozen=True)
class MessageSchema:
    """Normalized chat message schema."""

    role: str
    content: str
    timestamp: str
    type: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, message: Mapping[str, Any], now: str) -> "MessageSchema":
        """Build and validate a message from arbitrary mapping input."""
        role = message.get("role", "user")
        content = message.get("content", "")
        timestamp = message.get("timestamp", now)
        message_type = message.get("type", "message")
        metadata = message.get("metadata")

        if not isinstance(role, str) or not role.strip():
            raise ValueError("message.role must be a non-empty string")
        if not isinstance(content, str):
            raise ValueError("message.content must be a string")
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError("message.timestamp must be a non-empty string")
        if not isinstance(message_type, str) or not message_type.strip():
            raise ValueError("message.type must be a non-empty string")

        if metadata is None:
            metadata_dict: dict[str, Any] = {}
        elif isinstance(metadata, Mapping):
            metadata_dict = dict(metadata)
        else:
            raise ValueError("message.metadata must be an object")

        return cls(
            role=role,
            content=content,
            timestamp=timestamp,
            type=message_type,
            metadata=metadata_dict,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize schema to a plain dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "type": self.type,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class EventSchema:
    """Normalized streamed tool/system/result event schema."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    @classmethod
    def from_mapping(cls, event: Mapping[str, Any], now: str) -> "EventSchema":
        """Build and validate an event from arbitrary mapping input."""
        event_type = event.get("type", "system")
        payload = event.get("payload")
        timestamp = event.get("timestamp", now)

        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event.type must be a non-empty string")
        if event_type not in ALLOWED_STREAM_EVENT_TYPES:
            raise ValueError("event.type must be one of: tool, system, result")
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError("event.timestamp must be a non-empty string")

        if payload is None:
            payload_dict: dict[str, Any] = {}
        elif isinstance(payload, Mapping):
            payload_dict = dict(payload)
        else:
            raise ValueError("event.payload must be an object")

        return cls(type=event_type, payload=payload_dict, timestamp=timestamp)

    def to_dict(self) -> dict[str, Any]:
        """Serialize schema to a plain dictionary."""
        return {
            "type": self.type,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


class ChatStore(ABC):
    """Interface for chat session/message/event storage backends."""

    @abstractmethod
    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a session by id."""

    @abstractmethod
    def append_message(
        self,
        session_id: str,
        message: Mapping[str, Any],
        session_updates: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Append a message and persist session metadata in the same write operation.
        """

    @abstractmethod
    def get_messages(
        self, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get messages for a session."""

    @abstractmethod
    def append_event(
        self,
        session_id: str,
        event: Mapping[str, Any],
        session_updates: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Append an event and persist session metadata in the same write operation.
        """

    @abstractmethod
    def get_events(
        self, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get stream events for a session."""


class RedisChatStore(ChatStore):
    """
    Redis-backed chat store.

    Session writes and message appends are grouped in a Redis MULTI/EXEC
    transaction so both records are committed atomically.
    """

    def __init__(
        self,
        redis_client: Any,
        *,
        key_prefix: str = "chat",
        session_ttl_seconds: int | None = None,
        message_ttl_seconds: int | None = None,
        event_ttl_seconds: int | None = None,
    ) -> None:
        self._redis = redis_client
        self._key_prefix = key_prefix.strip(":")
        self._session_ttl_seconds = session_ttl_seconds
        self._message_ttl_seconds = message_ttl_seconds
        self._event_ttl_seconds = event_ttl_seconds

    @classmethod
    def from_url(cls, redis_url: str, **kwargs: Any) -> "RedisChatStore":
        """Create a Redis-backed store from a Redis URL."""
        try:
            from redis import Redis  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "redis package is required to use RedisChatStore.from_url()."
            ) from exc

        client = Redis.from_url(redis_url, decode_responses=True)
        return cls(client, **kwargs)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        raw = self._redis.get(self._session_key(session_id))
        if raw is None:
            return None
        return self._deserialize(raw)

    def append_message(
        self,
        session_id: str,
        message: Mapping[str, Any],
        session_updates: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _utc_now_iso()
        session = self._build_session_record(session_id, now, session_updates)
        message_record = self._build_message_record(message, now)

        session_key = self._session_key(session_id)
        messages_key = self._messages_key(session_id)

        pipe = self._redis.pipeline(transaction=True)
        pipe.set(
            session_key,
            json.dumps(session, separators=(",", ":"), sort_keys=True),
        )
        pipe.rpush(
            messages_key,
            json.dumps(message_record, separators=(",", ":"), sort_keys=True),
        )

        if self._session_ttl_seconds:
            pipe.expire(session_key, self._session_ttl_seconds)
        if self._message_ttl_seconds:
            pipe.expire(messages_key, self._message_ttl_seconds)

        pipe.execute()
        return message_record

    def get_messages(
        self, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        if limit is not None and limit <= 0:
            return []

        end = -1 if limit is None else limit - 1
        raw_items = self._redis.lrange(self._messages_key(session_id), 0, end)
        return [self._deserialize(item) for item in raw_items]

    def append_event(
        self,
        session_id: str,
        event: Mapping[str, Any],
        session_updates: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _utc_now_iso()
        session = self._build_session_record(session_id, now, session_updates)
        event_record = self._build_event_record(event, now)

        session_key = self._session_key(session_id)
        events_key = self._events_key(session_id)

        pipe = self._redis.pipeline(transaction=True)
        pipe.set(
            session_key,
            json.dumps(session, separators=(",", ":"), sort_keys=True),
        )
        pipe.rpush(
            events_key,
            json.dumps(event_record, separators=(",", ":"), sort_keys=True),
        )

        if self._session_ttl_seconds:
            pipe.expire(session_key, self._session_ttl_seconds)
        if self._event_ttl_seconds:
            pipe.expire(events_key, self._event_ttl_seconds)

        pipe.execute()
        return event_record

    def get_events(
        self, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        if limit is not None and limit <= 0:
            return []

        end = -1 if limit is None else limit - 1
        raw_items = self._redis.lrange(self._events_key(session_id), 0, end)
        return [self._deserialize(item) for item in raw_items]

    def _build_session_record(
        self,
        session_id: str,
        now: str,
        session_updates: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        existing = self.get_session(session_id)
        if existing is None:
            session: dict[str, Any] = {
                "id": session_id,
                "title": "New Chat",
                "status": "active",
                "sdk_session_id": None,
                "created_at": now,
            }
        else:
            session = dict(existing)

        if session_updates:
            session.update(session_updates)

        session["id"] = session_id
        session.setdefault("created_at", now)
        session["updated_at"] = now
        return session

    @staticmethod
    def _build_message_record(message: Mapping[str, Any], now: str) -> dict[str, Any]:
        return MessageSchema.from_mapping(message, now).to_dict()

    @staticmethod
    def _build_event_record(event: Mapping[str, Any], now: str) -> dict[str, Any]:
        return EventSchema.from_mapping(event, now).to_dict()

    def _session_key(self, session_id: str) -> str:
        return f"{self._key_prefix}:sessions:{session_id}"

    def _messages_key(self, session_id: str) -> str:
        return f"{self._key_prefix}:messages:{session_id}"

    def _events_key(self, session_id: str) -> str:
        return f"{self._key_prefix}:events:{session_id}"

    @staticmethod
    def _deserialize(raw: Any) -> dict[str, Any]:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)
