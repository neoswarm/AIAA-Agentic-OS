"""Token redaction helpers for gateway logs and exception messages."""

from __future__ import annotations

import re


_TOKEN_BEARER_PATTERN = re.compile(r"(?i)\b(bearer)(\s+)([A-Za-z0-9._\-]{8,})\b")
_TOKEN_PREFIX_PATTERN = re.compile(
    r"\b(?:sk-or-|pplx-|sk-ant-|sk-|xox[baprs]-|ghp_|github_pat_)[A-Za-z0-9._\-]{8,}\b",
    re.IGNORECASE,
)
_TOKEN_KEY_VALUE_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|authorization)\b(\s*[:=]\s*)([^\s\"',;]{8,})"
)
_TOKEN_JWT_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9._\-]{5,}\.[A-Za-z0-9._\-]{5,}\b"
)


def redact_token(token: str) -> str:
    clean = (token or "").strip()
    if not clean:
        return clean
    if len(clean) <= 10:
        return "***"
    return f"{clean[:6]}...{clean[-4:]}"


def redact_token_like_text(value: str) -> str:
    """Redact common token-like patterns from freeform text."""
    if not isinstance(value, str) or not value:
        return value

    redacted = _TOKEN_BEARER_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{redact_token(match.group(3))}",
        value,
    )
    redacted = _TOKEN_KEY_VALUE_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{redact_token(match.group(3))}",
        redacted,
    )
    redacted = _TOKEN_PREFIX_PATTERN.sub(
        lambda match: redact_token(match.group(0)),
        redacted,
    )
    redacted = _TOKEN_JWT_PATTERN.sub(
        lambda match: redact_token(match.group(0)),
        redacted,
    )
    return redacted


def redact_exception_message(exc: BaseException) -> str:
    """Build a token-redacted exception message for logs and API errors."""
    return redact_token_like_text(str(exc))
