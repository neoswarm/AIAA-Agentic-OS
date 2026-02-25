from pathlib import Path


SETTINGS_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "settings.html"


def _settings_template() -> str:
    return SETTINGS_TEMPLATE_PATH.read_text(encoding="utf-8")


def test_default_chat_profile_selector_is_rendered():
    template = _settings_template()

    assert "Default chat profile" in template
    assert 'id="pref-default-chat-profile"' in template
    assert "preferences.get('pref.default_chat_profile', 'balanced')" in template
    assert '<option value="balanced"' in template
    assert '<option value="research"' in template
    assert '<option value="creative"' in template
    assert '<option value="concise"' in template


def test_save_preferences_includes_default_chat_profile():
    template = _settings_template()

    assert "fetch('/api/v2/settings/preferences'" in template
    assert (
        "default_chat_profile: document.getElementById('pref-default-chat-profile').value"
        in template
    )
