"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_ENV: str = "development"
    API_VERSION: str = "v1"

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/shadower_analytics"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # Redis
    # IMPORTANT: Set these in environment variables or .env file
    # For development: Use .env with weak password
    # For production: Set strong password via environment variable (generate with: openssl rand -base64 32)
    # Empty defaults require configuration to prevent accidental production use without proper credentials
    REDIS_URL: str = ""
    REDIS_PASSWORD: Optional[str] = None

    # Celery
    # IMPORTANT: Set these in environment variables or .env file
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # Security & Authentication
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_EXPIRATION_HOURS: int = 24
    JWT_REFRESH_EXPIRATION_DAYS: int = 30

    # Optional: For RS256 (asymmetric encryption)
    JWT_PUBLIC_KEY: Optional[str] = None
    JWT_PRIVATE_KEY: Optional[str] = None

    # Supabase (if using Supabase Auth)
    SUPABASE_JWT_SECRET: Optional[str] = None
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # Main App Integration
    MAIN_APP_URL: str = "http://localhost:3001"

    # Monitoring
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: Optional[float] = None
    SENTRY_PROFILES_SAMPLE_RATE: Optional[float] = None
    PROMETHEUS_PORT: int = 9090

    # OpenTelemetry Tracing
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None
    OTEL_EXPORTER_INSECURE: str = "true"
    OTEL_CONSOLE_EXPORT: str = "false"

    # Log Aggregation
    ELASTICSEARCH_HOST: Optional[str] = None
    ELASTICSEARCH_PORT: int = 9200
    ELASTICSEARCH_SCHEME: str = "http"
    ELASTICSEARCH_USER: Optional[str] = None
    ELASTICSEARCH_PASSWORD: Optional[str] = None

    # Feature Flags
    ENABLE_REALTIME: bool = True
    ENABLE_ALERTS: bool = True
    ENABLE_EXPORTS: bool = True
    ENABLE_NOTIFICATIONS: bool = True

    # Notification System
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    SMTP_USE_TLS: bool = True

    # Notification Channels
    SLACK_WEBHOOK_URL: Optional[str] = None
    TEAMS_WEBHOOK_URL: Optional[str] = None
    DISCORD_WEBHOOK_URL: Optional[str] = None

    # Notification Defaults
    NOTIFICATION_MAX_RETRIES: int = 3
    NOTIFICATION_RETRY_DELAY: int = 300  # 5 minutes
    DIGEST_ENABLED: bool = True
    DIGEST_DAILY_TIME: str = "08:00"  # UTC time for daily digests
    DIGEST_WEEKLY_DAY: int = 1  # Monday

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Aggregation
    HOURLY_ROLLUP_ENABLED: bool = True
    DAILY_ROLLUP_ENABLED: bool = True
    WEEKLY_ROLLUP_ENABLED: bool = True
    MONTHLY_ROLLUP_ENABLED: bool = True

    @field_validator("REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND")
    @classmethod
    def validate_redis_urls(cls, v: str, info) -> str:
        """Validate Redis URLs are configured."""
        field_name = info.field_name
        
        if not v or v == "":
            raise ValueError(
                f"{field_name} must be set via environment variable or .env file. "
                f"See backend/.env.example for configuration examples."
            )
        
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Validate JWT secret key strength in production."""
        # Get APP_ENV from the values being validated
        app_env = info.data.get("APP_ENV", "development")

        # Weak secrets that should never be used
        weak_secrets = [
            "your-secret-key-change-in-production",
            "secret",
            "changeme",
            "default",
            "test",
            "password",
            "12345",
        ]

        if app_env == "production":
            # In production, enforce strict requirements
            if v.lower() in weak_secrets:
                raise ValueError(
                    "JWT_SECRET_KEY must be changed from default value in production. "
                    "Generate a strong secret using: openssl rand -hex 32"
                )
            if len(v) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be at least 32 characters in production. "
                    "Generate a strong secret using: openssl rand -hex 32"
                )
        else:
            # In development, warn but allow weak secrets
            if v.lower() in weak_secrets:
                import warnings
                warnings.warn(
                    f"Using default JWT_SECRET_KEY in {app_env} environment. "
                    "This is insecure for production use.",
                    UserWarning,
                )

        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
