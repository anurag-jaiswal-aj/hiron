"""Explicit Lifecycle Tests for Database Transaction Safety per Phase 16.4.
Verifies pool isolation, transaction lifecycle, and SQLAlchemy checkout hooks.
"""

import asyncio
import uuid
from typing import Any

import pytest
from sqlalchemy import text

from hiron.core.database import get_db_session
from hiron.security.context import set_tenant_context, tenant_context


@pytest.mark.asyncio
async def test_sqlalchemy_transaction_lifecycle() -> None:
    """Verify transaction commits, rollbacks, and connection reuse don't leak tenant context."""
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())

    async def get_tenant_setting(t_id: str | None) -> str:
        set_tenant_context(t_id)
        async for session in get_db_session():
            res = await session.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
            val = res.scalar()
            return str(val) if val else ""

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
        async for session in get_db_session():
            await asyncio.sleep(0.1)
            # Re-read contextvar to ensure it wasn't overwritten globally
            assert tenant_context.get() == t_id
            res = await session.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
            val = res.scalar()
            assert (str(val) if val else "") == (t_id if t_id else "")

    await asyncio.gather(
        concurrent_request(tenant_a),
        concurrent_request(tenant_b),
        concurrent_request(None)
    )

    # 6. & 7. Transaction Commit and Rollback
    set_tenant_context(tenant_a)
    async for session in get_db_session():
        # Commit
        await session.execute(text("SELECT 1"))
        await session.commit()
        res_after: Any = await session.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
        assert res_after.scalar() == tenant_a

        # Rollback
        await session.execute(text("SELECT 1"))
        await session.rollback()
        res_after_rollback: Any = await session.execute(text("SELECT current_setting('app.current_tenant_id', true)"))
        val_after_rollback = res_after_rollback.scalar()
        assert val_after_rollback == tenant_a
