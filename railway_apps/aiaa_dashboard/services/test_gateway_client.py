#!/usr/bin/env python3
"""Unit tests for gateway client retry/backoff and typed wrappers."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from typing import Any

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.gateway_client import (
    GatewayClient,
    GatewayClientError,
    GatewayDecodeError,
    GatewayHTTPError,
    RetryConfig,
)


class FakeResponse:
    """Tiny fake response object for request testing."""

    def __init__(
        self,
        status_code: int,
        body: dict[str, Any] | list[Any] | Exception | None = None,
        *,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.text = text

    def json(self) -> dict[str, Any] | list[Any]:
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class FakeSession:
    """Scripted request session for deterministic retry tests."""

    def __init__(self, scripted: list[FakeResponse | Exception]) -> None:
        self._scripted = list(scripted)
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": method, "url": url, "kwargs": kwargs})
        if not self._scripted:
            raise AssertionError("No scripted response left for request")
        item = self._scripted.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_get_json_retries_timeout_and_succeeds() -> None:
    session = FakeSession(
        [
            requests.Timeout("timed out"),
            FakeResponse(200, {"ok": True}),
        ]
    )
    sleeps: list[float] = []
    client = GatewayClient(
        "https://gateway.example",
        retry_config=RetryConfig(max_attempts=3, base_backoff_seconds=0.25),
        session=session,
        sleep=sleeps.append,
    )

    result = client.get_json("/health")

    assert result == {"ok": True}
    assert len(session.calls) == 2
    assert sleeps == [0.25]


def test_post_json_retries_retryable_status_code() -> None:
    session = FakeSession(
        [
            FakeResponse(503, {"error": "busy"}, text="busy"),
            FakeResponse(200, {"queued": True}),
        ]
    )
    sleeps: list[float] = []
    client = GatewayClient(
        "https://gateway.example",
        retry_config=RetryConfig(max_attempts=2, base_backoff_seconds=0.1),
        session=session,
        sleep=sleeps.append,
    )

    result = client.post_json("/jobs", payload={"name": "demo"})

    assert result == {"queued": True}
    assert len(session.calls) == 2
    assert session.calls[0]["kwargs"]["json"] == {"name": "demo"}
    assert sleeps == [0.1]


def test_get_json_raises_http_error_without_retry_for_400() -> None:
    session = FakeSession([FakeResponse(400, {"error": "bad request"}, text="bad")])
    sleeps: list[float] = []
    client = GatewayClient(
        "https://gateway.example",
        retry_config=RetryConfig(max_attempts=3, base_backoff_seconds=0.1),
        session=session,
        sleep=sleeps.append,
    )

    with pytest.raises(GatewayHTTPError) as excinfo:
        client.get_json("/bad-request")

    assert excinfo.value.status_code == 400
    assert len(session.calls) == 1
    assert sleeps == []


def test_request_json_raises_client_error_after_max_retries() -> None:
    session = FakeSession(
        [
            requests.ConnectionError("down-1"),
            requests.ConnectionError("down-2"),
            requests.ConnectionError("down-3"),
        ]
    )
    sleeps: list[float] = []
    client = GatewayClient(
        "https://gateway.example",
        retry_config=RetryConfig(max_attempts=3, base_backoff_seconds=0.2),
        session=session,
        sleep=sleeps.append,
    )

    with pytest.raises(GatewayClientError):
        client.get_json("/health")

    assert len(session.calls) == 3
    assert sleeps == [0.2, 0.4]


def test_get_typed_uses_parser_wrapper() -> None:
    session = FakeSession([FakeResponse(200, {"ok": True, "region": "us-east-1"})])
    client = GatewayClient("https://gateway.example", session=session)

    @dataclasses.dataclass(frozen=True)
    class HealthResponse:
        ok: bool
        region: str

    parsed = client.get_typed(
        "/health",
        parser=lambda body: HealthResponse(
            ok=bool(body["ok"]), region=str(body["region"])
        ),
    )

    assert parsed == HealthResponse(ok=True, region="us-east-1")


def test_get_json_raises_decode_error_for_non_json_response() -> None:
    session = FakeSession(
        [
            FakeResponse(200, ValueError("not json"), text="<html>boom</html>"),
        ]
    )
    client = GatewayClient("https://gateway.example", session=session)

    with pytest.raises(GatewayDecodeError):
        client.get_json("/health")
