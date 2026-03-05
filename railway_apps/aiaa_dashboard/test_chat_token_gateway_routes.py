#!/usr/bin/env python3
"""Route tests for gateway-backed token save/validate/revoke/rotate flows."""

from __future__ import annotations

from flask import Flask
import pytest

import routes.chat as chat_routes


class _FakeGatewayClient:
    """Simple fake gateway client that records POST calls."""

    calls = []
    responses = {}

    def __init__(self, base_url, api_key=None, **_kwargs):
        self.base_url = base_url
        self.api_key = api_key

    def post_json(self, path, *, payload=None, **_kwargs):
        _FakeGatewayClient.calls.append(
            {
                "base_url": self.base_url,
                "api_key": self.api_key,
                "path": path,
                "payload": payload or {},
            }
        )
        return _FakeGatewayClient.responses.get(path, {"status": "ok"})


@pytest.fixture()
def app(monkeypatch):
    application = Flask(__name__)
    application.config["TESTING"] = True
    application.secret_key = "chat-gateway-route-test-secret"
    application.config["CHAT_BACKEND"] = "gateway"
    application.register_blueprint(chat_routes.chat_bp)

    store = {}

    def _set_setting(key, value, **_kwargs):
        store[key] = value
        return 1

    def _get_setting(key):
        return store.get(key)

    def _delete_setting(key):
        store.pop(key, None)
        return 1

    monkeypatch.setattr(chat_routes.models, "set_setting", _set_setting, raising=False)
    monkeypatch.setattr(chat_routes.models, "get_setting", _get_setting, raising=False)
    monkeypatch.setattr(
        chat_routes.models, "delete_setting", _delete_setting, raising=False
    )

    monkeypatch.setattr(chat_routes, "_persist_to_railway_async", lambda *_: False)
    monkeypatch.setattr(chat_routes, "init_chat_runner", lambda *_: None)
    monkeypatch.setattr(chat_routes, "GatewayClient", _FakeGatewayClient)
    monkeypatch.setenv("GATEWAY_BASE_URL", "https://gateway.example.test")
    monkeypatch.setenv("GATEWAY_API_KEY", "gateway-api-key")

    _FakeGatewayClient.calls = []
    _FakeGatewayClient.responses = {}
    application.config["TOKEN_STORE"] = store
    return application


@pytest.fixture()
def auth_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "test-admin"
    return client


def test_save_token_calls_gateway_profile_upsert(auth_client, app, monkeypatch):
    token = "sk-ant-api03-save-token-12345"
    _FakeGatewayClient.responses["/v1/profiles/upsert"] = {
        "status": "ok",
        "profile_id": "default",
        "validation": "valid",
        "validation_detail": {"status": "valid", "message": "Gateway accepted token"},
    }
    monkeypatch.setattr(
        chat_routes,
        "validate_claude_token",
        lambda _token: {"status": "valid", "http_status": 200, "message": "valid"},
    )

    resp = auth_client.post("/api/chat/token", json={"token": token})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert app.config["TOKEN_STORE"][chat_routes.CLAUDE_TOKEN_SETTING_KEY] == token
    assert _FakeGatewayClient.calls[-1]["path"] == "/v1/profiles/upsert"
    payload = _FakeGatewayClient.calls[-1]["payload"]
    assert payload["profile_id"] == "default"
    assert payload["token"] == token


def test_validate_token_calls_gateway_profile_validate(auth_client, monkeypatch):
    token = "sk-ant-api03-validate-token-12345"
    _FakeGatewayClient.responses["/v1/profiles/validate"] = {
        "status": "ok",
        "profile_id": "default",
        "validation": "valid",
        "validation_detail": {"status": "valid", "message": "Gateway runtime canary ok"},
    }

    def _unexpected_provider_validation(_token):
        raise AssertionError("Direct provider token validation should not run")

    monkeypatch.setattr(chat_routes, "validate_claude_token", _unexpected_provider_validation)

    resp = auth_client.post("/api/chat/token/validate", json={"token": token})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["configured"] is True
    assert body["validation"] == "valid"
    assert _FakeGatewayClient.calls[-1]["path"] == "/v1/profiles/validate"
    assert _FakeGatewayClient.calls[-1]["payload"] == {
        "profile_id": "default",
        "token": token,
    }


