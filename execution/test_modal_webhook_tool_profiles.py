#!/usr/bin/env python3
"""Tests for named tool profiles in execution/modal_webhook.py."""

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("modal_webhook.py")
SPEC = importlib.util.spec_from_file_location("modal_webhook", MODULE_PATH)
modal_webhook = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(modal_webhook)


def test_safe_profile_resolves_expected_tools():
    tools, profile = modal_webhook.resolve_allowed_tools({"tool_profile": "safe"})

    assert profile == "safe"
    assert tools == modal_webhook.TOOL_PROFILES["safe"]


def test_tools_string_alias_supports_named_profiles():
    tools, profile = modal_webhook.resolve_allowed_tools({"tools": "full"})

    assert profile == "full"
    assert tools == modal_webhook.TOOL_PROFILES["full"]
    assert set(tools) == set(modal_webhook.ALL_TOOLS.keys())


def test_missing_config_uses_default_profile():
    tools, profile = modal_webhook.resolve_allowed_tools({})

    assert profile == modal_webhook.DEFAULT_TOOL_PROFILE
    assert tools == modal_webhook.TOOL_PROFILES[modal_webhook.DEFAULT_TOOL_PROFILE]


def test_unknown_profile_falls_back_to_default():
    tools, profile = modal_webhook.resolve_allowed_tools(
        {"tool_profile": "not-a-real-profile"}
    )

    assert profile == modal_webhook.DEFAULT_TOOL_PROFILE
    assert tools == modal_webhook.TOOL_PROFILES[modal_webhook.DEFAULT_TOOL_PROFILE]


def test_explicit_tools_list_stays_supported_and_filters_unknown_tools():
    tools, profile = modal_webhook.resolve_allowed_tools(
        {"tools": ["send_email", "create_folder", "web_fetch"]}
    )

    assert profile == "custom"
    assert tools == ["send_email", "web_fetch"]
