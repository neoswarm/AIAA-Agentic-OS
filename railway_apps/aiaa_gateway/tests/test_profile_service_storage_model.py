"""Tests for persistent gateway profile storage model."""

import importlib.util
import sqlite3
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


def test_ensure_profile_storage_model_creates_table(tmp_path):
    db_path = tmp_path / "gateway_profiles.db"

    profile_service.ensure_profile_storage_model(str(db_path))

    with sqlite3.connect(str(db_path)) as connection:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='gateway_profiles'"
        ).fetchone()
    assert row is not None


def test_upsert_profile_record_persists_encrypted_token_and_timestamps(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "gateway-profile-token-secret")
    db_path = tmp_path / "gateway_profiles.db"

    created = profile_service.upsert_profile_record(
        profile_id="default",
        token="setup-token-abc123",
        status="active",
        db_path=str(db_path),
    )

    assert created.profile_id == "default"
    assert created.status == "active"
    assert created.created_at
    assert created.updated_at
    assert created.encrypted_token.startswith(profile_service.ENCRYPTED_TOKEN_PREFIX)
    assert created.encrypted_token != "setup-token-abc123"
    assert (
        profile_service.decrypt_token_from_storage(created.encrypted_token)
        == "setup-token-abc123"
    )

    fetched = profile_service.get_profile_record("default", db_path=str(db_path))
    assert fetched is not None
    assert fetched.profile_id == "default"
    assert fetched.status == "active"
    assert (
        profile_service.decrypt_token_from_storage(fetched.encrypted_token)
        == "setup-token-abc123"
    )


def test_upsert_profile_record_updates_existing_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAT_TOKEN_ENCRYPTION_KEY", "gateway-profile-token-secret")
    db_path = tmp_path / "gateway_profiles.db"

    first = profile_service.upsert_profile_record(
        profile_id="tenant-a",
        token="token-one",
        status="active",
        db_path=str(db_path),
    )
    second = profile_service.upsert_profile_record(
        profile_id="tenant-a",
        token="token-two",
        status="inactive",
        db_path=str(db_path),
    )

    assert second.profile_id == "tenant-a"
    assert second.status == "inactive"
    assert second.created_at == first.created_at
    assert (
        profile_service.decrypt_token_from_storage(second.encrypted_token)
        == "token-two"
    )


def test_upsert_profile_record_validates_inputs(tmp_path):
    db_path = tmp_path / "gateway_profiles.db"

    with pytest.raises(ValueError, match="profile_id is required"):
        profile_service.upsert_profile_record(
            profile_id="",
            token="token",
            db_path=str(db_path),
        )

    with pytest.raises(ValueError, match="status must be one of"):
        profile_service.upsert_profile_record(
            profile_id="default",
            token="token",
            status="unknown",
            db_path=str(db_path),
        )
