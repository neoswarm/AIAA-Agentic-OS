"""AIAA Gateway application package."""

from __future__ import annotations

import os
import logging

from flask import Flask

from .routes import gateway_bp
from .services.profile_service import validate_token_encryption_key

logger = logging.getLogger(__name__)


def _validate_startup_configuration(app: Flask) -> None:
    """Validate required secrets before serving requests."""
    if not str(app.config.get("ANTHROPIC_API_KEY", "")).strip():
        logger.warning(
            "ANTHROPIC_API_KEY is not configured; gateway will require setup/profile tokens."
        )
    validate_token_encryption_key()


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the AIAA Gateway Flask app."""
    app = Flask(__name__)
    app.config.from_mapping(
        SERVICE_NAME="aiaa_gateway",
        JSON_SORT_KEYS=False,
        GATEWAY_API_KEY=os.getenv("GATEWAY_API_KEY", ""),
        GATEWAY_INTERNAL_TOKEN=os.getenv("GATEWAY_INTERNAL_TOKEN", ""),
        GATEWAY_AUTH_FAILURE_MAX_ATTEMPTS=int(
            os.getenv("GATEWAY_AUTH_FAILURE_MAX_ATTEMPTS", "5")
        ),
        GATEWAY_AUTH_FAILURE_WINDOW_SECONDS=int(
            os.getenv("GATEWAY_AUTH_FAILURE_WINDOW_SECONDS", "60")
        ),
        ANTHROPIC_BASE_URL=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        ANTHROPIC_API_VERSION=os.getenv("ANTHROPIC_API_VERSION", "2023-06-01"),
        ANTHROPIC_API_KEY=os.getenv("ANTHROPIC_API_KEY", ""),
        DEFAULT_ANTHROPIC_MODEL=os.getenv(
            "DEFAULT_ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"
        ),
        DEFAULT_MAX_OUTPUT_TOKENS=int(os.getenv("DEFAULT_MAX_OUTPUT_TOKENS", "1024")),
        UPSTREAM_REQUEST_TIMEOUT_SECONDS=float(
            os.getenv("UPSTREAM_REQUEST_TIMEOUT_SECONDS", "30")
        ),
        PROFILE_STORE={},
        GATEWAY_RUNTIME_CANARY_TIMEOUT_SECONDS=float(
            os.getenv("GATEWAY_RUNTIME_CANARY_TIMEOUT_SECONDS", "12")
        ),
        PROFILE_TOKEN_STORE={},
    )

    if test_config:
        app.config.update(test_config)

    _validate_startup_configuration(app)
    app.register_blueprint(gateway_bp)
    return app
