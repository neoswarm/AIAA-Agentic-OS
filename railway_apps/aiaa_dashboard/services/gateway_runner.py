"""
Gateway-backed chat runner implementing the existing runner interface contract.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Generator

from services.agent_runner import AgentRunner, RunnerError

__all__ = ["GatewayRunner", "RunnerError"]


class GatewayRunner(AgentRunner):
    """Drop-in runner implementation for gateway-based chat execution."""

    _CHUNK_ID_FIELDS = ("chunk_id", "delta_id", "event_id", "id")
    _CHUNK_SEQUENCE_FIELDS = ("chunk_index", "delta_index", "sequence", "seq", "index")

    def get_stream(
        self, session_id: str, keepalive_seconds: int = 20
    ) -> Generator[str, None, None]:
        """
        Filter reconnect replay artifacts for gateway text streams.

        Gateway reconnects may replay already-delivered chunks or emit delayed
        chunks out of order. When chunk identifiers or sequence metadata are
        present, suppress duplicates and stale chunks.
        """
        seen_chunk_ids: Dict[str, set[str]] = {"text": set(), "result": set()}
        highest_sequence: Dict[str, int] = {}

        for raw_chunk in super().get_stream(
            session_id, keepalive_seconds=keepalive_seconds
        ):
            event = self._parse_sse_payload(raw_chunk)
            if not event:
                yield raw_chunk
                continue

            event_type = str(event.get("type") or "").strip().lower()
            if event_type not in seen_chunk_ids:
                yield raw_chunk
                continue

            chunk_id = self._extract_chunk_id(event)
            if chunk_id:
                known_ids = seen_chunk_ids[event_type]
                if chunk_id in known_ids:
                    continue
                known_ids.add(chunk_id)

            chunk_sequence = self._extract_chunk_sequence(event)
            if chunk_sequence is not None:
                latest = highest_sequence.get(event_type)
                if latest is not None and chunk_sequence <= latest:
                    continue
                highest_sequence[event_type] = chunk_sequence

            yield raw_chunk

    @staticmethod
    def _parse_sse_payload(raw_chunk: str) -> dict[str, Any] | None:
        for line in (raw_chunk or "").splitlines():
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, dict):
                return parsed
        return None

    @classmethod
    def _extract_chunk_id(cls, event: dict[str, Any]) -> str | None:
        for source in cls._event_metadata_sources(event):
            for key in cls._CHUNK_ID_FIELDS:
                raw_value = source.get(key)
                if raw_value is None:
                    continue
                candidate = str(raw_value).strip()
                if candidate:
                    return candidate
        return None

    @classmethod
    def _extract_chunk_sequence(cls, event: dict[str, Any]) -> int | None:
        for source in cls._event_metadata_sources(event):
            for key in cls._CHUNK_SEQUENCE_FIELDS:
                candidate = cls._coerce_non_negative_int(source.get(key))
                if candidate is not None:
                    return candidate
        return None

    @staticmethod
    def _event_metadata_sources(event: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        sources: list[dict[str, Any]] = [event]
        payload = event.get("payload")
        if isinstance(payload, dict):
            sources.append(payload)
            metadata = payload.get("metadata")
            if isinstance(metadata, dict):
                sources.append(metadata)
        return tuple(sources)

    @staticmethod
    def _coerce_non_negative_int(value: Any) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value if value >= 0 else None
        if isinstance(value, float):
            if value.is_integer() and value >= 0:
                return int(value)
            return None
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                parsed = int(text)
            except ValueError:
                return None
            return parsed if parsed >= 0 else None
        return None
