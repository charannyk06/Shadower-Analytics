"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings
from typing import List
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

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Security
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

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

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
