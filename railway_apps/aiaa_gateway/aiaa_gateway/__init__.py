"""AIAA Gateway application package."""

from __future__ import annotations

import os

from flask import Flask

from .routes import gateway_bp


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the AIAA Gateway Flask app."""
    app = Flask(__name__)
    app.config.from_mapping(
        SERVICE_NAME="aiaa_gateway",
        JSON_SORT_KEYS=False,
        GATEWAY_API_KEY=os.getenv("GATEWAY_API_KEY", ""),
        GATEWAY_INTERNAL_TOKEN=os.getenv("GATEWAY_INTERNAL_TOKEN", ""),
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
    )

    if test_config:
        app.config.update(test_config)

    app.register_blueprint(gateway_bp)
    return app
