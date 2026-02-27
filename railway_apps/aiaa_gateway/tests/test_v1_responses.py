"""Tests for POST /v1/responses stream and non-stream modes."""

from __future__ import annotations

import json
import logging
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


@pytest.fixture(autouse=True)
def _set_required_encryption_key(monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "gateway-startup-test-key")


class FakeStreamResponse(FakeResponse):
    """Fake streaming response exposing iter_lines and close."""

    def __init__(
        self,
        status_code: int,
        lines: list[str],
        *,
        body: dict[str, Any] | list[Any] | None = None,
        text: str = "",
    ):
        super().__init__(status_code, body or {}, text=text)
        self._lines = lines
        self.closed = False

    def iter_lines(self, decode_unicode: bool = False):
        del decode_unicode
        yield from self._lines

    def close(self):
        self.closed = True


def _make_client(*, internal_token: str = "internal-gateway-token"):
    app = create_app(
        {
            "TESTING": True,
            "GATEWAY_INTERNAL_TOKEN": internal_token,
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


def _auth_headers(token: str = "internal-gateway-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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
        headers=_auth_headers(),
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
        headers={
            **_auth_headers(),
            routes.CORRELATION_HEADER: "corr-123",
        },
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
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    correlation_id = response.headers.get(routes.CORRELATION_HEADER)
    assert correlation_id
    assert len(correlation_id) == 32
    assert captured["headers"][routes.CORRELATION_HEADER] == correlation_id
    assert captured["headers"][routes.REQUEST_ID_HEADER] == correlation_id


def test_post_v1_responses_stream_success(monkeypatch):
    client = _make_client()
    captured: dict[str, Any] = {}
    stream_response = FakeStreamResponse(
        200,
        [
            "event: message_start",
            'data: {"type":"message_start","message":{"model":"claude-3-5-sonnet-latest","usage":{"input_tokens":7}}}',
            "",
            "event: content_block_start",
            'data: {"type":"content_block_start","content_block":{"type":"text","text":"Hello "}}',
            "",
            "event: content_block_delta",
            'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"world"}}',
            "",
            "event: message_delta",
            'data: {"type":"message_delta","usage":{"output_tokens":2}}',
            "",
            "event: message_stop",
            'data: {"type":"message_stop"}',
            "",
        ],
    )

    def fake_post(
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
        stream: bool,
    ):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        captured["stream"] = stream
        return stream_response

    monkeypatch.setattr(routes.http_requests, "post", fake_post)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello", "stream": True},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"

    data_chunks: list[str] = []
    for line in response.get_data(as_text=True).splitlines():
        if line.startswith("data: "):
            data_chunks.append(line[6:])

    assert data_chunks[-1] == "[DONE]"
    typed_events = [json.loads(item) for item in data_chunks if item != "[DONE]"]
    assert typed_events[0]["type"] == "response.created"
    assert typed_events[-1]["type"] == "response.completed"
    assert [
        event["delta"]
        for event in typed_events
        if event.get("type") == "response.output_text.delta"
    ] == ["Hello ", "world"]
    assert any(
        event.get("type") == "response.output_text.done"
        and event.get("text") == "Hello world"
        for event in typed_events
    )
    completed = typed_events[-1]["response"]
    assert completed["usage"]["input_tokens"] == 7
    assert completed["usage"]["output_tokens"] == 2
    assert completed["output"][0]["content"][0]["text"] == "Hello world"

    assert stream_response.closed is True
    assert captured["url"].endswith("/v1/messages")
    assert captured["json"]["stream"] is True
    assert captured["headers"]["accept"] == "text/event-stream"
    assert captured["stream"] is True


def test_post_v1_responses_stream_emits_failed_terminal_event(monkeypatch):
    client = _make_client()
    stream_response = FakeStreamResponse(
        200,
        [
            "event: message_start",
            'data: {"type":"message_start","message":{"model":"claude-3-5-sonnet-latest"}}',
            "",
            "event: error",
            'data: {"type":"error","error":{"message":"provider stream error"}}',
            "",
        ],
    )

    def fake_post(
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
        stream: bool,
    ):
        del url, json, headers, timeout, stream
        return stream_response

    monkeypatch.setattr(routes.http_requests, "post", fake_post)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello", "stream": True},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    chunks = [
        line[6:]
        for line in response.get_data(as_text=True).splitlines()
        if line.startswith("data: ")
    ]
    assert chunks[-1] == "[DONE]"

    typed_events = [json.loads(item) for item in chunks if item != "[DONE]"]
    assert typed_events[0]["type"] == "response.created"
    assert typed_events[-1]["type"] == "response.failed"
    assert "provider stream error" in typed_events[-1]["response"]["error"]["message"]
    assert stream_response.closed is True


def test_post_v1_responses_stream_surfaces_upstream_http_errors(monkeypatch):
    client = _make_client()
    captured: dict[str, Any] = {}

    def fake_post(
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
        stream: bool,
    ):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        captured["stream"] = stream
        return FakeStreamResponse(
            429,
            [],
            body={"error": {"message": "rate limit exceeded"}},
            text="rate limited",
        )

    monkeypatch.setattr(routes.http_requests, "post", fake_post)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello", "stream": True},
        headers=_auth_headers(),
    )

    assert response.status_code == 502
    body = response.get_json()
    assert body["error"]["type"] == "upstream_error"
    assert body["error"]["details"]["upstream_status"] == 429
    assert captured["headers"]["accept"] == "text/event-stream"
    assert captured["stream"] is True


def test_post_v1_responses_handles_normalized_upstream_payload(monkeypatch):
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
        headers=_auth_headers(),
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

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest"},
        headers=_auth_headers(),
    )

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
        headers=_auth_headers(),
    )

    assert response.status_code == 502
    body = response.get_json()
    assert body["error"]["type"] == "upstream_error"
    assert body["error"]["details"]["upstream_status"] == 429

