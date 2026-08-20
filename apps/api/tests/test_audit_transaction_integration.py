"""PostgreSQL transaction integration tests for audit logs."""

import json
import uuid

import asyncpg
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from hiron.audit.models import AuditLog
from hiron.audit.repository import AuditRepository
from hiron.audit.service import AuditService
from hiron.jobs.models import Job
from hiron.jobs.service import JobService
from hiron.tenants.models import Tenant
from hiron.users.models import User

ADMIN_DB_URL = "postgresql+asyncpg://hiron_user:hiron_secure_password@localhost:5432/hiron_dev"


@pytest.fixture(scope="session")
async def db_engine():
    """Create a real PostgreSQL engine."""
    engine = create_async_engine(ADMIN_DB_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def setup_data(db_engine) -> tuple[uuid.UUID, uuid.UUID]:
    """Setup test tenant and user in the database."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Create Tenant
        tenant = Tenant(id=tenant_id, name="Integration Test Tenant", slug=f"test-{tenant_id}")
        session.add(tenant)

        # Create User
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            email=f"{user_id}@test.com",
            full_name="Integration User",
            password_hash="hash",
            role="org_admin"
        )
        session.add(user)

        await session.commit()

    return tenant_id, user_id


@pytest.mark.asyncio
async def test_a_successful_atomic_transaction(
    db_engine,
    setup_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """TEST A: Perform a real mutation and verify both mutation and audit log are persisted."""
    tenant_id, user_id = setup_data

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        job_service = JobService()

        # We use a real mutation service and REAL AuditService
        job = await job_service.create_job(
            session=session,
            tenant_id=tenant_id,
            created_by=user_id,
            current_user_role="org_admin",
            title="Real Postgres Job",
            description="Real description",
            employment_type="full_time",
        )
        # Note: job_service.create_job calls session.commit() internally

        job_id = job.id

    # Query using a NEW separate session
    async with async_session() as session:
        # Assert job exists
        db_job = await session.get(Job, job_id)
        assert db_job is not None
        assert db_job.title == "Real Postgres Job"

        # Assert audit_logs row exists
        stmt = select(AuditLog).where(AuditLog.entity_id == job_id)
        result = await session.execute(stmt)
        audit_log = result.scalars().first()

        assert audit_log is not None
        assert audit_log.tenant_id == tenant_id
        assert audit_log.actor_id == user_id
        assert audit_log.action == "job_created"
        assert audit_log.entity_type == "job"

        # Verify changes payload
        changes = audit_log.changes
        assert "after" in changes
        assert changes["after"]["title"] == "Real Postgres Job"


@pytest.mark.asyncio
async def test_b_audit_failure_rolls_back_mutation(
    db_engine,
    setup_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """TEST B: Inject audit failure and verify mutation rolls back."""
    tenant_id, user_id = setup_data

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        job_service = JobService()

        # Mock audit service to raise exception
        class FailingAuditService(AuditService):
            async def record_audit_log(self, *args, **kwargs):
                raise Exception("Controlled audit failure")

        job_service.audit_service = FailingAuditService()

        try:
            await job_service.create_job(
                session=session,
                tenant_id=tenant_id,
                created_by=user_id,
                current_user_role="org_admin",
                title="Fail Postgres Job",
                description="Fail description",
                employment_type="full_time",
            )
            pytest.fail("Should have raised Exception")
        except Exception as e:
            assert str(e) == "Controlled audit failure"
            # get_db_session dependency calls session.rollback() on exception
            await session.rollback()

    # Open NEW PostgreSQL session
    async with async_session() as session:
        # Assert mutation row does NOT exist
        stmt = select(Job).where(Job.title == "Fail Postgres Job", Job.tenant_id == tenant_id)
        result = await session.execute(stmt)
        assert result.scalars().first() is None

        # Assert audit row does NOT exist
        stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id, AuditLog.action == "job_created")
        result = await session.execute(stmt)
        # Exclude the successful one from Test A
        logs = [log for log in result.scalars().all() if log.changes and log.changes.get("after", {}).get("title") == "Fail Postgres Job"]
        assert len(logs) == 0


@pytest.mark.asyncio
async def test_c_mutation_failure_rolls_back_audit(
    db_engine,
    setup_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """TEST C: Fail mutation after audit flush, verify audit rolls back."""
    tenant_id, user_id = setup_data

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        audit_service = AuditService()

        try:
            # Simulate a mutation that adds something, then flushes audit, then fails
            job_id = uuid.uuid4()
            job = Job(id=job_id, tenant_id=tenant_id, title="Will Fail Job", description="Desc")
            session.add(job)

            # Flush audit log
            await audit_service.record_audit_log(
                session=session,
                tenant_id=tenant_id,
                action="job_created",
                entity_type="job",
                entity_id=job_id,
                actor_id=user_id,
                changes={"after": {"title": "Will Fail Job"}}
            )

            # Raise exception BEFORE commit
            raise Exception("Controlled mutation failure")

        except Exception as e:
            assert str(e) == "Controlled mutation failure"
            await session.rollback()

    # Open NEW session
    async with async_session() as session:
        db_job = await session.get(Job, job_id)
        assert db_job is None

        stmt = select(AuditLog).where(AuditLog.entity_id == job_id)
        result = await session.execute(stmt)
        assert result.scalars().first() is None


@pytest.mark.asyncio
async def test_d_same_transaction(
    db_engine,
    setup_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """TEST D: Verify mutation and audit insertion use the exact same transaction ID (txid_current)."""
    tenant_id, user_id = setup_data

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Get the transaction ID of the current session
        res = await session.execute(text("SELECT txid_current()"))
        txid = res.scalar()

        # Perform mutation and audit in this session
        job_id = uuid.uuid4()
        job = Job(id=job_id, tenant_id=tenant_id, title="TxID Job", description="Desc")
        session.add(job)

        audit_repo = AuditRepository()
        await audit_repo.create_audit_log(
            session=session,
            tenant_id=tenant_id,
            action="job_created",
            entity_type="job",
            entity_id=job_id,
            actor_id=user_id,
            changes={"txid": txid}
        )

        # Verify the session hasn't implicitly opened a new transaction
        res2 = await session.execute(text("SELECT txid_current()"))
        txid2 = res2.scalar()

        assert txid == txid2, "Transaction ID changed during execution!"
        await session.rollback()


@pytest.mark.asyncio
async def test_e_secret_redaction(
    db_engine,
    setup_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """TEST E: Verify secrets are redacted in persisted JSONB."""
    tenant_id, user_id = setup_data

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        from hiron.audit.utils import sanitize_audit_payload

        sensitive_payload = {
            "after": {
                "email": "test@example.com",
                "password": "super-secret",
                "nested": {
                    "refresh_token": "secret-token",
                    "api_key": "my-api-key",
                    "cookie": "my-cookie",
                    "secret": "my-secret",
                    "access_token": "my-access-token"
                }
            }
        }

        sanitized = sanitize_audit_payload(sensitive_payload)

        audit_service = AuditService()
        entity_id = uuid.uuid4()

        await audit_service.record_audit_log(
            session=session,
            tenant_id=tenant_id,
            action="user_created",
            entity_type="user",
            entity_id=entity_id,
            actor_id=user_id,
            changes=sanitized
        )

        await session.commit()

    # Read the actual JSONB value from PostgreSQL using raw asyncpg to ensure we see EXACTLY what is persisted
    conn = await asyncpg.connect("postgresql://hiron_user:hiron_secure_password@localhost:5432/hiron_dev")
    try:
        row = await conn.fetchrow("SELECT changes FROM audit_logs WHERE entity_id = $1", entity_id)
        changes_json = row["changes"]

        # Assert REDACTED appears
        assert "***REDACTED***" in changes_json

        # Assert plaintext values do NOT appear
        assert "super-secret" not in changes_json
        assert "secret-token" not in changes_json
        assert "my-api-key" not in changes_json
        assert "my-cookie" not in changes_json
        assert "my-secret" not in changes_json
        assert "my-access-token" not in changes_json

        # Assert non-sensitive data remains intact
        parsed = json.loads(changes_json)
        assert parsed["after"]["email"] == "test@example.com"
        assert parsed["after"]["password"] == "***REDACTED***"
        assert parsed["after"]["nested"]["refresh_token"] == "***REDACTED***"

    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_f_update_before_after_persistence(
    db_engine,
    setup_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """TEST F: Verify update before/after persistence."""
    tenant_id, user_id = setup_data

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    job_id = None

    async with async_session() as session:
        job_service = JobService()

        # Create Job
        job = await job_service.create_job(
            session=session,
            tenant_id=tenant_id,
            created_by=user_id,
            current_user_role="org_admin",
            title="Update Test Job",
            description="Initial",
            employment_type="full_time",
        )
        job_id = job.id

    # Open new session for update
    async with async_session() as session:
        job_service = JobService()
        await job_service.close_job(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            current_user_role="org_admin",
            job_id=job_id
        )

    # Open new session to verify audit JSONB
    async with async_session() as session:
        stmt = select(AuditLog).where(AuditLog.entity_id == job_id, AuditLog.action == "job_closed")
        result = await session.execute(stmt)
        audit_log = result.scalars().first()

        assert audit_log is not None
        changes = audit_log.changes
        assert "before" in changes
        assert "after" in changes
        assert changes["before"]["status"] == "draft" # Default status on creation is draft
        assert changes["after"]["status"] == "closed"


@pytest.mark.asyncio
async def test_g_delete_archive_before_state(
    db_engine,
    setup_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """TEST G: Verify delete/archive includes before state."""
    tenant_id, user_id = setup_data

    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    # Let's use candidate archive
    from hiron.candidates.service import CandidateService
    candidate_id = None

    async with async_session() as session:
        cand_service = CandidateService()
        candidate = await cand_service.create_candidate(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            current_user_role="org_admin",
            full_name="Archive Me",
            email="archive@test.com",
            source="upload"
        )
        candidate_id = candidate.id

    # Open new session for archive
    async with async_session() as session:
        cand_service = CandidateService()
        await cand_service.archive_candidate(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            current_user_role="org_admin",
            candidate_id=candidate_id
        )

    # Open new session to verify audit JSONB
    async with async_session() as session:
        stmt = select(AuditLog).where(AuditLog.entity_id == candidate_id, AuditLog.action == "candidate_archived")
        result = await session.execute(stmt)
        audit_log = result.scalars().first()

        assert audit_log is not None
        changes = audit_log.changes
        assert "before" in changes
        assert "after" in changes
        assert changes["before"]["is_archived"] is False
        assert changes["after"]["is_archived"] is True
