"""Tests for POST /v1/responses non-stream mode."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pytest


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


@pytest.fixture(autouse=True)
def _reset_auth_failure_state():
    routes._reset_auth_failure_throttle_state()
    yield
    routes._reset_auth_failure_throttle_state()


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


def test_post_v1_responses_requires_gateway_bearer_when_configured(monkeypatch):
    app = create_app(
        {
            "TESTING": True,
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "GATEWAY_API_KEY": "gateway-secret",
        }
    )
    client = app.test_client()

    def fail_if_called(*args, **kwargs):  # pragma: no cover - safety guard
        raise AssertionError("Upstream call should not happen for missing auth")

    monkeypatch.setattr(routes.http_requests, "post", fail_if_called)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello"},
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    body = response.get_json()
    assert body["error"]["type"] == "authentication_error"
    assert body["error"]["message"] == "Missing gateway bearer token."


def test_post_v1_responses_throttles_repeated_invalid_gateway_bearer_tokens(monkeypatch):
    app = create_app(
        {
            "TESTING": True,
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "GATEWAY_API_KEY": "gateway-secret",
            "GATEWAY_AUTH_FAILURE_MAX_ATTEMPTS": 2,
            "GATEWAY_AUTH_FAILURE_WINDOW_SECONDS": 60,
        }
    )
    client = app.test_client()

    def fail_if_called(*args, **kwargs):  # pragma: no cover - safety guard
        raise AssertionError("Upstream call should not happen for invalid auth")

    monkeypatch.setattr(routes.http_requests, "post", fail_if_called)

    headers = {"Authorization": "Bearer wrong-token"}
    payload = {"model": "claude-3-5-sonnet-latest", "input": "hello"}

    first = client.post("/v1/responses", headers=headers, json=payload)
    assert first.status_code == 401

    second = client.post("/v1/responses", headers=headers, json=payload)
    assert second.status_code == 429
    assert second.headers["Retry-After"]
    body = second.get_json()
    assert body["error"]["type"] == "rate_limit_error"
    assert body["error"]["details"]["limit"] == 2
    assert body["error"]["details"]["window_seconds"] == 60
    assert body["error"]["details"]["retry_after_seconds"] >= 1


def test_post_v1_responses_gateway_bearer_auth_uses_configured_anthropic_key(monkeypatch):
    app = create_app(
        {
            "TESTING": True,
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "GATEWAY_API_KEY": "gateway-secret",
            "DEFAULT_MAX_OUTPUT_TOKENS": 256,
            "UPSTREAM_REQUEST_TIMEOUT_SECONDS": 5,
        }
    )
    client = app.test_client()
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
        headers={"Authorization": "Bearer gateway-secret"},
        json={"model": "claude-3-5-sonnet-latest", "input": "hello"},
    )

    assert response.status_code == 200
    assert captured["url"].endswith("/v1/messages")
    assert captured["headers"]["x-api-key"] == "test-anthropic-key"
