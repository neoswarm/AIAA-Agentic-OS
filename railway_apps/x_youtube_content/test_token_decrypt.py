#!/usr/bin/env python3
"""Tests for safe token decryption utility."""

import base64
import pickle

from run import decrypt_token_pickle


def test_decrypt_token_pickle_valid_payload():
    token_obj = {"token": "abc123", "refresh_token": "r123"}
    encoded = base64.b64encode(pickle.dumps(token_obj)).decode("utf-8")

    result = decrypt_token_pickle(encoded)

    assert result == token_obj


def test_decrypt_token_pickle_empty_payload():
    assert decrypt_token_pickle("") is None
    assert decrypt_token_pickle(None) is None


def test_decrypt_token_pickle_invalid_base64():
    assert decrypt_token_pickle("%%%not-base64%%%") is None


def test_decrypt_token_pickle_invalid_pickle_payload():
    encoded = base64.b64encode(b"not a pickle payload").decode("utf-8")
    assert decrypt_token_pickle(encoded) is None
