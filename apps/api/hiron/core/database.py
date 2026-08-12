"""Async SQLAlchemy database engine, session management, and connectivity probes."""

import time
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from hiron.security.context import get_tenant_context

from hiron.core.config import get_settings

logger = structlog.get_logger("hiron.api.database")
settings = get_settings()

import sys
from sqlalchemy import pool

# 1. Async SQLAlchemy Engine Configuration (§10 & Database Design)
_is_celery = sys.argv and "celery" in sys.argv[0]
_engine_kwargs = {
    "echo": (settings.environment == "development" and settings.log_level == "DEBUG"),
}
if _is_celery:
    # Celery workers execute async tasks in dynamically created/closed event loops.
    # NullPool prevents asyncpg from reusing connection futures across different loops.
    _engine_kwargs["poolclass"] = pool.NullPool
else:
    _engine_kwargs["pool_size"] = settings.db_pool_size
    _engine_kwargs["max_overflow"] = settings.db_max_overflow
    _engine_kwargs["pool_timeout"] = settings.db_pool_timeout
    _engine_kwargs["pool_pre_ping"] = True

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    **_engine_kwargs,
)

# 2. Async Session Factory
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

@event.listens_for(engine.sync_engine, "checkout")
def set_tenant_context_on_checkout(dbapi_connection, connection_record, connection_proxy) -> None:
    """Inject tenant identity into the PostgreSQL session upon checking out a connection."""
    tenant_id = get_tenant_context()
    cursor = dbapi_connection.cursor()
    try:
        if tenant_id:
            cursor.execute(f"SET app.current_tenant_id = '{tenant_id}'")
        else:
            # Clear tenant context to prevent data leakage from previous pooled connections
            cursor.execute("RESET app.current_tenant_id")
    except Exception as exc:
        logger.error("Failed to set RLS context on checkout", error=str(exc))
        raise
    finally:
        cursor.close()


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
