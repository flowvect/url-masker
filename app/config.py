"""Application settings loaded from environment variables.

Supports local development, Docker containers, and serverless runtimes like Vercel.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration — dynamically adapts to local and cloud environments."""

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/url_masker",
        description="Async PostgreSQL connection string (e.g. Neon, Supabase, Railway)",
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

    # ── Environment & URLs ────────────────────────────────────────────────
    ENVIRONMENT: str = Field(
        default_factory=lambda: os.getenv("VERCEL_ENV", "development")
    )
    
    # Explicit base URL (optional override)
    BASE_URL: Optional[str] = Field(
        default=None,
        description="Explicit public URL prefix (e.g. https://sho.rt or https://url-masker-test.vercel.app)",
    )
    
    # Vercel-injected deployment URL (e.g. url-masker-test.vercel.app)
    VERCEL_URL: Optional[str] = Field(
        default_factory=lambda: os.getenv("VERCEL_URL", None),
        description="Auto-injected by Vercel serverless platform",
    )

    # Repository link for UI
    GITHUB_REPO_URL: str = Field(
        default="https://github.com/flowvect/url-masker",
        description="GitHub repository URL",
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

    @property
    def is_serverless(self) -> bool:
        """True when running inside Vercel or AWS Lambda serverless runtime."""
        return bool(
            os.getenv("VERCEL")
            or os.getenv("VERCEL_ENV")
            or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
        )

    @property
    def async_database_url(self) -> str:
        """Ensure connection string uses postgresql+asyncpg:// driver for async SQLAlchemy.
        
        Handles copy-pasting standard postgres:// or postgresql:// URLs from Neon, Supabase, Railway.
        """
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        return url

    @property
    def effective_base_url(self) -> str:
        """Dynamically compute the active base URL.
        
        Priority:
        1. Explicit BASE_URL setting (if provided)
        2. VERCEL_URL auto-injected by Vercel (https://<VERCEL_URL>)
        3. Localhost fallback (http://localhost:8000)
        """
        if self.BASE_URL and self.BASE_URL.strip():
            url = self.BASE_URL.strip().rstrip("/")
            if not url.startswith("http://") and not url.startswith("https://"):
                url = f"https://{url}"
            return url
        
        if self.VERCEL_URL and self.VERCEL_URL.strip():
            v_url = self.VERCEL_URL.strip().rstrip("/")
            return f"https://{v_url}" if not v_url.startswith("http") else v_url

        return "http://localhost:8000"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
