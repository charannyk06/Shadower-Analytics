"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings
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

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
