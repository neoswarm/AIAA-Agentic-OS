"""Gateway profile token storage helpers."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
import hashlib
import os
import re
from typing import Any, MutableMapping, Optional

from cryptography.fernet import Fernet, InvalidToken


ENCRYPTED_TOKEN_PREFIX = "enc:v1:"
PROFILE_ID_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}")


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


def is_valid_profile_id(profile_id: str) -> bool:
    """Return True when the supplied profile_id passes gateway validation."""
    return bool(PROFILE_ID_PATTERN.fullmatch((profile_id or "").strip()))


def revoke_profile(
    profile_store: MutableMapping[str, dict[str, Any]],
    profile_id: str,
) -> dict[str, Any]:
    """Invalidate a profile and remove any persisted token material."""
    normalized_profile_id = (profile_id or "").strip()
    if not normalized_profile_id:
        raise ValueError("profile_id is required.")
    if not is_valid_profile_id(normalized_profile_id):
        raise ValueError("profile_id is invalid.")

    existing = profile_store.get(normalized_profile_id)
    record = dict(existing) if isinstance(existing, dict) else {}
    record.pop("token", None)
    record.pop("encrypted_token", None)

    revoked_at = datetime.now(UTC).isoformat()
    record["profile_id"] = normalized_profile_id
    record["status"] = "revoked"
    record["revoked_at"] = revoked_at
    record["updated_at"] = revoked_at
    profile_store[normalized_profile_id] = record
    return record
