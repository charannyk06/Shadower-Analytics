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
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

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
    PROMETHEUS_PORT: int = 9090

    # Feature Flags
    ENABLE_REALTIME: bool = True
    ENABLE_ALERTS: bool = True
    ENABLE_EXPORTS: bool = True

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Aggregation
    HOURLY_ROLLUP_ENABLED: bool = True
    DAILY_ROLLUP_ENABLED: bool = True
    WEEKLY_ROLLUP_ENABLED: bool = True
    MONTHLY_ROLLUP_ENABLED: bool = True

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
