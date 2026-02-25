from pathlib import Path


SETTINGS_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "settings.html"


def _settings_template() -> str:
    return SETTINGS_TEMPLATE_PATH.read_text(encoding="utf-8")


def test_settings_template_loads_token_lifecycle_helper():
    template = _settings_template()
    assert "filename='js/token_lifecycle.js'" in template


def test_settings_test_flow_checks_status_payload_and_lifecycle_mapping():
    template = _settings_template()
    assert "if (!data || data.status !== 'ok')" in template
    assert "var mapped = mapApiKeyLifecycleStatus(keyData);" in template
    assert "if ((mapped.statusClass === 'invalid' || mapped.statusClass === 'warning') && keyData.last_error)" in template


def test_settings_initial_status_uses_token_lifecycle_mapper():
    template = _settings_template()
    assert "var mapped = mapApiKeyLifecycleStatus(data.keys[key] || {});" in template
