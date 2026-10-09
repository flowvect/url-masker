"""Async SQLAlchemy engine and session factory with Serverless / Vercel auto-adaptation."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# On Serverless / Vercel (AWS Lambda), NullPool avoids connection pool exhaustion
# across ephemeral function lifecycles. On standalone servers, connection pooling is used.
if settings.is_serverless:
    engine = create_async_engine(
        settings.async_database_url,
        echo=False,
        poolclass=NullPool,
    )
else:
    engine = create_async_engine(
        settings.async_database_url,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency — yields an async DB session and closes it after use."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
