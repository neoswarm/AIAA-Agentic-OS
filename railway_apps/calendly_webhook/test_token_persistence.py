import importlib.util
import os
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "app.py"
MODULE_SPEC = importlib.util.spec_from_file_location("calendly_webhook_app", MODULE_PATH)
app_module = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(app_module)


class FakeResponse:
    def __init__(self, status_code, body=None, text=""):
        self.status_code = status_code
        self._body = body or {}
        self.text = text

    def json(self):
        return self._body


def test_persist_rotated_token_to_railway_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("RAILWAY_API_TOKEN", "railway-token")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "project-123")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "env-123")
    monkeypatch.setenv("RAILWAY_SERVICE_ID", "service-123")

    attempts = [
        Exception("network timeout"),
        FakeResponse(status_code=500, text="server error"),
        FakeResponse(status_code=200, body={"data": {"variableUpsert": "ok"}}),
    ]
    request_payloads = []
    sleep_delays = []

    def fake_post(url, headers=None, json=None, timeout=None):
        request_payloads.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        outcome = attempts.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(app_module.requests, "post", fake_post)
    monkeypatch.setattr(app_module.time, "sleep", lambda delay: sleep_delays.append(delay))

    success = app_module.persist_rotated_token_to_railway(
        token_json='{"token":"rotated"}',
        max_attempts=3,
        base_delay_seconds=0.5,
    )

    assert success is True
    assert len(request_payloads) == 3
    assert sleep_delays == [0.5, 1.0]
    payload_input = request_payloads[0]["json"]["variables"]["input"]
    assert payload_input["name"] == "GOOGLE_OAUTH_TOKEN_JSON"
    assert payload_input["value"] == '{"token":"rotated"}'
    assert payload_input["projectId"] == "project-123"
    assert payload_input["environmentId"] == "env-123"
    assert payload_input["serviceId"] == "service-123"


def test_persist_rotated_token_to_railway_background_spawns_daemon_thread(monkeypatch):
    captured = {}

    class FakeThread:
        def __init__(self, target=None, args=(), daemon=False):
            captured["target"] = target
            captured["args"] = args
            captured["daemon"] = daemon
            captured["started"] = False

        def start(self):
            captured["started"] = True

    monkeypatch.setattr(app_module.threading, "Thread", FakeThread)

    app_module.persist_rotated_token_to_railway_background('{"token":"rotated"}')

    assert captured["target"] is app_module.persist_rotated_token_to_railway
    assert captured["args"] == ('{"token":"rotated"}',)
    assert captured["daemon"] is True
    assert captured["started"] is True


def test_refresh_google_oauth_token_if_needed_persists_rotated_token(monkeypatch):
    persisted_tokens = []

    class FakeCreds:
        expired = True
        refresh_token = "refresh-token"

        def __init__(self):
            self._token_json = '{"token":"old"}'
            self.refresh_calls = 0

        def to_json(self):
            return self._token_json

        def refresh(self, _request):
            self.refresh_calls += 1
            self._token_json = '{"token":"new"}'

    monkeypatch.setattr(app_module, "Request", lambda: object())
    monkeypatch.setattr(
        app_module,
        "persist_rotated_token_to_railway_background",
        lambda token_json: persisted_tokens.append(token_json),
    )
    monkeypatch.setattr(app_module, "GOOGLE_OAUTH_TOKEN_JSON", '{"token":"old"}')

    creds = FakeCreds()
    app_module.refresh_google_oauth_token_if_needed(creds)

    assert creds.refresh_calls == 1
    assert persisted_tokens == ['{"token":"new"}']
    assert app_module.GOOGLE_OAUTH_TOKEN_JSON == '{"token":"new"}'
    assert os.environ["GOOGLE_OAUTH_TOKEN_JSON"] == '{"token":"new"}'


def test_refresh_google_oauth_token_if_needed_skips_when_not_expired(monkeypatch):
    persisted_tokens = []

    class FakeCreds:
        expired = False
        refresh_token = "refresh-token"

        def to_json(self):
            return '{"token":"unchanged"}'

        def refresh(self, _request):
            raise AssertionError("refresh should not be called when token is not expired")

    monkeypatch.setattr(
        app_module,
        "persist_rotated_token_to_railway_background",
        lambda token_json: persisted_tokens.append(token_json),
    )

    app_module.refresh_google_oauth_token_if_needed(FakeCreds())

    assert persisted_tokens == []