def test_post_v1_responses_redacts_token_from_request_exceptions(monkeypatch, caplog):
    client = _make_client()
    raw_token = "sk-ant-api03-super-secret-token-1234567890"
    leaked_message = f"Authorization: Bearer {raw_token}"

    def fake_post(
        url: str, *, json: dict[str, Any], headers: dict[str, str], timeout: float
    ):
        del url, json, headers, timeout
        raise routes.http_requests.RequestException(leaked_message)

    monkeypatch.setattr(routes.http_requests, "post", fake_post)

    with caplog.at_level("ERROR"):
        response = client.post(
            "/v1/responses",
            json={"model": "claude-3-5-sonnet-latest", "input": "hello"},
            headers=_auth_headers(),
        )

    assert response.status_code == 502
    body = response.get_json()
    assert body["error"]["type"] == "upstream_error"
    assert raw_token not in body["error"]["message"]
    assert "Bearer " in body["error"]["message"]

    assert raw_token not in caplog.text
    assert "Bearer " in caplog.text


def test_post_v1_responses_forwards_gateway_request_fields(monkeypatch):
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
                "id": "msg_upstream_789",
                "model": "claude-3-5-sonnet-latest",
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "stop_reason": "end_turn",
            },
        )

    monkeypatch.setattr(routes.http_requests, "post", fake_post)

    response = client.post(
        "/v1/responses",
        json={
            "model": "claude-3-5-sonnet-latest",
            "input": "hello",
            "profile_id": "student-a",
            "session_id": "session-123",
            "cwd": "/workspace/project",
            "tools_profile": "safe",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    headers = captured["headers"]
    assert headers["x-aiaa-profile-id"] == "student-a"
    assert headers["x-aiaa-session-id"] == "session-123"
    assert headers["x-aiaa-cwd"] == "/workspace/project"
    assert headers["x-aiaa-tools-profile"] == "safe"


def test_post_v1_responses_applies_gateway_field_defaults(monkeypatch):
    client = _make_client()
    captured: dict[str, Any] = {}

    def fake_post(
        url: str, *, json: dict[str, Any], headers: dict[str, str], timeout: float
    ):
        del url, json, timeout
        captured["headers"] = headers
        return FakeResponse(
            200,
            {
                "id": "msg_upstream_790",
                "model": "claude-3-5-sonnet-latest",
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "stop_reason": "end_turn",
            },
        )

    monkeypatch.setattr(routes.http_requests, "post", fake_post)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    headers = captured["headers"]
    assert headers["x-aiaa-cwd"] == "/app"
    assert headers["x-aiaa-tools-profile"] == "full"
    assert "x-aiaa-profile-id" not in headers
    assert "x-aiaa-session-id" not in headers


def test_post_v1_responses_rejects_non_string_gateway_fields():
    client = _make_client()

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello", "cwd": 123},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["type"] == "invalid_request_error"
    assert body["error"]["message"] == "cwd must be a string when provided."


def test_post_v1_responses_requires_internal_bearer_token(monkeypatch):
    client = _make_client()

    def fail_if_called(*args, **kwargs):  # pragma: no cover - safety guard
        raise AssertionError("Upstream call should not happen without bearer auth")

    monkeypatch.setattr(routes.http_requests, "post", fail_if_called)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello"},
    )

    assert response.status_code == 401
    body = response.get_json()
    assert body["error"]["type"] == "authentication_error"
    assert body["error"]["message"] == "Missing internal bearer token."


def test_post_v1_responses_rejects_invalid_internal_bearer_token(monkeypatch):
    client = _make_client()

    def fail_if_called(*args, **kwargs):  # pragma: no cover - safety guard
        raise AssertionError("Upstream call should not happen with invalid bearer auth")

    monkeypatch.setattr(routes.http_requests, "post", fail_if_called)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello"},
        headers=_auth_headers("wrong-token"),
    )

    assert response.status_code == 401
    body = response.get_json()
    assert body["error"]["type"] == "authentication_error"
    assert body["error"]["message"] == "Invalid internal bearer token."


def test_post_v1_responses_requires_internal_token_configuration(monkeypatch):
    client = _make_client(internal_token="")

    def fail_if_called(*args, **kwargs):  # pragma: no cover - safety guard
        raise AssertionError("Upstream call should not happen without auth config")

    monkeypatch.setattr(routes.http_requests, "post", fail_if_called)

    response = client.post(
        "/v1/responses",
        json={"model": "claude-3-5-sonnet-latest", "input": "hello"},
        headers=_auth_headers(),
    )

    assert response.status_code == 503
    body = response.get_json()
    assert body["error"]["type"] == "configuration_error"
    assert body["error"]["message"] == "Gateway internal bearer token is not configured."
