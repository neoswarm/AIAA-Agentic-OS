"""HTTP routes for AIAA Gateway."""

from datetime import datetime, UTC

from flask import Blueprint, current_app, jsonify

gateway_bp = Blueprint("gateway", __name__)


@gateway_bp.get("/")
def index():
    return jsonify(
        {
            "service": current_app.config["SERVICE_NAME"],
            "status": "ok",
        }
    )


@gateway_bp.get("/health")
def health():
    return jsonify(
        {
            "service": current_app.config["SERVICE_NAME"],
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )
