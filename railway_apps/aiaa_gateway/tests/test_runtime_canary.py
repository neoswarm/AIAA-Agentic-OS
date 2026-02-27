"""Tests for setup-token runtime canary OAuth behavior."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aiaa_gateway.services import runtime_canary


class _FakeResponse:
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> Any:
        return self._payload


def test_setup_token_canary_uses_oauth_headers(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_post(url: str, *, json: dict[str, Any], headers: dict[str, str], timeout: float):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _FakeResponse(
            200,
            {"content": [{"type": "text", "text": "OK"}]},
        )

    monkeypatch.setattr(runtime_canary.http_requests, "post", fake_post)

    result = runtime_canary.run_gateway_runtime_canary(
        "sk-ant-oat01-example-token",
        timeout_seconds=7,
    )

    assert result["status"] == "valid"
    assert "OAuth canary succeeded" in result["message"]
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["authorization"] == "Bearer sk-ant-oat01-example-token"
    assert "oauth-2025-04-20" in captured["headers"]["anthropic-beta"]
    assert captured["json"]["model"] == "claude-sonnet-4-6"


def test_setup_token_canary_maps_non_200_to_invalid(monkeypatch):
    def fake_post(url: str, *, json: dict[str, Any], headers: dict[str, str], timeout: float):
        del url, json, headers, timeout
        return _FakeResponse(
            401,
            {"error": {"type": "authentication_error", "message": "bad token"}},
        )

    monkeypatch.setattr(runtime_canary.http_requests, "post", fake_post)

    result = runtime_canary.run_gateway_runtime_canary(
        "sk-ant-oat01-bad-token",
        timeout_seconds=5,
    )

    assert result["status"] == "invalid"
    assert "OAuth canary failed" in result["message"]
    assert "authentication_error" in result["error"]
