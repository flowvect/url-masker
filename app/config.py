"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration — values come from .env or the OS environment."""

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/url_masker",
        description="Async PostgreSQL connection string",
    )

    # ── Security ──────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        default="change-me-to-a-random-secret-key",
        description="Secret used for JWT signing",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24,  # 24 hours
        description="JWT token lifetime in minutes",
    )

    # ── Application ───────────────────────────────────────────────────────
    ENVIRONMENT: str = Field(default="development")
    BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Public URL prefix for generated short links",
    )

    # ── Cache ─────────────────────────────────────────────────────────────
    CACHE_TTL: int = Field(
        default=300,
        description="TTL (seconds) for in-memory short-code cache entries",
    )
    CACHE_MAX_SIZE: int = Field(
        default=10_000,
        description="Maximum number of entries in the in-memory cache",
    )

    # ── Rate Limiting ─────────────────────────────────────────────────────
    RATE_LIMIT_ANON: int = Field(default=20)
    RATE_LIMIT_USER: int = Field(default=100)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
