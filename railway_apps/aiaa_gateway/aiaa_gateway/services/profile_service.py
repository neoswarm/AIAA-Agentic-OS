"""Gateway profile token storage helpers."""

from __future__ import annotations

import base64
import hashlib
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, NamedTuple, Optional

from cryptography.fernet import Fernet, InvalidToken


ENCRYPTED_TOKEN_PREFIX = "enc:v1:"
PROFILE_STATUSES = {"active", "inactive", "revoked"}
DEFAULT_PROFILE_DB_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "gateway_profiles.db"
)


class ProfileRecord(NamedTuple):
    """Persisted gateway profile row."""

    profile_id: str
    encrypted_token: str
    status: str
    created_at: str
    updated_at: str


def _resolve_profile_db_path(db_path: Optional[str] = None) -> Path:
    """Resolve profile storage file path."""
    resolved = (
        db_path
        or os.getenv("GATEWAY_PROFILE_DB_PATH")
        or os.getenv("PROFILE_STORAGE_DB_PATH")
    )
    if resolved:
        return Path(resolved)
    return DEFAULT_PROFILE_DB_PATH


@contextmanager
def _profile_db_cursor(
    db_path: Optional[str] = None,
) -> Iterator[sqlite3.Cursor]:
    """Yield a SQLite cursor with commit/rollback handling."""
    resolved_path = _resolve_profile_db_path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(resolved_path))
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def ensure_profile_storage_model(db_path: Optional[str] = None) -> None:
    """Ensure the persistent profile storage model exists."""
    with _profile_db_cursor(db_path) as cursor:
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS gateway_profiles (
                profile_id TEXT PRIMARY KEY,
                encrypted_token TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('active', 'inactive', 'revoked')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        cursor.execute(
            """CREATE INDEX IF NOT EXISTS idx_gateway_profiles_status_updated
            ON gateway_profiles(status, updated_at DESC)"""
        )


def _row_to_profile_record(row: sqlite3.Row) -> ProfileRecord:
    """Convert sqlite row to ProfileRecord."""
    return ProfileRecord(
        profile_id=str(row["profile_id"]),
        encrypted_token=str(row["encrypted_token"]),
        status=str(row["status"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def upsert_profile_record(
    profile_id: str,
    token: Optional[str],
    status: str = "active",
    db_path: Optional[str] = None,
) -> ProfileRecord:
    """Create or update a persistent profile record."""
    normalized_profile_id = (profile_id or "").strip()
    if not normalized_profile_id:
        raise ValueError("profile_id is required")

    normalized_status = (status or "").strip().lower()
    if normalized_status not in PROFILE_STATUSES:
        raise ValueError("status must be one of: active, inactive, revoked")

    ensure_profile_storage_model(db_path)
    encrypted_token = encrypt_token_for_storage(token or "")

    with _profile_db_cursor(db_path) as cursor:
        cursor.execute(
            """INSERT INTO gateway_profiles (
                profile_id, encrypted_token, status, created_at, updated_at
            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(profile_id) DO UPDATE SET
                encrypted_token = excluded.encrypted_token,
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP""",
            (normalized_profile_id, encrypted_token or "", normalized_status),
        )
        cursor.execute(
            """SELECT profile_id, encrypted_token, status, created_at, updated_at
            FROM gateway_profiles
            WHERE profile_id = ?""",
            (normalized_profile_id,),
        )
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Failed to persist gateway profile.")
    return _row_to_profile_record(row)


def get_profile_record(
    profile_id: str,
    db_path: Optional[str] = None,
) -> Optional[ProfileRecord]:
    """Fetch a persistent profile record by ID."""
    normalized_profile_id = (profile_id or "").strip()
    if not normalized_profile_id:
        return None

    ensure_profile_storage_model(db_path)
    with _profile_db_cursor(db_path) as cursor:
        cursor.execute(
            """SELECT profile_id, encrypted_token, status, created_at, updated_at
            FROM gateway_profiles
            WHERE profile_id = ?""",
            (normalized_profile_id,),
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return _row_to_profile_record(row)


def _resolve_token_encryption_key() -> str:
    """Resolve the secret used for token encryption/decryption."""
    key = (
        os.getenv("CHAT_TOKEN_ENCRYPTION_KEY")
        or os.getenv("SETTINGS_ENCRYPTION_KEY")
        or os.getenv("FLASK_SECRET_KEY")
        or os.getenv("SECRET_KEY")
    )
    if not key:
        raise RuntimeError(
            "Missing encryption key. Set CHAT_TOKEN_ENCRYPTION_KEY or FLASK_SECRET_KEY."
        )
    return key


def _build_fernet(raw_key: str) -> Fernet:
    """Build a Fernet cipher from a raw key or deterministic hash fallback."""
    try:
        return Fernet(raw_key.encode("utf-8"))
    except Exception:
        derived = base64.urlsafe_b64encode(
            hashlib.sha256(raw_key.encode("utf-8")).digest()
        )
        return Fernet(derived)


def encrypt_token_for_storage(token: Optional[str]) -> Optional[str]:
    """Encrypt a gateway profile token for at-rest storage."""
    if token is None:
        return None
    if token.startswith(ENCRYPTED_TOKEN_PREFIX):
        return token

    cipher = _build_fernet(_resolve_token_encryption_key())
    encrypted = cipher.encrypt(token.encode("utf-8")).decode("utf-8")
    return f"{ENCRYPTED_TOKEN_PREFIX}{encrypted}"


def decrypt_token_from_storage(stored_token: Optional[str]) -> Optional[str]:
    """Decrypt an encrypted gateway profile token with safe failure handling."""
    if stored_token is None:
        return None
    if not stored_token.startswith(ENCRYPTED_TOKEN_PREFIX):
        return stored_token

    cipher = _build_fernet(_resolve_token_encryption_key())
    token_value = stored_token[len(ENCRYPTED_TOKEN_PREFIX) :]
    try:
        return cipher.decrypt(token_value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
