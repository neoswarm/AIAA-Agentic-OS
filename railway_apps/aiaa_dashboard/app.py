#!/usr/bin/env python3
"""
AIAA Agentic OS Dashboard - Modular Application v5.0

A clean, modular Flask application for managing workflows, executions, and deployments.
Features password-protected auth, REST API, webhook management, and Railway integration.
"""

import os
import hashlib
import hmac
from functools import wraps
from pathlib import Path

from flask import Flask, session, redirect, url_for, render_template

# Import configuration and database
from config import get_config
import database
import models

# Import blueprints
from routes import api_bp, views_bp, api_v2_bp, chat_bp, init_chat_runner

VERSION = "5.0"


# =============================================================================
# Application Factory
# =============================================================================


def create_app(config_class=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    if config_class is None:
        config_class = get_config()
    
    app.config.from_object(config_class)
    # Re-read env overrides at app-creation time so tests and subprocesses that
    # mutate env vars after module import still get the correct runtime config.
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", app.config.get("SECRET_KEY"))
    app.config["DASHBOARD_USERNAME"] = os.getenv(
        "DASHBOARD_USERNAME", app.config.get("DASHBOARD_USERNAME")
    )
    app.config["DASHBOARD_PASSWORD_HASH"] = os.getenv(
        "DASHBOARD_PASSWORD_HASH", app.config.get("DASHBOARD_PASSWORD_HASH")
    )
    app.config["DB_PATH"] = os.getenv("DB_PATH", app.config.get("DB_PATH"))

    app.secret_key = app.config["SECRET_KEY"]
    app.config["PROJECT_ROOT"] = str(Path(__file__).resolve().parents[2])

    # Configure session cookies
    app.config["SESSION_COOKIE_SECURE"] = config_class.SESSION_COOKIE_SECURE
    app.config["SESSION_COOKIE_HTTPONLY"] = config_class.SESSION_COOKIE_HTTPONLY
    app.config["SESSION_COOKIE_SAMESITE"] = config_class.SESSION_COOKIE_SAMESITE
    app.config["PERMANENT_SESSION_LIFETIME"] = config_class.PERMANENT_SESSION_LIFETIME

    # Set database path
    database.set_db_path(app.config["DB_PATH"])

    # Initialize database
    with app.app_context():
        database.init_db(app)
        print(f"✅ Database initialized at {app.config['DB_PATH']}")

        # Validate configuration
        validation = config_class.validate_config()
        if not validation["valid"]:
            print("❌ Configuration errors:")
            for issue in validation["issues"]:
                print(f"   - {issue}")
        if validation["warnings"]:
            print("⚠️  Configuration warnings:")
            for warning in validation["warnings"]:
                print(f"   - {warning}")

    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(api_v2_bp)
    app.register_blueprint(chat_bp)

    with app.app_context():
        init_chat_runner(app)

    print(f"✅ Registered API blueprint at /api")
    print(f"✅ Registered API v2 blueprint at /api/v2")
    print(f"✅ Registered views blueprint at /")
    print(f"✅ Registered chat blueprint at /chat and /api/chat/*")

    # App-level error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        if session.get("logged_in"):
            username = session.get("username", "Admin")
            return (
                render_template(
                    "error_v2.html",
                    username=username,
                    active_page=None,
                    error_code=404,
                ),
                404,
            )
        return redirect(url_for("views.login"))

    @app.errorhandler(500)
    def internal_error(e):
        if session.get("logged_in"):
            username = session.get("username", "Admin")
            return (
                render_template(
                    "error_v2.html",
                    username=username,
                    active_page=None,
                    error_code=500,
                    error_message=str(e) if app.debug else None,
                ),
                500,
            )
        return redirect(url_for("views.login"))

    return app


# =============================================================================
# Helper Functions
# =============================================================================


def hash_password(password: str) -> str:
    """Hash password with SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def check_password(password: str) -> bool:
    """Check password against configured hash."""
    from config import Config
    
    password_hash = os.getenv("DASHBOARD_PASSWORD_HASH", Config.DASHBOARD_PASSWORD_HASH)

    if not password_hash:
        return False

    # Detect bcrypt hash (starts with $2b$)
    if password_hash.startswith("$2b$"):
        try:
            import bcrypt

            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except ImportError:
            print("⚠️  bcrypt not installed, falling back to SHA-256")
            return False

    # Legacy SHA-256 with constant-time comparison
    return hmac.compare_digest(
        hashlib.sha256(password.encode()).hexdigest(), password_hash
    )


def login_required(f):
    """Decorator to require login for a route."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("views.login"))
        return f(*args, **kwargs)

    return decorated_function


# =============================================================================
# Application Instance
# =============================================================================

# Create app instance
app = create_app()


@app.context_processor
def inject_version():
    return dict(version=VERSION)


# Make helper functions available to routes
app.check_password = check_password
app.login_required = login_required


# =============================================================================
# CLI Commands
# =============================================================================


@app.cli.command()
def init_db():
    """Initialize the database."""
    database.init_db(app)
    print("✅ Database initialized")


@app.cli.command()
def validate_config():
    """Validate configuration."""
    from config import get_config

    config = get_config()
    validation = config.validate_config()

    print("Configuration Validation")
    print("=" * 50)

    if validation["valid"]:
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration has errors:")
        for issue in validation["issues"]:
            print(f"   - {issue}")

    if validation["warnings"]:
        print("\n⚠️  Warnings:")
        for warning in validation["warnings"]:
            print(f"   - {warning}")


@app.cli.command()
def cleanup_db():
    """Clean up old events and logs."""
    events_deleted = database.cleanup_old_events(days=30)
    logs_deleted = database.cleanup_old_webhook_logs(days=7)
    print(f"✅ Deleted {events_deleted} old events")
    print(f"✅ Deleted {logs_deleted} old webhook logs")
    database.vacuum()
    print("✅ Database vacuumed")


@app.cli.command()
def check_health():
    """Check database health."""
    health = database.check_health()
    print("Database Health Check")
    print("=" * 50)
    print(f"Status: {health['status']}")
    print(f"Path: {health.get('path', 'N/A')}")

    if "stats" in health:
        print("\nStatistics:")
        for key, value in health["stats"].items():
            print(f"  {key}: {value}")

    if "error" in health:
        print(f"\n❌ Error: {health['error']}")


# =============================================================================
# Development Server
# =============================================================================

if __name__ == "__main__":
    from config import Config

    # Print startup info
    print("\n" + "=" * 60)
    print("AIAA Agentic OS Dashboard v5.0")
    print("=" * 60)
    print(f"Environment: {os.getenv('FLASK_ENV', 'production')}")
    print(f"Host: {Config.HOST}:{Config.PORT}")
    print(f"Debug: {Config.DEBUG}")
    print(f"Database: {Config.DB_PATH}")
    print("=" * 60 + "\n")

    # Run the app
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
