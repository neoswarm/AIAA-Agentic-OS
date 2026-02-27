"""Tests for POST /v1/responses non-stream mode."""

from __future__ import annotations

import json
import logging
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
        self, status_code: int, body: dict[str, Any] | list[Any], *, text: str = ""
    ):
        self.status_code = status_code
        self._body = body
        self.text = text

    def json(self) -> dict[str, Any] | list[Any]:
        return self._body


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


def _gateway_log_payloads(caplog, event_name: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for record in caplog.records:
        try:
            payload = json.loads(record.getMessage())
        except (TypeError, json.JSONDecodeError):
            continue
        if payload.get("event") == event_name:
            payloads.append(payload)
    return payloads


def test_post_v1_responses_non_stream_success(monkeypatch):
    client = _make_client()
    captured: dict[str, Any] = {}

    def fake_post(
        url: str, *, json: dict[str, Any], headers: dict[str, str], timeout: float
    ):
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


def test_post_v1_responses_propagates_correlation_id_and_logs(
    monkeypatch, caplog
):
    client = _make_client()
    captured: dict[str, Any] = {}

    def fake_post(
        url: str, *, json: dict[str, Any], headers: dict[str, str], timeout: float
    ):
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
    caplog.set_level(logging.INFO, logger="aiaa_gateway.routes")
    caplog.clear()

    response = client.post(
        "/v1/responses",
        json={
            "model": "claude-3-5-sonnet-latest",
            "input": "Say hello",
            "stream": False,
        },
        headers={routes.CORRELATION_HEADER: "corr-123"},
    )

    assert response.status_code == 200
    assert response.headers.get(routes.CORRELATION_HEADER) == "corr-123"
    assert captured["headers"][routes.CORRELATION_HEADER] == "corr-123"
    assert captured["headers"][routes.REQUEST_ID_HEADER] == "corr-123"

    payloads = _gateway_log_payloads(caplog, "gateway.responses")
    assert any(
        payload.get("status") == "received"
        and payload.get("correlation_id") == "corr-123"
        and payload.get("path") == "/v1/responses"
        for payload in payloads
    )
    assert any(
        payload.get("status") == "success"
        and payload.get("correlation_id") == "corr-123"
        for payload in payloads
    )


def test_post_v1_responses_generates_correlation_id_when_missing(monkeypatch):
    client = _make_client()
    captured: dict[str, Any] = {}

    def fake_post(
        url: str, *, json: dict[str, Any], headers: dict[str, str], timeout: float
    ):
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
            "input": "Say hello",
            "stream": False,
        },
    )

    assert response.status_code == 200
    correlation_id = response.headers.get(routes.CORRELATION_HEADER)
    assert correlation_id
    assert len(correlation_id) == 32
    assert captured["headers"][routes.CORRELATION_HEADER] == correlation_id
    assert captured["headers"][routes.REQUEST_ID_HEADER] == correlation_id


def test_post_v1_responses_rejects_stream_true(monkeypatch):
    client = _make_client()

    def fail_if_called(*args, **kwargs):  # pragma: no cover - safety guard
        raise AssertionError("Upstream call should not happen when stream=true")

    monkeypatch.setattr(routes.http_requests, "post", fail_if_called)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello", "stream": True},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["type"] == "invalid_request_error"
    assert "non-stream mode" in body["error"]["message"]


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
        url: str, *, json: dict[str, Any], headers: dict[str, str], timeout: float
    ):
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
