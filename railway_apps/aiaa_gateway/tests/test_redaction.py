"""Tests for gateway token redaction utilities."""

from __future__ import annotations

from pathlib import Path
import sys


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aiaa_gateway.redaction import redact_exception_message, redact_token_like_text


def test_redact_token_like_text_masks_common_token_patterns():
    raw_bearer = "Bearer sk-ant-api03-super-secret-token-1234567890"
    raw_prefix = "github_pat_1234567890abcdefghijklmno"
    raw_kv = "api_key=pplx-super-secret-token-1234567890"
    raw_jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ."
        "signedpayload1234567890"
    )
    sample = f"{raw_bearer} {raw_prefix} {raw_kv} {raw_jwt}"

    redacted = redact_token_like_text(sample)

    assert raw_bearer not in redacted
    assert raw_prefix not in redacted
    assert raw_kv not in redacted
    assert raw_jwt not in redacted
    assert "Bearer " in redacted
    assert "api_key=" in redacted


def test_redact_exception_message_masks_token_values():
    raw_token = "sk-or-secret-token-1234567890"
    error = RuntimeError(f"gateway failed: token={raw_token}")

    redacted = redact_exception_message(error)

    assert raw_token not in redacted
    assert "token=" in redacted
