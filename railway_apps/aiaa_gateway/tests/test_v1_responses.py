"""Tests for POST /v1/responses non-stream mode."""

from __future__ import annotations

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


def test_post_v1_responses_handles_normalized_upstream_payload(monkeypatch):
    client = _make_client()

    def fake_post(
        url: str, *, json: dict[str, Any], headers: dict[str, str], timeout: float
    ):
        del url, json, headers, timeout
        return FakeResponse(
            200,
            {
                "id": "resp_normalized_123",
                "object": "response",
                "created_at": 1730000000,
                "status": "completed",
                "model": "claude-3-5-sonnet-latest",
                "output": [
                    {
                        "id": "msg_normalized_1",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "Hello from normalized payload",
                                "annotations": [],
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 11, "output_tokens": 6, "total_tokens": 17},
            },
        )

    monkeypatch.setattr(routes.http_requests, "post", fake_post)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == "resp_normalized_123"
    assert body["created_at"] == 1730000000
    assert body["status"] == "completed"
    assert body["output_text"] == "Hello from normalized payload"
    assert body["output"][0]["id"] == "msg_normalized_1"
    assert body["usage"] == {"input_tokens": 11, "output_tokens": 6, "total_tokens": 17}


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
