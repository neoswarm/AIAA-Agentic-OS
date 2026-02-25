#!/usr/bin/env python3
"""Regression tests for API keys template."""

from pathlib import Path


def test_api_keys_revoke_uses_modal_confirmation():
    """Token revoke should use the shared confirmation modal helper."""
    template_path = Path(__file__).parent / "templates" / "api_keys.html"
    html = template_path.read_text(encoding="utf-8")

    assert 'async function revokeKey(keyId, keyName)' in html
    assert 'await confirmAction(`Are you sure you want to revoke "${keyName}"? This cannot be undone.`);' in html
    assert 'if (!confirm(`Are you sure you want to revoke "${keyName}"? This cannot be undone.`)) {' not in html