def test_revoke_token_calls_gateway_profile_revoke(auth_client, app, monkeypatch):
    token = "sk-ant-api03-revoke-token-12345"
    app.config["TOKEN_STORE"][chat_routes.CLAUDE_TOKEN_SETTING_KEY] = token
    monkeypatch.setenv("CLAUDE_SETUP_TOKEN", token)
    _FakeGatewayClient.responses["/v1/profiles/revoke"] = {
        "status": "ok",
        "profile_id": "default",
        "revoked": True,
    }

    resp = auth_client.post("/api/chat/token/revoke")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["revoked"] is True
    assert _FakeGatewayClient.calls[-1]["path"] == "/v1/profiles/revoke"
    assert _FakeGatewayClient.calls[-1]["payload"] == {"profile_id": "default"}
    assert "CLAUDE_SETUP_TOKEN" not in chat_routes.os.environ
    assert chat_routes.CLAUDE_TOKEN_SETTING_KEY not in app.config["TOKEN_STORE"]


def test_rotate_token_calls_gateway_profile_upsert(auth_client, app, monkeypatch):
    old_token = "sk-ant-api03-old-token-12345"
    new_token = "sk-ant-api03-new-token-67890"
    app.config["TOKEN_STORE"][chat_routes.CLAUDE_TOKEN_SETTING_KEY] = old_token
    monkeypatch.setenv("CLAUDE_SETUP_TOKEN", old_token)
    _FakeGatewayClient.responses["/v1/profiles/upsert"] = {
        "status": "ok",
        "profile_id": "default",
        "validation": "valid",
        "validation_detail": {"status": "valid", "message": "Gateway rotated token"},
    }
    monkeypatch.setattr(
        chat_routes,
        "validate_claude_token",
        lambda _token: {"status": "valid", "http_status": 200, "message": "valid"},
    )

    resp = auth_client.post(
        "/api/chat/token/rotate",
        json={"current_token": old_token, "new_token": new_token},
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["validation"] == "valid"
    assert _FakeGatewayClient.calls[-1]["path"] == "/v1/profiles/upsert"
    assert _FakeGatewayClient.calls[-1]["payload"] == {
        "profile_id": "default",
        "token": new_token,
    }
    assert app.config["TOKEN_STORE"][chat_routes.CLAUDE_TOKEN_SETTING_KEY] == new_token
    assert chat_routes.os.environ["CLAUDE_SETUP_TOKEN"] == new_token


def test_railway_persist_uses_config_fallback_service_id(monkeypatch):
    captured = {}

    class _OkResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"data": {"variableUpsert": True}}

    def _fake_post(url, *, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json or {}
        captured["headers"] = headers or {}
        captured["timeout"] = timeout
        return _OkResponse()

    monkeypatch.setenv("RAILWAY_API_TOKEN", "railway-api-token")
    monkeypatch.delenv("RAILWAY_SERVICE_ID", raising=False)
    monkeypatch.setattr(
        chat_routes.Config,
        "RAILWAY_SERVICE_ID",
        "service-from-config",
        raising=False,
    )
    monkeypatch.setattr(chat_routes.http_requests, "post", _fake_post)

    persisted = chat_routes._persist_to_railway_async(
        {"CLAUDE_SETUP_TOKEN": "sk-ant-oat01-test-token"}
    )

    assert persisted is True
    assert captured["json"]["variables"]["input"]["serviceId"] == "service-from-config"


def test_railway_persist_returns_false_on_graphql_errors(monkeypatch):
    class _ErrorResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"errors": [{"message": "bad request"}]}

    monkeypatch.setenv("RAILWAY_API_TOKEN", "railway-api-token")
    monkeypatch.setenv("RAILWAY_SERVICE_ID", "service-id")
    monkeypatch.setattr(
        chat_routes.http_requests, "post", lambda *args, **kwargs: _ErrorResponse()
    )

    persisted = chat_routes._persist_to_railway_async({"CLAUDE_SETUP_TOKEN": "token"})
    assert persisted is False
