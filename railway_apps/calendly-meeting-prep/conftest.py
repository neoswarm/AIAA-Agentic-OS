import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parent / "app.py"
MODULE_SPEC = importlib.util.spec_from_file_location("calendly_meeting_prep_gateway_app", MODULE_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"Unable to load app module from {MODULE_PATH}")

gateway_app = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(gateway_app)


@pytest.fixture
def client():
    with gateway_app.app.test_client() as test_client:
        yield test_client
