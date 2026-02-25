"""Tests for gateway profile token encryption storage helpers."""

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "aiaa_gateway"
    / "services"
    / "profile_service.py"
)
SPEC = importlib.util.spec_from_file_location("gateway_profile_service", MODULE_PATH)
profile_service = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profile_service)


def test_encrypt_and_decrypt_token_round_trip(monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "gateway-profile-token-secret")
    token = "sk-ant-session-token-12345"

    encrypted = profile_service.encrypt_token_for_storage(token)

    assert encrypted != token
    assert encrypted.startswith(profile_service.ENCRYPTED_TOKEN_PREFIX)
    assert profile_service.decrypt_token_from_storage(encrypted) == token


def test_encrypt_token_is_idempotent_for_prefixed_value(monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "gateway-profile-token-secret")
    encrypted_once = profile_service.encrypt_token_for_storage("test-token")

    encrypted_twice = profile_service.encrypt_token_for_storage(encrypted_once)

    assert encrypted_twice == encrypted_once


def test_decrypt_plain_token_passthrough(monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "gateway-profile-token-secret")

    assert (
        profile_service.decrypt_token_from_storage("plain-token-value")
        == "plain-token-value"
    )


def test_decrypt_invalid_encrypted_token_returns_none(monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "gateway-profile-token-secret")

    assert (
        profile_service.decrypt_token_from_storage("enc:v1:not-a-valid-token") is None
    )


def test_encrypt_raises_when_no_key_is_configured(monkeypatch):
    monkeypatch.delenv("CHAT_TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError):
        profile_service.encrypt_token_for_storage("any-token")


def test_flask_secret_key_fallback_supports_round_trip(monkeypatch):
    monkeypatch.delenv("CHAT_TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("FLASK_SECRET_KEY", "fallback-flask-secret")
    token = "setup-token-xyz"

    encrypted = profile_service.encrypt_token_for_storage(token)

    assert profile_service.decrypt_token_from_storage(encrypted) == token
