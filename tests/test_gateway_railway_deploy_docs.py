from pathlib import Path


DOC_PATH = Path("railway_apps/gateway_service/RAILWAY_DEPLOY.md")


def test_gateway_railway_deploy_doc_exists():
    assert DOC_PATH.exists(), f"Missing deploy doc: {DOC_PATH}"


def test_gateway_railway_deploy_doc_has_initial_sections():
    content = DOC_PATH.read_text(encoding="utf-8")
    required_sections = [
        "# Gateway Service Railway Deploy (Initial)",
        "## Prerequisites",
        "## Required Service Files",
        "## Required Environment Variables",
        "## Deploy Steps",
        "## Verification",
        "## Rollback",
    ]
    for section in required_sections:
        assert section in content, f"Missing required section: {section}"
