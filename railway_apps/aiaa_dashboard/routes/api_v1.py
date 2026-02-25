#!/usr/bin/env python3
"""AIAA Dashboard API v1 routes."""

import os
from functools import wraps

from flask import Blueprint, jsonify, request, session

from services.profile_service import ProfileServiceError, upsert_profile


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/v1")


def login_required(f):
    """Require session login or API key auth for v1 API endpoints."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("logged_in"):
            return f(*args, **kwargs)
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key == os.getenv("DASHBOARD_API_KEY"):
            return f(*args, **kwargs)
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    return decorated


@api_v1_bp.route("/profiles/upsert", methods=["POST"])
@login_required
def api_upsert_profile():
    """Create or update a client profile."""
    data = request.get_json(silent=True) or {}

    try:
        result = upsert_profile(data)
        status_code = 201 if result.get("action") == "created" else 200
        payload = {"status": "ok"}
        payload.update(result)
        return jsonify(payload), status_code
    except ProfileServiceError as exc:
        payload = {"status": "error", "message": exc.message}
        if exc.errors:
            payload["errors"] = exc.errors
        return jsonify(payload), exc.status_code
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
