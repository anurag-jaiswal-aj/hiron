"""Unit tests for AuditRepository entry creation, entity filtering, and pagination."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.audit.repository import AuditRepository


@pytest.mark.asyncio
async def test_create_audit_log_persists_entry() -> None:
    """Verify create_audit_log adds AuditLog entity to session."""
    repo = AuditRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    log = await repo.create_audit_log(
        session=session,
        tenant_id=tenant_id,
        action="stage_changed",
        entity_type="job_candidate",
        entity_id=entity_id,
        actor_id=actor_id,
        changes={"before": {"stage": "Screening"}, "after": {"stage": "Interview"}},
    )

    assert log.tenant_id == tenant_id
    assert log.action == "stage_changed"
    assert log.entity_type == "job_candidate"
    assert log.entity_id == entity_id
    assert log.actor_id == actor_id
    assert log.changes == {"before": {"stage": "Screening"}, "after": {"stage": "Interview"}}
    session.add.assert_called_once()
