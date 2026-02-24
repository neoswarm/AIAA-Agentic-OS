import importlib
import sys
from pathlib import Path

import pytest


MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

webhooks_app = importlib.import_module("app")


class MockResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def clear_events():
    with webhooks_app.events_lock:
        webhooks_app.events_log.clear()


@pytest.fixture
def client():
    with webhooks_app.app.test_client() as test_client:
        yield test_client


def test_health_generates_correlation_id(client):
    response = client.get("/health")
    response_data = response.get_json()
    header_id = response.headers.get(webhooks_app.CORRELATION_HEADER)

    assert header_id
    assert response_data["correlation_id"] == header_id


def test_health_preserves_incoming_correlation_id(client):
    incoming_id = "req-123"
    response = client.get("/health", headers={webhooks_app.CORRELATION_HEADER: incoming_id})
    response_data = response.get_json()

    assert response.headers.get(webhooks_app.CORRELATION_HEADER) == incoming_id
    assert response_data["correlation_id"] == incoming_id


def test_webhook_error_response_and_event_include_correlation_id(client):
    response = client.post("/webhook/calendly", json={})
    response_data = response.get_json()
    header_id = response.headers.get(webhooks_app.CORRELATION_HEADER)

    assert response.status_code == 400
    assert response_data["correlation_id"] == header_id

    events_response = client.get("/api/events")
    events = events_response.get_json()
    assert events[0]["correlation_id"] == header_id


def test_perplexity_request_includes_correlation_id(monkeypatch):
    captured_headers = {}

    def mock_post(_url, headers=None, **_kwargs):
        captured_headers.update(headers or {})
        return MockResponse(200, {"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(webhooks_app, "PERPLEXITY_API_KEY", "test-key")
    monkeypatch.setattr(webhooks_app.requests, "post", mock_post)

    result = webhooks_app.research_with_perplexity("hello", correlation_id="corr-1")
    assert result == "ok"
    assert captured_headers[webhooks_app.CORRELATION_HEADER] == "corr-1"


def test_openrouter_request_includes_correlation_id(monkeypatch):
    captured_headers = {}

    def mock_post(_url, headers=None, **_kwargs):
        captured_headers.update(headers or {})
        return MockResponse(200, {"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(webhooks_app, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(webhooks_app.requests, "post", mock_post)

    result = webhooks_app.research_with_claude("hello", correlation_id="corr-2")
    assert result == "ok"
    assert captured_headers[webhooks_app.CORRELATION_HEADER] == "corr-2"
