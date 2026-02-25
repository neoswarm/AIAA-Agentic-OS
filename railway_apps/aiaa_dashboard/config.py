"""
AIAA Dashboard - Configuration Module
Centralized configuration with environment variable management.
"""

import os
import secrets
from datetime import timedelta
from pathlib import Path


class Config:
    """Application configuration."""
    
    # Flask Configuration
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
    CHAT_TOKEN_ENCRYPTION_KEY = os.getenv("CHAT_TOKEN_ENCRYPTION_KEY", "")
    
    # Dashboard Authentication
    DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
    DASHBOARD_PASSWORD_HASH = os.getenv("DASHBOARD_PASSWORD_HASH", "")
    
    # Database Configuration
    DB_PATH = os.getenv("DB_PATH", str(Path(__file__).parent / "data" / "dashboard.db"))
    DB_BACKUP_ENABLED = os.getenv("DB_BACKUP_ENABLED", "true").lower() == "true"
    DB_BACKUP_INTERVAL_HOURS = int(os.getenv("DB_BACKUP_INTERVAL_HOURS", "24"))
    
    # Railway API Configuration
    RAILWAY_API_TOKEN = os.getenv("RAILWAY_API_TOKEN", "")
    RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"
    RAILWAY_PROJECT_ID = os.getenv("RAILWAY_PROJECT_ID", "3b96c81f-9518-4131-b2bc-bcd7a524a5ef")
    RAILWAY_SERVICE_ID = os.getenv("RAILWAY_SERVICE_ID", "415686bb-d10c-40c5-b610-4c5e41bbe762")
    RAILWAY_ENVIRONMENT_ID = os.getenv("RAILWAY_ENVIRONMENT_ID", os.getenv("RAILWAY_ENV_ID", "951885c9-85a5-46f5-96a1-2151936b0314"))
    
    # Tracked Environment Variables
    TRACKED_ENV_VARS = [
        "OPENROUTER_API_KEY",
        "PERPLEXITY_API_KEY",
        "SLACK_WEBHOOK_URL",
        "CHAT_TOKEN_ENCRYPTION_KEY",
        "CALENDLY_API_KEY",
        "GOOGLE_OAUTH_TOKEN_JSON",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "FAL_KEY",
        "RAILWAY_API_TOKEN",
    ]
    
    # Workflow Configuration
    WORKFLOW_CACHE_TTL_SECONDS = int(os.getenv("WORKFLOW_CACHE_TTL_SECONDS", "300"))  # 5 minutes

    # Query & Pagination Limits
    DEFAULT_RECENT_WORKFLOWS_LIMIT = int(os.getenv("DEFAULT_RECENT_WORKFLOWS_LIMIT", "5"))
    DEFAULT_EXECUTIONS_LIMIT = int(os.getenv("DEFAULT_EXECUTIONS_LIMIT", "50"))
    DEFAULT_EVENTS_LIMIT = int(os.getenv("DEFAULT_EVENTS_LIMIT", "100"))
    DEFAULT_OUTPUTS_LIMIT = int(os.getenv("DEFAULT_OUTPUTS_LIMIT", "50"))
    DEFAULT_RECENT_SKILL_EXECUTIONS_LIMIT = int(os.getenv("DEFAULT_RECENT_SKILL_EXECUTIONS_LIMIT", "10"))
    DEFAULT_RECOMMENDED_SKILLS_LIMIT = int(os.getenv("DEFAULT_RECOMMENDED_SKILLS_LIMIT", "8"))
    MAX_RECOMMENDED_SKILLS_LIMIT = int(os.getenv("MAX_RECOMMENDED_SKILLS_LIMIT", "20"))
    MAX_EXECUTIONS_LIMIT = int(os.getenv("MAX_EXECUTIONS_LIMIT", "200"))
    DEFAULT_DEPLOYMENTS_LIMIT = int(os.getenv("DEFAULT_DEPLOYMENTS_LIMIT", "50"))

    # Execution Timeouts
    SKILL_EXECUTION_TIMEOUT_SECONDS = int(os.getenv("SKILL_EXECUTION_TIMEOUT_SECONDS", "600"))
    GOOGLE_DOC_DELIVERY_TIMEOUT_SECONDS = int(os.getenv("GOOGLE_DOC_DELIVERY_TIMEOUT_SECONDS", "60"))
    
    # Webhook Configuration
    WEBHOOK_RETRY_ATTEMPTS = int(os.getenv("WEBHOOK_RETRY_ATTEMPTS", "3"))
    WEBHOOK_RETRY_DELAY_SECONDS = int(os.getenv("WEBHOOK_RETRY_DELAY_SECONDS", "2"))
    WEBHOOK_TIMEOUT_SECONDS = int(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "30"))
    
    # Logging Configuration
    MAX_EVENTS_IN_MEMORY = int(os.getenv("MAX_EVENTS_IN_MEMORY", "500"))
    EVENT_RETENTION_DAYS = int(os.getenv("EVENT_RETENTION_DAYS", "30"))
    WEBHOOK_LOG_RETENTION_DAYS = int(os.getenv("WEBHOOK_LOG_RETENTION_DAYS", "7"))
    
    # Security Configuration
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Session keepalive strategy:
    # - Keepalive is activity-based via SESSION_REFRESH_EACH_REQUEST=True (rolling expiry).
    # - Idle timeout is enforced by PERMANENT_SESSION_LIFETIME when no requests occur.
    # Together this gives a sliding session window: active users stay logged in, idle users expire.
    SESSION_REFRESH_EACH_REQUEST = os.getenv("SESSION_REFRESH_EACH_REQUEST", "true").lower() == "true"
    PERMANENT_SESSION_LIFETIME_SECONDS = int(os.getenv("PERMANENT_SESSION_LIFETIME", "86400"))
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=PERMANENT_SESSION_LIFETIME_SECONDS)  # 24-hour default idle timeout
    
    # Rate Limiting (future use)
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    MAX_PENDING_RUNNING_RUNS_PER_SESSION = int(
        os.getenv("MAX_PENDING_RUNNING_RUNS_PER_SESSION", "3")
    )
    
    # Deployment Configuration
    PORT = int(os.getenv("PORT", "8080"))
    HOST = os.getenv("HOST", "0.0.0.0")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    # Monitoring Configuration
    HEALTH_CHECK_ENABLED = os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true"
    METRICS_ENABLED = os.getenv("METRICS_ENABLED", "false").lower() == "true"
    
    @classmethod
    def get_env_var_value(cls, var_name: str) -> str:
        """Get environment variable value."""
        return os.getenv(var_name, "")
    
    @classmethod
    def set_env_var(cls, var_name: str, value: str):
        """Set environment variable (runtime only)."""
        os.environ[var_name] = value
    
    @classmethod
    def is_env_var_set(cls, var_name: str) -> bool:
        """Check if environment variable is set."""
        return bool(os.getenv(var_name, ""))
    
    @classmethod
    def get_all_tracked_vars(cls) -> dict:
        """Get all tracked environment variables with their values (redacted)."""
        vars_dict = {}
        for var in cls.TRACKED_ENV_VARS:
            value = os.getenv(var, "")
            if value:
                # Redact sensitive values
                if len(value) > 10:
                    vars_dict[var] = f"{value[:4]}...{value[-4:]}"
                else:
                    vars_dict[var] = "***"
            else:
                vars_dict[var] = ""
        return vars_dict
    
    @classmethod
    def validate_config(cls) -> dict:
        """Validate critical configuration and return status."""
        issues = []
        warnings = []
        
        # Check critical configuration
        if not cls.DASHBOARD_PASSWORD_HASH:
            issues.append("DASHBOARD_PASSWORD_HASH is not set - dashboard is insecure!")

        if not cls.CHAT_TOKEN_ENCRYPTION_KEY:
            issues.append("CHAT_TOKEN_ENCRYPTION_KEY is not set - chat token encryption is insecure!")
        elif len(cls.CHAT_TOKEN_ENCRYPTION_KEY) < 32:
            issues.append("CHAT_TOKEN_ENCRYPTION_KEY must be at least 32 characters long")
        
        if not cls.RAILWAY_API_TOKEN:
            warnings.append("RAILWAY_API_TOKEN not set - Railway features disabled")
        
        if not cls.get_env_var_value("SLACK_WEBHOOK_URL"):
            warnings.append("SLACK_WEBHOOK_URL not set - Slack notifications disabled")
        
        # Check database path is writable
        db_dir = Path(cls.DB_PATH).parent
        if not db_dir.exists():
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                issues.append(f"Cannot create database directory: {e}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True


# Select configuration based on environment
def get_config():
    """Get configuration based on FLASK_ENV."""
    env = os.getenv("FLASK_ENV", "production").lower()
    if env == "development":
        return DevelopmentConfig
    return ProductionConfig
