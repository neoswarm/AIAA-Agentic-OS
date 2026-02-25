"""AIAA Gateway application package."""

from flask import Flask

from .routes import gateway_bp


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the AIAA Gateway Flask app."""
    app = Flask(__name__)
    app.config.from_mapping(
        SERVICE_NAME="aiaa_gateway",
        JSON_SORT_KEYS=False,
    )

    if test_config:
        app.config.update(test_config)

    app.register_blueprint(gateway_bp)
    return app
