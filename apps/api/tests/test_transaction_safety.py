"""Explicit Lifecycle Tests for Database Transaction Safety per Phase 16.4.
Verifies pool isolation, transaction lifecycle, and SQLAlchemy checkout hooks.
"""

import asyncio
import uuid
from typing import Any

import pytest
from sqlalchemy import text

from hiron.core.database import AsyncSessionLocal, engine
from hiron.security.context import set_tenant_context, tenant_context


@pytest.mark.asyncio
async def test_sqlalchemy_transaction_lifecycle() -> None:
    """Verify transaction commits, rollbacks, and connection reuse don't leak tenant context."""
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())

    # We will manually get a raw connection from the engine to simulate pool reuse precisely
    # Or just use AsyncSessionLocal to test the full stack lifecycle.

    # 1. A then B on the same connection.
    # To test same connection, we will bind a session to a single connection.
    set_tenant_context(tenant_a)
    async with engine.connect() as conn:
        # Request A
        # Note: SQLAlchemy's checkout hook fires on engine.connect(), NOT on session.execute()
        # Wait, if we use engine.connect(), checkout fires once. If we change tenant context WHILE holding the connection,
        # the checkout hook won't fire again. This means tenant context is connection-bound for its lifetime!
        # Let's verify this behavior.
        res = await conn.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
        assert res.scalar() == tenant_a

        # If Request B uses the SAME checkout without returning to pool, which shouldn't happen in ASGI apps,
        # but let's test typical session boundaries.

    # In FastAPI, a new request means a new checkout from the pool via get_db_session()
    # 1. & 2. A then B / B then A on the same pooled connection
    # Let's force the pool to have size 1 so we guarantee reuse.

    async def get_tenant_setting(t_id: str | None) -> str:
        set_tenant_context(t_id)
        async with AsyncSessionLocal() as session:
            res = await session.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
            return str(res.scalar())

    # Auth A
    assert await get_tenant_setting(tenant_a) == tenant_a
    # Auth B (reusing connection)
    assert await get_tenant_setting(tenant_b) == tenant_b
    # Auth A again
    assert await get_tenant_setting(tenant_a) == tenant_a

    # 3. Authenticated then unauthenticated
    assert await get_tenant_setting(tenant_b) == tenant_b
    assert await get_tenant_setting(None) == ""

    # 4. Unauthenticated then authenticated
    assert await get_tenant_setting(None) == ""
    assert await get_tenant_setting(tenant_a) == tenant_a

    # 5. Concurrent Tenant A and Tenant B requests
    async def concurrent_request(t_id: str | None) -> None:
        set_tenant_context(t_id)
        # Force a slight pause to allow interleaving
        async with AsyncSessionLocal() as session:
            await asyncio.sleep(0.1)
            # Re-read contextvar to ensure it wasn't overwritten globally
            assert tenant_context.get() == t_id
            res = await session.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
            assert res.scalar() == (t_id if t_id else "")

    await asyncio.gather(
        concurrent_request(tenant_a),
        concurrent_request(tenant_b),
        concurrent_request(None)
    )

    # 6. & 7. Transaction Commit and Rollback
    set_tenant_context(tenant_a)
    async with AsyncSessionLocal() as session:
        # Commit
        await session.execute(text("SELECT 1"))
        await session.commit()
        # After commit, the transaction ends. SQLAlchemy will begin a new one on next execute.
        # But wait! If we do `SET` without `LOCAL`, it survives the commit.
        # If we use `SET LOCAL`, it is cleared by `commit`.
        # Does our checkout hook run again after `commit`? NO.
        # This is a critical security vulnerability if the app does multiple transactions per request!
        # Let's test if the setting survives a commit.
        res_after: Any = await session.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
        assert res_after.scalar() == tenant_a, "Context lost after COMMIT! Implementation uses SET LOCAL improperly, or connection lost state."

        # Rollback
        await session.execute(text("SELECT 1"))
        await session.rollback()
        res_after_rollback: Any = await session.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
        val_after_rollback = res_after_rollback.scalar()
        assert val_after_rollback == tenant_a, "Context lost after ROLLBACK! Implementation uses SET LOCAL improperly, or connection lost state."
