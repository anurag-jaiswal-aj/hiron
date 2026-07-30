"""Async SQLAlchemy database engine, session management, and connectivity probes."""

import time
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from hiron.core.config import get_settings

logger = structlog.get_logger("hiron.api.database")
settings = get_settings()

# 1. Async SQLAlchemy Engine Configuration (§10 & Database Design)
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=(settings.environment == "development" and settings.log_level == "DEBUG"),
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,  # Automatically test connections before returning from pool
)

# 2. Async Session Factory
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# 3. FastAPI Dependency Injection for Async Database Sessions (§5.2)
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session and ensure proper cleanup/rollback on exit."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 4. Database Readiness Probe Function (API Contract §HEALTH-2)
async def check_database_connection() -> tuple[bool, float]:
    """Perform a ping query (SELECT 1) against PostgreSQL and measure latency.

    Returns:
        Tuple[bool, float]: (is_healthy, latency_in_ms)
    """
    start_time = time.perf_counter()
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return True, latency_ms
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.warning("Database health check failed", error=str(exc), latency_ms=latency_ms)
        return False, latency_ms
