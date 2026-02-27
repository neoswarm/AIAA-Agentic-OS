"""Tests for POST /v1/responses compatibility modes."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aiaa_gateway import create_app
from aiaa_gateway import routes


class FakeResponse:
    """Small fake HTTP response for route tests."""

    def __init__(
        self,
        status_code: int,
        body: dict[str, Any] | list[Any],
        *,
        text: str = "",
        stream_lines: list[str] | None = None,
    ):
        self.status_code = status_code
        self._body = body
        self.text = text
        self._stream_lines = stream_lines or []

    def json(self) -> dict[str, Any] | list[Any]:
        return self._body

    def iter_lines(self, decode_unicode: bool = False):
        for line in self._stream_lines:
            if decode_unicode:
                yield line
            else:
                yield line.encode("utf-8")

    def close(self) -> None:
        return None


def _make_client():
    app = create_app(
        {
            "TESTING": True,
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "DEFAULT_ANTHROPIC_MODEL": "claude-3-5-sonnet-latest",
            "DEFAULT_MAX_OUTPUT_TOKENS": 256,
            "UPSTREAM_REQUEST_TIMEOUT_SECONDS": 5,
        }
    )
    return app.test_client()


def test_post_v1_responses_non_stream_success(monkeypatch):
    client = _make_client()
    captured: dict[str, Any] = {}

    def fake_post(
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
        stream: bool = False,
    ):
        assert stream is False
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse(
            200,
            {
                "id": "msg_upstream_123",
                "model": "claude-3-5-sonnet-latest",
                "content": [{"type": "text", "text": "Hello from Anthropic"}],
                "usage": {"input_tokens": 9, "output_tokens": 4},
                "stop_reason": "end_turn",
            },
        )

    monkeypatch.setattr(routes.http_requests, "post", fake_post)

    response = client.post(
        "/v1/responses",
        json={
            "model": "claude-3-5-sonnet-latest",
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Say hello"}],
                }
            ],
            "stream": False,
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["object"] == "response"
    assert body["status"] == "completed"
    assert body["model"] == "claude-3-5-sonnet-latest"
    assert body["output_text"] == "Hello from Anthropic"
    assert body["output"][0]["role"] == "assistant"
    assert body["output"][0]["content"][0]["type"] == "output_text"
    assert body["usage"]["input_tokens"] == 9
    assert body["usage"]["output_tokens"] == 4

    assert captured["url"].endswith("/v1/messages")
    assert captured["json"]["messages"] == [{"role": "user", "content": "Say hello"}]
    assert captured["json"]["max_tokens"] == 256
    assert captured["headers"]["x-api-key"] == "test-anthropic-key"


def test_post_v1_responses_stream_emits_sse_chunks_and_done(monkeypatch):
    client = _make_client()
    captured: dict[str, Any] = {}

    def fake_post(
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
        stream: bool = False,
    ):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        captured["stream"] = stream
        return FakeResponse(
            200,
            {},
            stream_lines=[
                'event: message_start',
                'data: {"type":"message_start"}',
                "",
                'event: content_block_delta',
                (
                    'data: {"type":"content_block_delta","delta":{"type":"text_delta",'
                    '"text":"Hello "}}'
                ),
                "",
                'event: content_block_delta',
                (
                    'data: {"type":"content_block_delta","delta":{"type":"text_delta",'
                    '"text":"world"}}'
                ),
                "",
                'event: message_stop',
                'data: {"type":"message_stop"}',
                "",
            ],
        )

    monkeypatch.setattr(routes.http_requests, "post", fake_post)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello", "stream": True},
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"

    chunks: list[str] = []
    typed_events: list[dict[str, Any]] = []
    for line in response.get_data(as_text=True).splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        chunks.append(payload)
        if payload == "[DONE]":
            continue
        typed_events.append(json.loads(payload))

    assert chunks[-1] == "[DONE]"
    assert typed_events[0]["type"] == "response.created"
    assert typed_events[-1]["type"] == "response.completed"
    assert any(
        event.get("type") == "response.output_text.delta"
        and event.get("delta") == "Hello "
        for event in typed_events
    )
    assert any(
        event.get("type") == "response.output_text.delta"
        and event.get("delta") == "world"
        for event in typed_events
    )
    assert any(
        event.get("type") == "response.output_text.done"
        and event.get("text") == "Hello world"
        for event in typed_events
    )
    assert captured["url"].endswith("/v1/messages")
    assert captured["json"]["stream"] is True
    assert captured["headers"]["accept"] == "text/event-stream"
    assert captured["stream"] is True


def test_post_v1_responses_requires_input():
    client = _make_client()

    response = client.post("/v1/responses", json={"model": "claude-3-5-sonnet-latest"})

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["type"] == "invalid_request_error"
    assert body["error"]["message"] == "input is required."


def test_post_v1_responses_surfaces_upstream_errors(monkeypatch):
    client = _make_client()

    def fake_post(
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
        stream: bool = False,
    ):
        assert stream is False
        del url, json, headers, timeout
        return FakeResponse(
            429, {"error": {"message": "rate limit exceeded"}}, text="rate limited"
        )

    monkeypatch.setattr(routes.http_requests, "post", fake_post)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello"},
    )

    assert response.status_code == 502
    body = response.get_json()
    assert body["error"]["type"] == "upstream_error"
    assert body["error"]["details"]["upstream_status"] == 429


def test_post_v1_responses_stream_emits_failed_and_done_for_error_event(monkeypatch):
    client = _make_client()

    def fake_post(
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
        stream: bool = False,
    ):
        del url, json, headers, timeout
        assert stream is True
        return FakeResponse(
            200,
            {},
            stream_lines=[
                'event: error',
                'data: {"type":"error","error":{"message":"upstream exploded"}}',
                "",
            ],
        )

    monkeypatch.setattr(routes.http_requests, "post", fake_post)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello", "stream": True},
    )

    assert response.status_code == 200
    chunks = [
        line[6:]
        for line in response.get_data(as_text=True).splitlines()
        if line.startswith("data: ")
    ]
    assert chunks[-1] == "[DONE]"

    typed_events = [json.loads(chunk) for chunk in chunks if chunk != "[DONE]"]
    assert typed_events[0]["type"] == "response.created"
    assert typed_events[1]["type"] == "response.failed"
    assert "upstream exploded" in typed_events[1]["response"]["error"]["message"]
