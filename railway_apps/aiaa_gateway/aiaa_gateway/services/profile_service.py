"""Gateway profile token storage helpers."""

from __future__ import annotations

import base64
import hashlib
import os
import re
from collections.abc import Mapping
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken


ENCRYPTED_TOKEN_PREFIX = "enc:v1:"
PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")


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


def normalize_profile_id(profile_id: Optional[str]) -> str:
    """Normalize and validate a profile_id for gateway profile lookups."""
    normalized = (profile_id or "").strip().lower()
    if not normalized:
        return ""
    if not PROFILE_ID_PATTERN.fullmatch(normalized):
        return ""
    return normalized


def _token_from_profile_record(record: Any) -> Optional[str]:
    """Extract stored token text from a profile-store record value."""
    if isinstance(record, str):
        return record
    if isinstance(record, Mapping):
        encrypted = record.get("encrypted_token")
        if isinstance(encrypted, str) and encrypted.strip():
            return encrypted
        token = record.get("token")
        if isinstance(token, str) and token.strip():
            return token
    return None


def _profile_token_env_keys(profile_id: str) -> tuple[str, ...]:
    suffix = profile_id.upper().replace("-", "_")
    keys = [f"GATEWAY_PROFILE_TOKEN_{suffix}"]
    if profile_id == "default":
        keys.extend(["GATEWAY_PROFILE_TOKEN_DEFAULT", "GATEWAY_PROFILE_TOKEN"])
        keys.append("CLAUDE_SETUP_TOKEN")
    return tuple(keys)


def resolve_stored_profile_token(
    profile_id: str,
    *,
    profile_store: Mapping[str, Any] | None = None,
) -> Optional[str]:
    """Resolve and decrypt the stored setup-token for a profile if available."""
    normalized_profile_id = normalize_profile_id(profile_id)
    if not normalized_profile_id:
        return None

    stored_token: Optional[str] = None
    if profile_store is not None:
        stored_token = _token_from_profile_record(profile_store.get(normalized_profile_id))

    if not stored_token:
        for env_key in _profile_token_env_keys(normalized_profile_id):
            candidate = (os.getenv(env_key) or "").strip()
            if candidate:
                stored_token = candidate
                break

    if not stored_token:
        return None

    try:
        token = decrypt_token_from_storage(stored_token)
    except RuntimeError:
        return None

    if not token:
        return None
    return token.strip() or None
