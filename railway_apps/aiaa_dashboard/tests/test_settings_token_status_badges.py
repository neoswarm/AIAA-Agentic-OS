from pathlib import Path


SETTINGS_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "settings.html"


def _settings_template() -> str:
    return SETTINGS_TEMPLATE_PATH.read_text(encoding="utf-8")


def test_token_status_badges_include_action_state_styles():
    template = _settings_template()

    assert ".api-key-status.validating" in template
    assert ".api-key-status.saving" in template
    assert ".api-key-status.rotating" in template
    assert ".api-key-status.revoking" in template
    assert "@keyframes tokenStatusPulse" in template


def test_settings_actions_set_in_progress_token_badges():
    template = _settings_template()

    assert "var TOKEN_ACTION_STATUS = {" in template
    assert "validate: { status: 'validating', text: 'Validating...' }" in template
    assert "save: { status: 'saving', text: 'Saving...' }" in template
    assert "rotate: { status: 'rotating', text: 'Rotating...' }" in template
    assert "revoke: { status: 'revoking', text: 'Revoking...' }" in template
    assert "setTokenActionStatus(keyName, 'validate');" in template
    assert "setTokenActionStatus(keyName, 'save');" in template
    assert "setTokenActionStatus(keyName, 'rotate');" in template
    assert "setTokenActionStatus(keyName, 'revoke');" in template
    assert "setTokenActionStatus('claude', 'validate');" in template
    assert "setTokenActionStatus('claude', 'save');" in template


def test_claude_controls_have_explicit_validate_and_save_actions():
    template = _settings_template()

    assert 'data-action="validate" onclick="testClaudeToken()"' in template
    assert 'data-action="save" onclick="saveClaudeToken()"' in template
